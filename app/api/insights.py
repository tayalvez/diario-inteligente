"""API de Insights — análise de padrões, correlações e predições."""
import json
import re
import unicodedata
from datetime import date, timedelta, datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db, Evento, RelacaoEvento, InsightGerado

router = APIRouter(prefix="/api/insights", tags=["Insights e IA"])


def _media(lst):
    vals = [v for v in lst if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^\w\s]", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def _tokens_relevantes(texto: str) -> list[str]:
    stop = {
        "de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "em", "no", "na",
        "nos", "nas", "um", "uma", "para", "por", "com", "sem", "que", "pra", "pro",
        "foi", "era", "ser", "estar", "mais", "menos", "muito", "muita", "dia",
    }
    return [
        token for token in _normalizar_texto(texto).split()
        if len(token) >= 4 and token not in stop
    ]


def _padrao_horario_registro(eventos) -> Dict[str, Any] | None:
    from collections import defaultdict

    periodos = {
        "manhã": (6, 12),
        "tarde": (12, 18),
        "noite": (18, 24),
        "madrugada": (0, 6),
    }
    contagem = defaultdict(int)
    for e in eventos:
        hora = e.data_hora.hour
        for nome, (inicio, fim) in periodos.items():
            if inicio <= hora < fim:
                contagem[nome] += 1
                break

    if len(contagem) < 2:
        return None

    mais = max(contagem, key=contagem.get)
    menos = min(contagem, key=contagem.get)
    total = sum(contagem.values())
    proporcao = contagem[mais] / total if total else 0
    if proporcao < 0.35:
        return None

    return {
        "tipo": "horario_registro",
        "titulo": f"Seus registros se concentram mais no período da {mais}",
        "descricao": (
            f"Nos últimos registros, {round(proporcao * 100)}% foram feitos no período da {mais} "
            f"({contagem[mais]} anotações), enquanto o período menos frequente foi {menos} "
            f"({contagem[menos]}). Isso sugere um padrão de quando você tende a registrar."
        ),
        "dados": dict(contagem),
        "relevancia": min(0.82, 0.5 + proporcao * 0.5),
    }


def _padrao_tema_recorrente(eventos) -> Dict[str, Any] | None:
    from collections import Counter

    total = len(eventos)
    tags = Counter()
    termos = Counter()

    for e in eventos:
        if e.tags_json:
            try:
                for tag in json.loads(e.tags_json) or []:
                    tag_norm = _normalizar_texto(str(tag))
                    if tag_norm:
                        tags[tag_norm] += 1
            except Exception:
                pass
        if e.descricao:
            for token in set(_tokens_relevantes(e.descricao)):
                termos[token] += 1

    candidatos = []
    if tags:
        tag, count = tags.most_common(1)[0]
        candidatos.append(("tag", tag, count))
    if termos:
        termo, count = termos.most_common(1)[0]
        candidatos.append(("termo", termo, count))

    if not candidatos:
        return None

    tipo, valor, count = max(candidatos, key=lambda item: item[2])
    proporcao = count / total if total else 0
    if count < 2 or proporcao < 0.2:
        return None

    label = "tag" if tipo == "tag" else "tema"
    return {
        "tipo": f"{tipo}_recorrente",
        "titulo": f"'{valor}' aparece como {label} recorrente nos registros",
        "descricao": (
            f"'{valor}' aparece em {count} dos últimos {total} registros "
            f"({round(proporcao * 100)}%). Isso sugere um tema recorrente nas suas anotações recentes."
        ),
        "dados": {tipo: valor, "contagem": count, "proporcao": round(proporcao, 3)},
        "relevancia": min(0.84, 0.45 + proporcao * 0.8),
    }


def _padrao_relacao_dominante(eventos) -> Dict[str, Any] | None:
    from app.ml.insights_comportamentais import _coletar_relacoes_unicas

    relacoes = [r for r in _coletar_relacoes_unicas(eventos) if r["score_evidencia"] >= 2.0]
    if not relacoes:
        return None

    melhor = max(
        relacoes,
        key=lambda r: (r["score_evidencia"], r["num_fatores"], r["intensidade"], r["confiabilidade"]),
    )
    return {
        "tipo": "relacao_dominante",
        "titulo": f"{melhor['par']} se destaca como conexão recorrente do período",
        "descricao": (
            f"Essa relação reúne {melhor['num_fatores']} evidência(s), intensidade de "
            f"{melhor['intensidade']:.2f} e confiabilidade de {melhor['confiabilidade']:.2f}. "
            f"Hoje, ela é a associação mais forte entre suas anotações recentes."
        ),
        "dados": {
            "par": melhor["par"],
            "num_fatores": melhor["num_fatores"],
            "intensidade": round(melhor["intensidade"], 3),
            "confiabilidade": round(melhor["confiabilidade"], 3),
        },
        "relevancia": min(0.9, 0.45 + melhor["score_evidencia"] * 0.08),
    }


# ── Correlações entre dimensões ───────────────────────────────────────────────

@router.get("/correlacoes")
def analisar_correlacoes(
    dias: int = Query(60, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        from app.ml.correlacao import calcular_correlacoes_dimensoes
        data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
        return calcular_correlacoes_dimensoes(db, data_inicio)
    except Exception as e:
        return {"erro": str(e), "correlacoes": []}


# ── Padrões ───────────────────────────────────────────────────────────────────

@router.get("/padroes")
def detectar_padroes(
    dias: int = Query(60, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    from collections import defaultdict
    from sqlalchemy.orm import joinedload

    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = (
        db.query(Evento)
        .options(
            joinedload(Evento.relacoes_origem).joinedload(RelacaoEvento.evento_destino),
            joinedload(Evento.relacoes_destino).joinedload(RelacaoEvento.evento_origem),
        )
        .filter(Evento.data_hora >= data_inicio)
        .all()
    )

    if not eventos:
        return {"periodo_dias": dias, "padroes": [], "total": 0}

    padroes = []

    # 1. Frequência por dia da semana
    dias_labels = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    contagem_dia: Dict[int, int] = defaultdict(int)
    for e in eventos:
        contagem_dia[e.data_hora.weekday()] += 1

    if len(contagem_dia) >= 3:
        mais_ativo = max(contagem_dia, key=contagem_dia.get)
        menos_ativo = min(contagem_dia, key=contagem_dia.get)
        padroes.append({
            "tipo": "frequencia_dia_semana",
            "titulo": "Padrão de atividade semanal",
            "descricao": (
                f"Você registra mais eventos nas {dias_labels[mais_ativo]}s "
                f"({contagem_dia[mais_ativo]} registros) e menos nas "
                f"{dias_labels[menos_ativo]}s ({contagem_dia[menos_ativo]} registros)."
            ),
            "dados": {dias_labels[k]: v for k, v in contagem_dia.items()},
            "relevancia": 0.6,
        })

    horario = _padrao_horario_registro(eventos)
    if horario:
        padroes.append(horario)

    relacao_dominante = _padrao_relacao_dominante(eventos)
    if relacao_dominante:
        padroes.append(relacao_dominante)

    tema_recorrente = _padrao_tema_recorrente(eventos)
    if tema_recorrente:
        padroes.append(tema_recorrente)

    # 2. Tendência das dimensões
    ordered = sorted(eventos, key=lambda e: e.data_hora)
    if len(ordered) >= 6:
        meio = len(ordered) // 2
        antigos = ordered[:meio]
        recentes = ordered[meio:]

        for dim, label, inv in [
            ("energia", "energia", False), ("humor", "humor", False), ("estresse", "estresse", True),
            ("serenidade", "serenidade", False), ("interesse", "interesse", False), ("sensibilidade", "sensibilidade", False),
        ]:
            media_ant = _media([getattr(e, dim, None) for e in antigos])
            media_rec = _media([getattr(e, dim, None) for e in recentes])
            if media_ant is not None and media_rec is not None:
                diff = round(media_rec - media_ant, 2)
                if abs(diff) >= 0.1:
                    direcao = "melhorando" if (diff > 0 and not inv) or (diff < 0 and inv) else "piorando"
                    padroes.append({
                        "tipo": f"tendencia_{dim}",
                        "titulo": f"{label.capitalize()} percebida {direcao} no período",
                        "descricao": (
                            f"Nos seus registros recentes, {label} percebida média é {media_rec:.2f} "
                            f"(vs {media_ant:.2f} no início do período). "
                            f"Variação de {'+' if diff > 0 else ''}{diff} nos registros."
                        ),
                        "dados": {"media_antiga": media_ant, "media_recente": media_rec, "variacao": diff},
                        "relevancia": 0.85,
                    })

    # 3. Dimensões consistentemente em nível crítico
    medias_dims = {
        dim: _media([getattr(e, dim, None) for e in eventos])
        for dim in ("energia", "humor", "estresse", "serenidade", "interesse", "sensibilidade")
    }

    if medias_dims["energia"] is not None and medias_dims["energia"] <= 0.35:
        padroes.append({
            "tipo": "energia_baixa",
            "titulo": "Energia percebida frequentemente baixa nos registros",
            "descricao": f"Nos seus registros dos últimos {dias} dias, energia percebida média aparece em {medias_dims['energia']:.2f}. Isso pode indicar que você tem percebido e registrado estados de baixa energia com frequência.",
            "dados": {"media": medias_dims["energia"]},
            "relevancia": 0.8,
        })
    if medias_dims["humor"] is not None and medias_dims["humor"] <= 0.35:
        padroes.append({
            "tipo": "humor_baixo",
            "titulo": "Humor percebido frequentemente baixo nos registros",
            "descricao": f"Nos seus registros dos últimos {dias} dias, humor percebido médio aparece em {medias_dims['humor']:.2f}. Você tem registrado estados de humor baixo com consistência.",
            "dados": {"media": medias_dims["humor"]},
            "relevancia": 0.85,
        })
    if medias_dims["estresse"] is not None and medias_dims["estresse"] >= 0.7:
        padroes.append({
            "tipo": "estresse_alto",
            "titulo": "Estresse percebido frequentemente alto nos registros",
            "descricao": f"Nos seus registros, estresse percebido médio aparece em {medias_dims['estresse']:.2f}. Você tem registrado estados de alta pressão com frequência.",
            "dados": {"media": medias_dims["estresse"]},
            "relevancia": 0.9,
        })
    if medias_dims["interesse"] is not None and medias_dims["interesse"] <= 0.35:
        padroes.append({
            "tipo": "interesse_baixo_persistente",
            "titulo": "Baixa vontade de engajamento persistente nos registros",
            "descricao": f"Nos seus registros dos últimos {dias} dias, interesse (vontade de engajamento) médio aparece em {medias_dims['interesse']:.2f}. Você tem registrado baixa disposição para se engajar com frequência — padrão distinto de humor baixo.",
            "dados": {"media": medias_dims["interesse"]},
            "relevancia": 0.85,
        })
    if medias_dims["serenidade"] is not None and medias_dims["serenidade"] <= 0.35:
        padroes.append({
            "tipo": "serenidade_baixa_persistente",
            "titulo": "Serenidade persistentemente baixa nos registros",
            "descricao": f"Nos seus registros dos últimos {dias} dias, serenidade percebida média aparece em {medias_dims['serenidade']:.2f}. Você tem registrado estados de agitação ou irritação com frequência.",
            "dados": {"media": medias_dims["serenidade"]},
            "relevancia": 0.85,
        })
    if medias_dims["sensibilidade"] is not None and medias_dims["sensibilidade"] >= 0.70:
        padroes.append({
            "tipo": "sensibilidade_alta_persistente",
            "titulo": "Alta sensibilidade ao ambiente persistente nos registros",
            "descricao": f"Nos seus registros dos últimos {dias} dias, sensibilidade ao ambiente média aparece em {medias_dims['sensibilidade']:.2f}. Você tem registrado alta receptividade ao entorno com frequência — pode indicar sobrecarga perceptiva persistente.",
            "dados": {"media": medias_dims["sensibilidade"]},
            "relevancia": 0.75,
        })

    return {
        "periodo_dias": dias,
        "padroes": sorted(padroes, key=lambda x: x["relevancia"], reverse=True),
        "total": len(padroes),
    }


# ── Recomendações ─────────────────────────────────────────────────────────────

@router.get("/recomendacoes")
def gerar_recomendacoes(db: Session = Depends(get_db)) -> Dict[str, Any]:
    data_inicio = datetime.combine(date.today() - timedelta(days=14), datetime.min.time())
    eventos = db.query(Evento).filter(Evento.data_hora >= data_inicio).all()

    if not eventos:
        return {
            "recomendacoes": [{
                "categoria": "geral",
                "titulo": "Comece a registrar!",
                "descricao": "Registre seu primeiro evento para começar a receber recomendações personalizadas.",
                "prioridade": "alta",
            }],
            "baseado_em_eventos": 0,
        }

    recomendacoes = []

    medias_rec = {
        dim: _media([getattr(e, dim, None) for e in eventos])
        for dim in ("energia", "humor", "estresse", "serenidade", "interesse", "sensibilidade")
    }

    if medias_rec["energia"] is not None and medias_rec["energia"] < 0.35:
        recomendacoes.append({
            "categoria": "energia",
            "titulo": "Energia percebida baixa nos seus registros recentes",
            "descricao": f"Nos últimos 14 dias, você tem registrado energia percebida média de {medias_rec['energia']:.2f}. Seus registros sugerem que você tem se percebido com pouca energia — pode valer atenção ao descanso.",
            "prioridade": "alta",
        })
    if medias_rec["humor"] is not None and medias_rec["humor"] < 0.35:
        recomendacoes.append({
            "categoria": "humor",
            "titulo": "Humor percebido baixo nos seus registros recentes",
            "descricao": f"Nos últimos 14 dias, você tem registrado humor percebido médio de {medias_rec['humor']:.2f}. Seus registros mostram que você tem percebido estados de humor baixo com frequência.",
            "prioridade": "alta",
        })
    if medias_rec["estresse"] is not None and medias_rec["estresse"] > 0.7:
        recomendacoes.append({
            "categoria": "estresse",
            "titulo": "Estresse percebido elevado nos seus registros recentes",
            "descricao": f"Nos últimos 14 dias, você tem registrado estresse percebido médio de {medias_rec['estresse']:.2f}. Seus registros indicam que você tem se percebido sob alta pressão com frequência.",
            "prioridade": "alta",
        })
    if medias_rec["interesse"] is not None and medias_rec["interesse"] < 0.35:
        recomendacoes.append({
            "categoria": "engajamento",
            "titulo": "Baixa vontade de engajamento nos seus registros recentes",
            "descricao": f"Nos últimos 14 dias, você tem registrado interesse (vontade de engajamento) médio de {medias_rec['interesse']:.2f}. Seus registros sugerem baixa disposição persistente — distinto de humor baixo.",
            "prioridade": "alta",
        })
    if medias_rec["serenidade"] is not None and medias_rec["serenidade"] < 0.35:
        recomendacoes.append({
            "categoria": "serenidade",
            "titulo": "Serenidade percebida baixa nos seus registros recentes",
            "descricao": f"Nos últimos 14 dias, você tem registrado serenidade percebida média de {medias_rec['serenidade']:.2f}. Seus registros mostram agitação ou irritação persistente nos registros.",
            "prioridade": "alta",
        })
    if medias_rec["sensibilidade"] is not None and medias_rec["sensibilidade"] > 0.75:
        recomendacoes.append({
            "categoria": "sobrecarga_sensorial",
            "titulo": "Alta sensibilidade ao ambiente nos seus registros recentes",
            "descricao": f"Nos últimos 14 dias, você tem registrado sensibilidade ao ambiente média de {medias_rec['sensibilidade']:.2f}. Alta sensibilidade pode ser contextual e positiva, mas quando persistente pode indicar sobrecarga perceptiva.",
            "prioridade": "media",
        })

    datas_com_eventos = {e.data_hora.date() for e in eventos}
    if len(datas_com_eventos) < 5:
        recomendacoes.append({
            "categoria": "habito",
            "titulo": "Registre mais frequentemente",
            "descricao": f"Você registrou em apenas {len(datas_com_eventos)} dos últimos 14 dias. Quanto mais registros, mais rica a análise de percepção.",
            "prioridade": "baixa",
        })

    if not recomendacoes:
        recomendacoes.append({
            "categoria": "geral",
            "titulo": "Continue registrando!",
            "descricao": "Seus registros estão consistentes e os indicadores percebidos parecem equilibrados. Continue com os bons hábitos de registro!",
            "prioridade": "baixa",
        })

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    recomendacoes.sort(key=lambda x: ordem.get(x["prioridade"], 3))

    return {
        "recomendacoes": recomendacoes,
        "baseado_em_eventos": len(eventos),
    }


# ── Similaridade semântica ────────────────────────────────────────────────────

@router.get("/similaridade/{evento_id}")
def eventos_similares(
    evento_id: int,
    top_n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        return {"erro": "Evento não encontrado", "similares": []}

    if not evento.embedding:
        return {"mensagem": "Evento sem embedding ainda.", "similares": []}

    try:
        from app.ml.nlp import similaridade_coseno
        vec_origem = json.loads(evento.embedding)

        candidatos = db.query(Evento).filter(
            Evento.id != evento_id, Evento.embedding.isnot(None)
        ).all()

        resultados = []
        for c in candidatos:
            try:
                vec = json.loads(c.embedding)
                sim = similaridade_coseno(vec_origem, vec)
                resultados.append({
                    "id": c.id,
                    "evento": c.evento,
                    "descricao": c.descricao,
                    "data_hora": c.data_hora.isoformat(),
                    "similaridade": round(sim, 4),
                })
            except Exception:
                continue

        resultados.sort(key=lambda x: x["similaridade"], reverse=True)
        return {"evento_id": evento_id, "similares": resultados[:top_n]}

    except Exception as e:
        return {"erro": str(e), "similares": []}


# ── Similaridade / enriquecimento do grafo ────────────────────────────────────

@router.post("/similaridade/enriquecer")
def enriquecer_grafo_similaridade(
    dias: int = Query(90, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Calcula similaridade entre eventos e cria relações automaticamente."""
    from app.ml.similaridade import gerar_relacoes_similaridade
    from app.models.database import RelacaoEvento

    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = db.query(Evento).filter(Evento.data_hora >= data_inicio).all()

    if len(eventos) < 2:
        return {"criadas": 0, "mensagem": "Eventos insuficientes para análise."}

    # Relações já existentes
    ids = [e.id for e in eventos]
    existentes = db.query(RelacaoEvento).filter(
        RelacaoEvento.origem_id.in_(ids),
        RelacaoEvento.destino_id.in_(ids),
    ).all()
    pares_existentes = {(r.origem_id, r.destino_id) for r in existentes}

    novas = gerar_relacoes_similaridade(eventos, pares_existentes)

    criadas = 0
    for rel in novas:
        # Verificar novamente para evitar race condition
        existe = db.query(RelacaoEvento).filter(
            RelacaoEvento.origem_id == rel["origem_id"],
            RelacaoEvento.destino_id == rel["destino_id"],
        ).first()
        if existe:
            continue
        db.add(RelacaoEvento(
            origem_id=rel["origem_id"],
            destino_id=rel["destino_id"],
            intensidade=rel["intensidade"],
            confiabilidade=rel["confiabilidade"],
        ))
        criadas += 1

    db.commit()

    return {
        "criadas": criadas,
        "analisados": len(eventos),
        "mensagem": f"{criadas} relação(ões) de similaridade criada(s) entre {len(eventos)} eventos.",
    }


@router.get("/similaridade/preview")
def preview_similaridade(
    dias: int = Query(90, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Mostra as relações que seriam criadas sem salvar."""
    from app.ml.similaridade import gerar_relacoes_similaridade
    from app.models.database import RelacaoEvento

    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = db.query(Evento).filter(Evento.data_hora >= data_inicio).all()
    evt_map = {e.id: e.evento for e in eventos}

    if len(eventos) < 2:
        return {"total": 0, "relacoes": []}

    ids = [e.id for e in eventos]
    existentes = db.query(RelacaoEvento).filter(
        RelacaoEvento.origem_id.in_(ids),
        RelacaoEvento.destino_id.in_(ids),
    ).all()
    pares_existentes = {(r.origem_id, r.destino_id) for r in existentes}

    novas = gerar_relacoes_similaridade(eventos, pares_existentes)

    return {
        "total": len(novas),
        "analisados": len(eventos),
        "relacoes": [
            {
                "origem": evt_map.get(r["origem_id"], str(r["origem_id"])),
                "destino": evt_map.get(r["destino_id"], str(r["destino_id"])),
                "intensidade": r["intensidade"],
                "confiabilidade": r["confiabilidade"],
            }
            for r in novas
        ],
    }


# ── Insights comportamentais ──────────────────────────────────────────────────

@router.get("/qualidade-relacoes")
def qualidade_relacoes(
    dias: int = Query(60, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    from app.ml.insights_comportamentais import gerar_qualidade_relacoes
    from sqlalchemy.orm import joinedload
    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = (
        db.query(Evento)
        .options(
            joinedload(Evento.relacoes_origem).joinedload(RelacaoEvento.evento_destino),
            joinedload(Evento.relacoes_destino).joinedload(RelacaoEvento.evento_origem),
        )
        .filter(Evento.data_hora >= data_inicio)
        .all()
    )
    return gerar_qualidade_relacoes(eventos)


@router.get("/relacoes-insights")
def insights_relacoes(
    dias: int = Query(60, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    from app.ml.insights_comportamentais import gerar_insights_relacoes
    from sqlalchemy.orm import joinedload
    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = (
        db.query(Evento)
        .options(
            joinedload(Evento.relacoes_origem).joinedload(RelacaoEvento.evento_destino),
            joinedload(Evento.relacoes_destino).joinedload(RelacaoEvento.evento_origem),
        )
        .filter(Evento.data_hora >= data_inicio)
        .all()
    )
    return gerar_insights_relacoes(eventos)


@router.get("/comportamentais")
def insights_comportamentais(
    dias: int = Query(60, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    from app.ml.insights_comportamentais import gerar_insights_comportamentais
    from sqlalchemy.orm import joinedload
    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = (
        db.query(Evento)
        .options(
            joinedload(Evento.relacoes_origem).joinedload(RelacaoEvento.evento_destino),
            joinedload(Evento.relacoes_destino).joinedload(RelacaoEvento.evento_origem),
        )
        .filter(Evento.data_hora >= data_inicio)
        .all()
    )
    padroes = gerar_insights_comportamentais(eventos)
    return {"padroes": padroes, "total": len(padroes), "periodo_dias": dias}


# ── Percepção subjetiva ───────────────────────────────────────────────────────

@router.get("/perception-bias")
def perception_bias(
    dias: int = Query(60, ge=14, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Análise de viés de percepção — como o usuário registra e percebe experiências."""
    from app.ml.perception_bias import calcular_perception_bias
    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())
    eventos = db.query(Evento).filter(Evento.data_hora >= data_inicio).all()
    return calcular_perception_bias(eventos, dias)


# ── Histórico de insights ─────────────────────────────────────────────────────

@router.get("/historico")
def historico_insights(
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[Dict]:
    insights = db.query(InsightGerado).order_by(InsightGerado.gerado_em.desc()).limit(limite).all()
    return [{
        "id": i.id, "tipo": i.tipo, "titulo": i.titulo,
        "descricao": i.descricao, "relevancia": i.relevancia,
        "gerado_em": i.gerado_em.isoformat(),
    } for i in insights]
