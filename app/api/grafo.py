"""API de Grafo — visualização da rede de eventos e relações."""
from datetime import date, datetime, timedelta
from typing import Optional, Set
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db, Evento, RelacaoEvento

router = APIRouter(prefix="/api/grafo", tags=["Grafo de Eventos"])

# Cores por nível de energia (fallback)
CORES_ENERGIA = {
    "alta":   "#5dc893",
    "media":  "#7eb8e8",
    "baixa":  "#e07da8",
}

COR_ARESTA = "#9b8de0"


def _cor_no(e: Evento) -> str:
    if e.humor >= 0.7:
        return "#c8f0d4"
    if e.humor >= 0.4:
        return "#b8d4f0"
    return "#f0b8d4"


def _build_no(e: Evento, contagem: int) -> dict:
    label = e.evento[:35] + "..." if len(e.evento) > 35 else e.evento
    tooltip = (
        f"<b>{e.evento}</b><br>"
        f"E {round(e.energia * 10, 1)} · H {round(e.humor * 10, 1)} · St {round(e.estresse * 10, 1)}<br>"
        f"Sb {round(e.sensibilidade * 10, 1)} · Sr {round(e.serenidade * 10, 1)} · In {round(e.interesse * 10, 1)}<br>"
        f"{e.data_hora.strftime('%d/%m/%Y %H:%M')}"
    )
    if e.descricao:
        tooltip += f"<br><i>{e.descricao[:80]}</i>"
    tooltip += "<br><small style='opacity:0.6'>baseado na sua percepção</small>"

    return {
        "id": e.id,
        "label": label,
        "group": "evento",
        "color": _cor_no(e),
        "title": tooltip,
        "evento": e.evento,
        "timestamp": e.data_hora.isoformat(),
        "energia": e.energia,
        "humor": e.humor,
        "estresse": e.estresse,
        "sensibilidade": e.sensibilidade,
        "serenidade": e.serenidade,
        "interesse": e.interesse,
        "relacoes_contagem": contagem,
        "size": max(10, min(30, 10 + contagem * 4)),
    }


def _build_aresta(r: RelacaoEvento) -> dict:
    return {
        "id": r.id,
        "from": r.origem_id,
        "to": r.destino_id,
        "label": f"{round(r.intensidade * 100)}%",
        "value": r.intensidade,
        "intensidade": r.intensidade,
        "confiabilidade": r.confiabilidade,
        "motivo": r.motivo,
        "natureza": "percepcao",
        "interpretacao_confiavel": False,
        "color": {"color": COR_ARESTA, "opacity": 0.5 + r.intensidade * 0.5},
        "width": max(1, r.intensidade * 4),
        "dashes": r.confiabilidade < 0.8,
    }


@router.get("/")
def grafo_global(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    limite: int = Query(200, ge=10, le=1000),
    db: Session = Depends(get_db),
):
    relacoes = db.query(RelacaoEvento).all()
    evt_query = db.query(Evento).order_by(Evento.data_hora.desc())
    if data_inicio:
        evt_query = evt_query.filter(Evento.data_hora >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        evt_query = evt_query.filter(Evento.data_hora <= datetime.combine(data_fim, datetime.max.time()))

    todos_eventos = evt_query.limit(limite).all()
    evento_por_id = {e.id: e for e in todos_eventos}

    ids_com_relacao = {r.origem_id for r in relacoes} | {r.destino_id for r in relacoes}
    ids_faltando = ids_com_relacao - set(evento_por_id.keys())
    if ids_faltando:
        for e in db.query(Evento).filter(Evento.id.in_(ids_faltando)).all():
            evento_por_id[e.id] = e

    contagem: dict = {e_id: 0 for e_id in evento_por_id}
    relacoes_validas = []
    for r in relacoes:
        if r.origem_id in evento_por_id and r.destino_id in evento_por_id:
            relacoes_validas.append(r)
            contagem[r.origem_id] = contagem.get(r.origem_id, 0) + 1
            contagem[r.destino_id] = contagem.get(r.destino_id, 0) + 1

    nodes = [_build_no(e, contagem.get(e.id, 0)) for e in evento_por_id.values()]
    edges = [_build_aresta(r) for r in relacoes_validas]
    return {"nodes": nodes, "edges": edges, "total_nos": len(nodes), "total_arestas": len(edges)}


@router.get("/{evento_id}")
def grafo_local(
    evento_id: int,
    profundidade: int = Query(2, ge=1, le=4),
    db: Session = Depends(get_db),
):
    if not db.query(Evento).filter(Evento.id == evento_id).first():
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    visitados: Set[int] = {evento_id}
    fronteira: Set[int] = {evento_id}
    relacoes_coletadas = []

    for _ in range(profundidade):
        if not fronteira:
            break
        rels = db.query(RelacaoEvento).filter(
            (RelacaoEvento.origem_id.in_(fronteira)) | (RelacaoEvento.destino_id.in_(fronteira))
        ).all()
        nova_fronteira: Set[int] = set()
        for r in rels:
            relacoes_coletadas.append(r)
            for nid in [r.origem_id, r.destino_id]:
                if nid not in visitados:
                    nova_fronteira.add(nid)
                    visitados.add(nid)
        fronteira = nova_fronteira

    relacoes_unicas = {r.id: r for r in relacoes_coletadas}
    eventos = db.query(Evento).filter(Evento.id.in_(visitados)).all()
    contagem: dict = {e_id: 0 for e_id in visitados}
    for r in relacoes_unicas.values():
        contagem[r.origem_id] = contagem.get(r.origem_id, 0) + 1
        contagem[r.destino_id] = contagem.get(r.destino_id, 0) + 1

    nodes = []
    for e in eventos:
        no = _build_no(e, contagem.get(e.id, 0))
        if e.id == evento_id:
            no["color"] = "#C8A8E8"
            no["size"] = 28
        nodes.append(no)

    edges = [_build_aresta(r) for r in relacoes_unicas.values()]
    return {
        "nodes": nodes, "edges": edges,
        "evento_central": evento_id,
        "profundidade": profundidade,
        "total_nos": len(nodes),
        "total_arestas": len(edges),
    }
