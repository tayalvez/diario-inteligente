"""Camada de percepção subjetiva — análise de viés nos registros do usuário.

Os padrões aqui identificados refletem COMO o usuário registra e percebe
suas experiências, não a realidade objetiva dos fatos.
"""
import json
from collections import Counter, defaultdict
from datetime import timedelta
from typing import List, Dict, Any, Optional


def _tags(evt) -> List[str]:
    if not evt.tags_json:
        return []
    try:
        return json.loads(evt.tags_json) or []
    except Exception:
        return []


def _contexto(evt) -> Dict:
    if not evt.contexto_json:
        return {}
    try:
        return json.loads(evt.contexto_json) or {}
    except Exception:
        return {}


def _classificar_humor(humor: float) -> str:
    if humor < 0.35:
        return "negativo"
    elif humor > 0.65:
        return "positivo"
    return "neutro"


def calcular_vies_valencia(eventos) -> Dict[str, Any]:
    """Viés de valência: distribuição de humor positivo/neutro/negativo nos registros."""
    if not eventos:
        return {"negativo": 0.0, "neutro": 0.0, "positivo": 0.0, "total": 0, "insight": None}

    contagem = Counter(
        _classificar_humor(e.humor) for e in eventos if e.humor is not None
    )
    total = sum(contagem.values())

    if total == 0:
        return {"negativo": 0.0, "neutro": 0.0, "positivo": 0.0, "total": 0, "insight": None}

    neg = contagem.get("negativo", 0) / total
    pos = contagem.get("positivo", 0) / total
    neu = contagem.get("neutro", 0) / total

    insight = None
    if neg >= 0.65:
        insight = (
            f"{round(neg * 100)}% dos seus registros descrevem estados percebidos como negativos. "
            "Experiências com carga emocional intensa tendem a ser anotadas com mais frequência — "
            "isso é um padrão comum de percepção, não necessariamente um reflexo da sua realidade."
        )
    elif pos >= 0.65:
        insight = (
            f"{round(pos * 100)}% dos seus registros descrevem estados percebidos positivamente. "
            "Momentos marcantes positivos parecem chamar mais sua atenção no registro."
        )
    elif neg >= 0.5:
        insight = (
            "Experiências percebidas como negativas aparecem com frequência nos seus registros — "
            "o que pode indicar viés de atenção emocional."
        )

    return {
        "negativo": round(neg, 3),
        "neutro": round(neu, 3),
        "positivo": round(pos, 3),
        "total": total,
        "insight": insight,
    }


def calcular_vies_registro(eventos) -> Dict[str, Any]:
    """Viés de registro: frequência de tags e contextos nos registros."""
    if not eventos:
        return {
            "total_eventos": 0,
            "tags_frequentes": [],
            "contextos_frequentes": [],
            "aviso": None,
        }

    total = len(eventos)

    # Tags mais frequentes
    todas_tags = []
    for e in eventos:
        todas_tags.extend(_tags(e))

    top_tags = []
    if todas_tags:
        for tag, count in Counter(todas_tags).most_common(5):
            top_tags.append({
                "tag": tag,
                "contagem": count,
                "proporcao": round(count / total, 3),
            })

    # Contextos mais frequentes (valores do dict de contexto)
    contextos_vals = []
    for e in eventos:
        for v in _contexto(e).values():
            if isinstance(v, str) and v.strip():
                contextos_vals.append(v.lower().strip())

    top_contextos = []
    if contextos_vals:
        for ctx_val, count in Counter(contextos_vals).most_common(5):
            top_contextos.append({
                "contexto": ctx_val,
                "contagem": count,
                "proporcao": round(count / total, 3),
            })

    aviso = None
    if top_tags:
        top_tag = top_tags[0]
        if top_tag["proporcao"] >= 0.5:
            aviso = (
                f"A tag '{top_tag['tag']}' aparece em {round(top_tag['proporcao'] * 100)}% dos registros. "
                "Isso não significa que esse contexto domina sua vida — apenas que é registrado com mais frequência."
            )

    return {
        "total_eventos": total,
        "tags_frequentes": top_tags,
        "contextos_frequentes": top_contextos,
        "aviso": aviso,
    }


def calcular_vies_intensidade(eventos) -> Dict[str, Any]:
    """Viés de intensidade: proporção de estados extremos vs moderados nos registros."""
    if not eventos:
        return {"pct_extremos": 0.0, "total_extremos": 0, "total": 0, "medias": {}, "insight": None}

    total = len(eventos)

    extremos = sum(
        1 for e in eventos
        if (e.estresse is not None and e.estresse >= 0.75)
        or (e.humor is not None and e.humor <= 0.25)
        or (e.energia is not None and e.energia <= 0.25)
        or (e.humor is not None and e.humor >= 0.85)
        or (e.energia is not None and e.energia >= 0.85)
        or (getattr(e, "serenidade", None) is not None and getattr(e, "serenidade") <= 0.25)
        or (getattr(e, "interesse", None) is not None and getattr(e, "interesse") <= 0.25)
        or (getattr(e, "sensibilidade", None) is not None and getattr(e, "sensibilidade") >= 0.85)
    )

    pct_extremos = round(extremos / total, 3)

    medias: Dict[str, Optional[float]] = {}
    for dim in ["energia", "humor", "estresse", "sensibilidade", "serenidade", "interesse"]:
        vals = [getattr(e, dim, None) for e in eventos if getattr(e, dim, None) is not None]
        medias[dim] = round(sum(vals) / len(vals), 3) if vals else None

    insight = None
    if pct_extremos >= 0.5:
        insight = (
            "Grande parte dos seus registros descreve estados intensos. "
            "Momentos de alta carga emocional — estresse elevado, humor muito baixo ou muito alto — "
            "tendem a motivar mais o ato de registrar do que estados neutros."
        )
    elif pct_extremos <= 0.15:
        insight = "Seus registros tendem a descrever estados moderados, sem muitos extremos emocionais."

    return {
        "pct_extremos": pct_extremos,
        "total_extremos": extremos,
        "total": total,
        "medias": medias,
        "insight": insight,
    }


def gerar_insights_metapercepao(eventos, vies_valencia: Dict) -> List[Dict[str, Any]]:
    """Gera análises sobre como o usuário percebe e registra suas experiências."""
    insights = []

    if not eventos:
        return insights

    total = len(eventos)
    neg = vies_valencia.get("negativo", 0)
    pos = vies_valencia.get("positivo", 0)

    if neg >= 0.55:
        insights.append({
            "tipo": "metapercepao_valencia_negativa",
            "titulo": "Você registra mais experiências percebidas como negativas",
            "descricao": (
                f"{round(neg * 100)}% dos seus registros descrevem estados percebidos como negativos. "
                "Experiências com carga emocional tendem a chamar mais atenção e ser registradas com mais frequência — "
                "isso é um padrão de percepção, não necessariamente um retrato da sua realidade."
            ),
            "natureza": "percepcao",
            "interpretacao_confiavel": False,
        })
    elif pos >= 0.6:
        insights.append({
            "tipo": "metapercepao_valencia_positiva",
            "titulo": "Seus registros tendem a descrever experiências positivas",
            "descricao": (
                f"{round(pos * 100)}% dos seus registros descrevem estados percebidos positivamente. "
                "Isso pode refletir um período favorável — ou que os momentos marcantes positivos "
                "motivam mais o registro no seu caso."
            ),
            "natureza": "percepcao",
            "interpretacao_confiavel": False,
        })

    if total >= 5:
        datas = sorted([e.data_hora for e in eventos])
        periodo_dias = max((datas[-1] - datas[0]).days, 1)
        freq = total / periodo_dias

        if freq < 0.4:
            insights.append({
                "tipo": "metapercepao_frequencia_baixa",
                "titulo": "Eventos intensos têm maior probabilidade de serem registrados",
                "descricao": (
                    f"Com {total} registros em ~{periodo_dias} dias, muitos momentos ficam sem anotação. "
                    "Experiências mais intensas — especialmente as difíceis — tendem a motivar mais o ato de registrar."
                ),
                "natureza": "percepcao",
                "interpretacao_confiavel": False,
            })

    # Insight de contexto dominante
    todos_contextos = []
    for e in eventos:
        for v in (json.loads(e.contexto_json) if e.contexto_json else {}).values():
            if isinstance(v, str):
                todos_contextos.append(v.lower().strip())

    if todos_contextos:
        mais_comum, count = Counter(todos_contextos).most_common(1)[0]
        prop = count / total
        if prop >= 0.4:
            insights.append({
                "tipo": "metapercepao_contexto_dominante",
                "titulo": f"O contexto '{mais_comum}' aparece frequentemente nos seus registros",
                "descricao": (
                    f"'{mais_comum.capitalize()}' está presente em {round(prop * 100)}% dos seus registros. "
                    "Nos seus registros, emoções negativas aparecem frequentemente associadas a esse contexto — "
                    "mas não sabemos se esse contexto ocupa esse espaço na sua vida, apenas que é registrado assim."
                ),
                "natureza": "percepcao",
                "interpretacao_confiavel": False,
            })

    return insights


def calcular_perception_bias(eventos, dias: int = 60) -> Dict[str, Any]:
    """Retorna análise completa de viés de percepção subjetiva."""
    if not eventos:
        return {
            "total_eventos": 0,
            "periodo_dias": dias,
            "vies_valencia": {},
            "vies_registro": {},
            "vies_intensidade": {},
            "insights_metapercepao": [],
            "aviso_geral": "Registre mais eventos para obter a análise de percepção.",
            "natureza": "percepcao",
            "interpretacao_confiavel": False,
        }

    vies_valencia = calcular_vies_valencia(eventos)
    vies_registro = calcular_vies_registro(eventos)
    vies_intensidade = calcular_vies_intensidade(eventos)
    insights = gerar_insights_metapercepao(eventos, vies_valencia)

    return {
        "total_eventos": len(eventos),
        "periodo_dias": dias,
        "vies_valencia": vies_valencia,
        "vies_registro": vies_registro,
        "vies_intensidade": vies_intensidade,
        "insights_metapercepao": insights,
        "aviso_geral": (
            "Esses dados refletem seus registros, não necessariamente a realidade. "
            "Padrões nos registros revelam o que chama mais sua atenção emocionalmente."
        ),
        "natureza": "percepcao",
        "interpretacao_confiavel": False,
    }
