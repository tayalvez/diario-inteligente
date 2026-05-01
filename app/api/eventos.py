"""API de Eventos — entidade central do sistema."""
import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.models.database import get_db, Evento, RelacaoEvento
from app.schemas.evento import (
    EventoCriar, EventoAtualizar, EventoResposta,
    RelacaoCriar, RelacaoResposta,
    PresetResposta, EstadoAgregado,
)

router = APIRouter(prefix="/api/eventos", tags=["Eventos"])

# ── Presets de entrada rápida ──────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "cansada":        {"energia": 0.2, "estresse": 0.6, "humor": 0.4},
    "estressada":     {"estresse": 0.8, "humor": 0.3, "energia": 0.4},
    "ansiosa":        {"estresse": 0.7, "humor": 0.3, "energia": 0.5},
    "tranquila":      {"estresse": 0.1, "humor": 0.7, "energia": 0.6},
    "animada":        {"humor": 0.8, "energia": 0.8, "estresse": 0.1},
    "feliz":          {"humor": 0.9, "energia": 0.7, "estresse": 0.1},
    "triste":         {"humor": 0.2, "energia": 0.3, "estresse": 0.4},
    "irritada":       {"estresse": 0.8, "humor": 0.2, "energia": 0.6},
    "focada":         {"energia": 0.7, "humor": 0.6, "estresse": 0.1, "dimensoes_extras": {"foco": 0.9}},
    "confusa":        {"energia": 0.5, "humor": 0.4, "estresse": 0.5, "dimensoes_extras": {"foco": 0.2}},
    "motivada":       {"energia": 0.9, "humor": 0.7, "estresse": 0.1},
    "entediada":      {"energia": 0.3, "humor": 0.3, "estresse": 0.2},
    "sobrecarregada": {"estresse": 0.9, "energia": 0.3, "humor": 0.3},
    "empolgada":      {"humor": 0.85, "energia": 0.9, "estresse": 0.1},
    "realizada":      {"humor": 0.85, "energia": 0.7, "estresse": 0.1},
    "grata":          {"humor": 0.8, "estresse": 0.1, "energia": 0.7},
}


# ── Similaridade automática ───────────────────────────────────────────────────


def _pair_key(origem_id: int, destino_id: int) -> tuple[int, int]:
    return (min(origem_id, destino_id), max(origem_id, destino_id))


def _reconciliar_relacoes_automaticas(db: Session, evento_id: int, descricao_alterada: bool = False) -> None:
    """Atualiza relações automáticas do evento antes de responder ao save."""
    try:
        from app.ml.similaridade import gerar_relacoes_similaridade
        import traceback

        novo = db.query(Evento).filter(Evento.id == evento_id).first()
        if not novo:
            return

        if (descricao_alterada or not novo.embedding) and novo.descricao and novo.descricao.strip():
            try:
                from app.ml.nlp import gerar_embedding
                vetor = gerar_embedding(novo.descricao.strip())
                if vetor:
                    novo.embedding = json.dumps(vetor)
                    db.flush()
            except Exception as e:
                print(f"[similaridade_sync] ERRO ao gerar embedding: {e}")
                traceback.print_exc()

        janela = novo.data_hora - timedelta(days=90)
        candidatos = db.query(Evento).filter(
            Evento.data_hora >= janela,
            Evento.id != evento_id,
        ).all()
        if not candidatos:
            # sem candidatos, remove apenas relações automáticas que apontavam para o evento
            relacoes_auto = db.query(RelacaoEvento).filter(
                ((RelacaoEvento.origem_id == evento_id) | (RelacaoEvento.destino_id == evento_id)),
                RelacaoEvento.confiabilidade < 1.0,
            ).all()
            for rel in relacoes_auto:
                db.delete(rel)
            db.flush()
            return

        eventos = [novo] + candidatos
        ids_eventos = [e.id for e in eventos]
        relacoes_existentes = db.query(RelacaoEvento).filter(
            RelacaoEvento.origem_id.in_(ids_eventos),
            RelacaoEvento.destino_id.in_(ids_eventos),
        ).all()

        pares_manuais = {
            _pair_key(r.origem_id, r.destino_id)
            for r in relacoes_existentes
            if r.confiabilidade >= 1.0
        }
        desejadas = [
            rel for rel in gerar_relacoes_similaridade(eventos, pares_manuais)
            if rel["origem_id"] == evento_id or rel["destino_id"] == evento_id
        ]
        desejadas_por_par = {
            _pair_key(rel["origem_id"], rel["destino_id"]): rel
            for rel in desejadas
        }

        relacoes_auto = [
            r for r in relacoes_existentes
            if r.confiabilidade < 1.0 and (r.origem_id == evento_id or r.destino_id == evento_id)
        ]
        automaticas_por_par = {
            _pair_key(r.origem_id, r.destino_id): r
            for r in relacoes_auto
        }

        for par, rel in automaticas_por_par.items():
            if par not in desejadas_por_par:
                db.delete(rel)

        for par, rel_desejada in desejadas_por_par.items():
            existente = automaticas_por_par.get(par)
            if existente:
                existente.origem_id = rel_desejada["origem_id"]
                existente.destino_id = rel_desejada["destino_id"]
                existente.intensidade = rel_desejada["intensidade"]
                existente.confiabilidade = rel_desejada["confiabilidade"]
                existente.motivo = rel_desejada.get("motivo")
                continue

            db.add(RelacaoEvento(
                origem_id=rel_desejada["origem_id"],
                destino_id=rel_desejada["destino_id"],
                intensidade=rel_desejada["intensidade"],
                confiabilidade=rel_desejada["confiabilidade"],
                motivo=rel_desejada.get("motivo"),
            ))
        db.flush()
    except Exception as e:
        import traceback
        print(f"[similaridade_sync] ERRO: {e}")
        traceback.print_exc()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _json_load(text: Optional[str]) -> Optional[dict | list]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _to_resp(e: Evento, include_relacoes: bool = False) -> EventoResposta:
    contagem = len(e.relacoes_origem) + len(e.relacoes_destino)
    relacoes = None
    if include_relacoes:
        relacoes = []
        for r in e.relacoes_origem:
            outro = r.evento_destino
            relacoes.append(RelacaoResposta(
                id=r.id, origem_id=r.origem_id, destino_id=r.destino_id,
                intensidade=r.intensidade, confiabilidade=r.confiabilidade,
                motivo=r.motivo,
                criado_em=r.criado_em,
                outro_evento_id=outro.id if outro else None,
                outro_evento_label=outro.evento if outro else None,
                outro_evento_data_hora=outro.data_hora if outro else None,
            ))
        for r in e.relacoes_destino:
            outro = r.evento_origem
            relacoes.append(RelacaoResposta(
                id=r.id, origem_id=r.origem_id, destino_id=r.destino_id,
                intensidade=r.intensidade, confiabilidade=r.confiabilidade,
                motivo=r.motivo,
                criado_em=r.criado_em,
                outro_evento_id=outro.id if outro else None,
                outro_evento_label=outro.evento if outro else None,
                outro_evento_data_hora=outro.data_hora if outro else None,
            ))

    return EventoResposta(
        id=e.id,
        evento=e.evento,
        data_hora=e.data_hora,
        energia=e.energia,
        humor=e.humor,
        estresse=e.estresse,
        sensibilidade=e.sensibilidade,
        serenidade=e.serenidade,
        interesse=e.interesse,
        descricao=e.descricao,
        contexto=_json_load(e.contexto_json),
        tags=_json_load(e.tags_json),
        dimensoes_extras=_json_load(e.dimensoes_extras_json),
        hora=e.hora,
        dia_semana=e.dia_semana,
        sentimento_score=e.sentimento_score,
        relacoes_contagem=contagem,
        relacoes=relacoes,
        criado_em=e.criado_em,
    )


def _agregar(eventos: list) -> dict:
    """Média de todas as dimensões."""
    def avg(lst): return round(sum(lst) / len(lst), 3) if lst else None

    result = {}
    for dim in ("energia", "humor", "estresse", "sensibilidade", "serenidade", "interesse"):
        vals = [getattr(e, dim, None) for e in eventos if getattr(e, dim, None) is not None]
        result[dim] = avg(vals)
    return result


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/presets", response_model=List[PresetResposta])
def listar_presets():
    result = []
    for k, v in PRESETS.items():
        result.append(PresetResposta(
            label=k,
            energia=v["energia"],
            humor=v["humor"],
            estresse=v["estresse"],
            sensibilidade=v.get("sensibilidade", 0.5),
            serenidade=v.get("serenidade", 0.5),
            interesse=v.get("interesse", 0.5),
            dimensoes_extras=v.get("dimensoes_extras"),
        ))
    return result


@router.get("/estado-hoje", response_model=Optional[EstadoAgregado])
def estado_hoje(db: Session = Depends(get_db)):
    inicio = datetime.combine(date.today(), datetime.min.time())
    fim    = datetime.combine(date.today(), datetime.max.time())
    evts = db.query(Evento).filter(
        Evento.data_hora >= inicio, Evento.data_hora <= fim
    ).all()
    if not evts:
        return None
    estado = _agregar(evts)
    return EstadoAgregado(data=date.today().isoformat(), total_eventos=len(evts), **estado)


@router.get("/historico", response_model=List[EstadoAgregado])
def historico_estados(dias: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    data_inicio = date.today() - timedelta(days=dias - 1)
    evts = db.query(Evento).filter(
        Evento.data_hora >= datetime.combine(data_inicio, datetime.min.time())
    ).order_by(Evento.data_hora.asc()).all()

    por_dia: dict[date, list] = {}
    for e in evts:
        d = e.data_hora.date()
        por_dia.setdefault(d, []).append(e)

    result = []
    for d in sorted(por_dia.keys()):
        estado = _agregar(por_dia[d])
        result.append(EstadoAgregado(
            data=d.isoformat(), total_eventos=len(por_dia[d]), **estado
        ))
    return result


@router.get("/", response_model=List[EventoResposta])
def listar_eventos(
    dias: Optional[int] = Query(None, ge=1, le=365),
    limite: int = Query(50, ge=1, le=500),
    include_relacoes: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(Evento).order_by(Evento.data_hora.desc())
    if dias:
        corte = datetime.combine(date.today() - timedelta(days=dias - 1), datetime.min.time())
        q = q.filter(Evento.data_hora >= corte)
    return [_to_resp(e, include_relacoes) for e in q.limit(limite).all()]


@router.post("/", response_model=EventoResposta, status_code=201)
def criar_evento(dados: EventoCriar, db: Session = Depends(get_db)):
    ts = dados.data_hora or datetime.utcnow()
    preset = PRESETS.get(dados.evento.lower().strip(), {})

    evt = Evento(
        evento=dados.evento.lower().strip(),
        data_hora=ts,
        energia=dados.energia if dados.energia is not None else preset.get("energia", 0.5),
        humor=dados.humor if dados.humor is not None else preset.get("humor", 0.5),
        estresse=dados.estresse if dados.estresse is not None else preset.get("estresse", 0.5),
        sensibilidade=dados.sensibilidade if dados.sensibilidade is not None else 0.5,
        serenidade=dados.serenidade if dados.serenidade is not None else 0.5,
        interesse=dados.interesse if dados.interesse is not None else 0.5,
        descricao=dados.descricao,
        contexto_json=json.dumps(dados.contexto, ensure_ascii=False) if dados.contexto else None,
        tags_json=json.dumps(dados.tags, ensure_ascii=False) if dados.tags else None,
        dimensoes_extras_json=json.dumps(dados.dimensoes_extras, ensure_ascii=False) if dados.dimensoes_extras else None,
        hora=ts.hour,
        dia_semana=ts.weekday(),
    )
    db.add(evt)
    db.flush()  # obtém o ID sem commitar ainda

    if dados.relacoes:
        for rel_data in dados.relacoes:
            destino = db.query(Evento).filter(Evento.id == rel_data.evento_id).first()
            if destino and destino.id != evt.id:
                db.add(RelacaoEvento(
                    origem_id=evt.id,
                    destino_id=destino.id,
                    intensidade=rel_data.intensidade,
                    confiabilidade=rel_data.confiabilidade,
                ))

    _reconciliar_relacoes_automaticas(db, evt.id)
    db.commit()
    db.refresh(evt)
    evt = db.query(Evento).filter(Evento.id == evt.id).first()
    return _to_resp(evt, include_relacoes=True)


@router.get("/{evento_id}", response_model=EventoResposta)
def obter_evento(evento_id: int, include_relacoes: bool = Query(True), db: Session = Depends(get_db)):
    e = db.query(Evento).filter(Evento.id == evento_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return _to_resp(e, include_relacoes)


@router.put("/{evento_id}", response_model=EventoResposta)
def atualizar_evento(evento_id: int, dados: EventoAtualizar, db: Session = Depends(get_db)):
    evt = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    update = dados.model_dump(exclude_unset=True)
    descricao_alterada = False  # Flag para saber se descrição foi editada

    if "evento" in update and update["evento"]:
        evt.evento = update["evento"].lower().strip()
    if "data_hora" in update and update["data_hora"]:
        ts = update["data_hora"]
        evt.data_hora = ts
        evt.hora = ts.hour
        evt.dia_semana = ts.weekday()
    if "energia" in update:
        evt.energia = update["energia"]
    if "humor" in update:
        evt.humor = update["humor"]
    if "estresse" in update:
        evt.estresse = update["estresse"]
    if "sensibilidade" in update:
        evt.sensibilidade = update["sensibilidade"]
    if "serenidade" in update:
        evt.serenidade = update["serenidade"]
    if "interesse" in update:
        evt.interesse = update["interesse"]
    if "descricao" in update:
        evt.descricao = update["descricao"]
        descricao_alterada = True  # Marca que descrição foi editada
    if "contexto" in update:
        evt.contexto_json = json.dumps(update["contexto"], ensure_ascii=False) if update["contexto"] else None
    if "tags" in update:
        evt.tags_json = json.dumps(update["tags"], ensure_ascii=False) if update["tags"] else None
    if "dimensoes_extras" in update:
        evt.dimensoes_extras_json = json.dumps(update["dimensoes_extras"], ensure_ascii=False) if update["dimensoes_extras"] else None

    db.flush()
    _reconciliar_relacoes_automaticas(db, evt.id, descricao_alterada)
    db.commit()
    db.refresh(evt)
    evt = db.query(Evento).filter(Evento.id == evt.id).first()
    return _to_resp(evt, include_relacoes=True)


@router.delete("/{evento_id}", status_code=204)
def excluir_evento(evento_id: int, db: Session = Depends(get_db)):
    evt = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    # Remove explicitamente as relações deste evento (origem e destino)
    db.query(RelacaoEvento).filter(
        (RelacaoEvento.origem_id == evento_id) | (RelacaoEvento.destino_id == evento_id)
    ).delete(synchronize_session=False)
    
    db.delete(evt)
    db.commit()
    return Response(status_code=204)


# ── Relações ───────────────────────────────────────────────────────────────────

@router.get("/{evento_id}/relacoes", response_model=List[RelacaoResposta])
def listar_relacoes(evento_id: int, db: Session = Depends(get_db)):
    e = db.query(Evento).filter(Evento.id == evento_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return _to_resp(e, include_relacoes=True).relacoes or []


@router.post("/{evento_id}/relacoes", response_model=RelacaoResposta, status_code=201)
def criar_relacao(evento_id: int, dados: RelacaoCriar, db: Session = Depends(get_db)):
    origem = db.query(Evento).filter(Evento.id == evento_id).first()
    destino = db.query(Evento).filter(Evento.id == dados.evento_id).first()
    if not origem:
        raise HTTPException(status_code=404, detail="Evento de origem não encontrado")
    if not destino:
        raise HTTPException(status_code=404, detail="Evento de destino não encontrado")
    if evento_id == dados.evento_id:
        raise HTTPException(status_code=400, detail="Um evento não pode se relacionar com ele mesmo")

    existente = db.query(RelacaoEvento).filter(
        RelacaoEvento.origem_id == evento_id,
        RelacaoEvento.destino_id == dados.evento_id,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Essa relação já existe")

    rel = RelacaoEvento(
        origem_id=evento_id,
        destino_id=dados.evento_id,
        intensidade=dados.intensidade,
        confiabilidade=dados.confiabilidade,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    return RelacaoResposta(
        id=rel.id, origem_id=rel.origem_id, destino_id=rel.destino_id,
        intensidade=rel.intensidade, confiabilidade=rel.confiabilidade,
        criado_em=rel.criado_em,
        outro_evento_id=destino.id,
        outro_evento_label=destino.evento,
        outro_evento_data_hora=destino.data_hora,
    )


@router.delete("/relacoes/{relacao_id}", status_code=204)
def excluir_relacao(relacao_id: int, db: Session = Depends(get_db)):
    rel = db.query(RelacaoEvento).filter(RelacaoEvento.id == relacao_id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relação não encontrada")
    db.delete(rel)
    db.commit()
    return Response(status_code=204)


@router.get("/{evento_id}/sugestoes", response_model=List[EventoResposta])
def sugerir_relacionados(
    evento_id: int,
    horas: int = Query(48, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Sugere eventos próximos no tempo para criar relações."""
    evt = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    ids_relacionados = {r.destino_id for r in evt.relacoes_origem}
    ids_relacionados |= {r.origem_id for r in evt.relacoes_destino}
    ids_relacionados.add(evento_id)

    janela = datetime.utcnow() - timedelta(hours=horas)
    candidatos = (
        db.query(Evento)
        .filter(Evento.data_hora >= janela, Evento.id.notin_(ids_relacionados))
        .order_by(Evento.data_hora.desc())
        .limit(10)
        .all()
    )
    return [_to_resp(c) for c in candidatos]
