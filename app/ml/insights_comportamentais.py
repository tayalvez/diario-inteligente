"""Insights comportamentais — análises acionáveis sobre padrões de estado."""
import json
import math
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def _media(lst):
    vals = [v for v in lst if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _desvio(lst):
    vals = [v for v in lst if v is not None]
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def _bem_estar(evt) -> Optional[float]:
    """Score composto de bem-estar: média das dimensões positivas com estresse invertido."""
    vals = []
    for dim in ("humor", "energia", "serenidade", "interesse", "sensibilidade"):
        v = getattr(evt, dim, None)
        if v is not None:
            vals.append(v)
    if getattr(evt, "estresse", None) is not None:
        vals.append(1 - evt.estresse)
    return round(sum(vals) / len(vals), 3) if vals else None


def _resumo_dims(evts) -> str:
    """Linha resumida das médias de todas as dimensões para usar em descrições de insight."""
    nomes = [
        ("humor", "humor"),
        ("energia", "energia"),
        ("estresse", "estresse"),
        ("serenidade", "serenidade"),
        ("interesse", "interesse"),
        ("sensibilidade", "sensibilidade"),
    ]
    partes = []
    for attr, label in nomes:
        m = _media([getattr(e, attr, None) for e in evts])
        if m is not None:
            partes.append(f"{label} {m:.2f}")
    return ", ".join(partes)


def _tags(evt) -> List[str]:
    if not evt.tags_json:
        return []
    try:
        return json.loads(evt.tags_json) or []
    except Exception:
        return []


def _coletar_relacoes_unicas(eventos) -> List[Dict[str, Any]]:
    """Normaliza relações únicas para reuse nas análises do grafo."""
    relacoes = []
    vistas = set()

    for evt in eventos:
        for r in list(evt.relacoes_origem) + list(evt.relacoes_destino):
            if r.id in vistas:
                continue
            vistas.add(r.id)

            origem_label = None
            destino_label = None

            if getattr(r, "evento_origem", None):
                origem_label = r.evento_origem.evento
            elif r.origem_id == getattr(evt, "id", None):
                origem_label = evt.evento

            if getattr(r, "evento_destino", None):
                destino_label = r.evento_destino.evento
            elif r.destino_id == getattr(evt, "id", None):
                destino_label = evt.evento

            if not origem_label and destino_label:
                origem_label = evt.evento
            if not destino_label and origem_label:
                destino_label = evt.evento

            if origem_label and destino_label:
                labels = sorted([origem_label, destino_label])
                par = f"{labels[0]} ↔ {labels[1]}"
            else:
                par = origem_label or destino_label or evt.evento

            fatores = [p.strip() for p in (r.motivo or "").split(";") if p.strip()]
            num_fatores = len(fatores)
            intensidade = r.intensidade or 0
            confiabilidade = r.confiabilidade or 0

            relacoes.append({
                "id": r.id,
                "origem_id": r.origem_id,
                "destino_id": r.destino_id,
                "origem_label": origem_label,
                "destino_label": destino_label,
                "par": par,
                "num_fatores": num_fatores,
                "fatores": fatores,
                "motivo": r.motivo,
                "intensidade": intensidade,
                "confiabilidade": confiabilidade,
                "manual": confiabilidade >= 1.0,
                "automatica": confiabilidade < 1.0,
                "score_evidencia": round(
                    num_fatores * 1.0 + intensidade * 2.2 + confiabilidade * 0.8,
                    4,
                ),
            })

    return relacoes


# ── 1. Tendência recente ──────────────────────────────────────────────────────

def _tendencia_recente(eventos) -> Optional[Dict]:
    """Compara última semana com a semana anterior para detectar melhora ou piora."""
    agora = eventos[-1].data_hora
    limite_recente = agora - timedelta(days=7)
    limite_anterior = agora - timedelta(days=14)

    recentes = [e for e in eventos if e.data_hora >= limite_recente]
    anteriores = [e for e in eventos if limite_anterior <= e.data_hora < limite_recente]

    if len(recentes) < 2 or len(anteriores) < 2:
        return None

    scores_r = [s for e in recentes if (s := _bem_estar(e)) is not None]
    scores_a = [s for e in anteriores if (s := _bem_estar(e)) is not None]

    if not scores_r or not scores_a:
        return None

    media_r = sum(scores_r) / len(scores_r)
    media_a = sum(scores_a) / len(scores_a)
    delta = media_r - media_a

    if abs(delta) < 0.05:
        return None

    pct = abs(delta) / max(media_a, 0.01)
    melhorando = delta > 0

    # Qual dimensão mais mudou
    dims = {}
    for dim, inv in [("humor", False), ("energia", False), ("estresse", True), ("serenidade", False), ("interesse", False), ("sensibilidade", False)]:
        vr = _media([getattr(e, dim, None) for e in recentes])
        va = _media([getattr(e, dim, None) for e in anteriores])
        if vr is not None and va is not None:
            diff = (vr - va) if not inv else (va - vr)
            dims[dim] = diff

    dim_principal = max(dims, key=lambda d: abs(dims[d])) if dims else None
    labels = {"humor": "humor", "energia": "energia", "estresse": "estresse", "serenidade": "serenidade", "interesse": "interesse", "sensibilidade": "sensibilidade"}

    if melhorando:
        titulo = f"Registros desta semana mostram bem-estar percebido {pct:.0%} mais alto"
        descricao = (
            f"Comparando os {len(recentes)} registros dos últimos 7 dias com os "
            f"{len(anteriores)} da semana anterior, o bem-estar percebido nos registros subiu "
            f"{pct:.0%}."
        )
        if dim_principal:
            descricao += f" A maior variação foi no {labels[dim_principal]} percebido."
    else:
        titulo = f"Registros desta semana mostram bem-estar percebido {pct:.0%} mais baixo"
        descricao = (
            f"Comparando os {len(recentes)} registros dos últimos 7 dias com os "
            f"{len(anteriores)} da semana anterior, o bem-estar percebido nos registros caiu "
            f"{pct:.0%}."
        )
        if dim_principal:
            descricao += f" A maior variação foi no {labels[dim_principal]} percebido."

    return {
        "tipo": "tendencia_recente",
        "titulo": titulo,
        "descricao": descricao,
        "dados": {
            "bem_estar_recente": round(media_r, 3),
            "bem_estar_anterior": round(media_a, 3),
            "variacao": round(delta, 3),
            "eventos_recentes": len(recentes),
            "eventos_anteriores": len(anteriores),
        },
        "relevancia": min(0.95, 0.65 + abs(delta) * 2),
    }


# ── 4b. Alertas específicos das novas dimensões ───────────────────────────────

def _alerta_interesse_baixo(eventos) -> Optional[Dict]:
    if len(eventos) < 3:
        return None
    ultimos = eventos[-4:]
    baixos = [e for e in ultimos if getattr(e, "interesse", None) is not None and e.interesse < 0.30]
    if len(baixos) < 3:
        return None
    media = sum(e.interesse for e in baixos) / len(baixos)
    return {
        "tipo": "alerta_interesse_baixo",
        "titulo": "Baixa vontade de engajamento nos últimos registros",
        "descricao": (
            f"Nos seus últimos {len(baixos)} de {len(ultimos)} registros, você aparece com baixa vontade de engajamento — "
            f"interesse abaixo de 0.30 (média {media:.2f} nos registros). "
            "Isso é independente do humor: alguém pode estar com humor neutro mas sem vontade de fazer coisas."
        ),
        "dados": {"registros_baixos": len(baixos), "media_interesse": round(media, 3)},
        "relevancia": min(0.90, 0.70 + (0.30 - media)),
    }


def _alerta_serenidade_baixa(eventos) -> Optional[Dict]:
    if len(eventos) < 3:
        return None
    ultimos = eventos[-4:]
    baixos = [e for e in ultimos if getattr(e, "serenidade", None) is not None and e.serenidade < 0.30]
    if len(baixos) < 3:
        return None
    media = sum(e.serenidade for e in baixos) / len(baixos)
    return {
        "tipo": "alerta_serenidade_baixa",
        "titulo": "Serenidade consistentemente baixa nos últimos registros",
        "descricao": (
            f"Seus últimos {len(baixos)} de {len(ultimos)} registros mostram serenidade abaixo de 0.30 "
            f"(média {media:.2f}) — possível agitação ou irritação persistente nos registros. "
            "Esse padrão pode aparecer mesmo quando humor e bem-estar geral parecem neutros."
        ),
        "dados": {"registros_baixos": len(baixos), "media_serenidade": round(media, 3)},
        "relevancia": min(0.90, 0.70 + (0.30 - media)),
    }


def _alerta_sensibilidade_alta(eventos) -> Optional[Dict]:
    if len(eventos) < 3:
        return None
    ultimos = eventos[-4:]
    altos = [e for e in ultimos if getattr(e, "sensibilidade", None) is not None and e.sensibilidade > 0.75]
    if len(altos) < 3:
        return None
    media = sum(e.sensibilidade for e in altos) / len(altos)
    return {
        "tipo": "alerta_sensibilidade_alta",
        "titulo": "Alta sensibilidade ao ambiente nos últimos registros",
        "descricao": (
            f"Você registrou alta sensibilidade ao ambiente em {len(altos)} dos últimos {len(ultimos)} registros "
            f"(média {media:.2f}) — possível sobrecarga perceptiva nos registros. "
            "Alta sensibilidade nem sempre é negativa, mas quando persistente pode indicar cansaço perceptivo."
        ),
        "dados": {"registros_altos": len(altos), "media_sensibilidade": round(media, 3)},
        "relevancia": min(0.80, 0.60 + (media - 0.75)),
    }


def _frase_dim_periodo(dim: str, label_periodo: str, sentido: str) -> str:
    """Gera frase de co-ocorrência entre uma dimensão e um período do dia."""
    periodo = label_periodo.split("(")[0].strip()
    if sentido == "alta":
        if dim == "sensibilidade":
            return f"À {periodo}, sensibilidade aparece elevada nos seus registros."
        return f"De {periodo}, seus registros mostram {dim} significativamente mais alta."
    else:
        if dim == "interesse":
            return f"À {periodo}, seus registros mostram interesse mais baixo — menor vontade de engajamento."
        if dim == "serenidade":
            return f"À {periodo}, serenidade aparece mais baixa nos seus registros."
        return f"À {periodo}, sensibilidade aparece mais baixa nos seus registros."


def _frase_dim_dia(dim: str, nome_dia: str, sentido: str) -> str:
    """Gera frase de co-ocorrência entre uma dimensão e um dia da semana."""
    if sentido == "alta":
        if dim == "interesse":
            return f"{nome_dia.capitalize()} aparece nos seus registros com interesse significativamente mais alto."
        if dim == "serenidade":
            return f"{nome_dia.capitalize()} co-ocorre com serenidade mais alta nos seus registros."
        return f"{nome_dia.capitalize()} aparece com sensibilidade mais elevada nos seus registros."
    else:
        if dim == "serenidade":
            return f"{nome_dia.capitalize()} co-ocorre com serenidade mais baixa nos seus registros."
        if dim == "interesse":
            return f"{nome_dia.capitalize()} aparece com menor vontade de engajamento nos seus registros."
        return f"{nome_dia.capitalize()} co-ocorre com sensibilidade mais baixa nos seus registros."


# ── 2. Padrão por hora do dia ─────────────────────────────────────────────────

def _padrao_horario(eventos) -> Optional[Dict]:
    """Identifica período do dia com melhor e pior estado."""
    periodos = {
        "manhã (6h–12h)": (6, 12),
        "tarde (12h–18h)": (12, 18),
        "noite (18h–24h)": (18, 24),
        "madrugada (0h–6h)": (0, 6),
    }

    scores_por_periodo: Dict[str, List[float]] = defaultdict(list)
    for evt in eventos:
        h = evt.data_hora.hour
        for nome, (inicio, fim) in periodos.items():
            if inicio <= h < fim:
                s = _bem_estar(evt)
                if s is not None:
                    scores_por_periodo[nome].append(s)
                break

    # Precisa de ao menos 2 períodos diferentes com dados suficientes
    validos = {p: v for p, v in scores_por_periodo.items() if len(v) >= 2}
    if len(validos) < 2:
        return None

    medias = {p: sum(v) / len(v) for p, v in validos.items()}
    melhor = max(medias, key=medias.get)
    pior = min(medias, key=medias.get)

    if medias[melhor] - medias[pior] < 0.1:
        return None

    diff = medias[melhor] - medias[pior]

    # Contagem de registros por período para identificar viés de frequência
    contagens = {p: len(v) for p, v in scores_por_periodo.items() if p in validos}
    total_reg = sum(contagens.values())
    pct_melhor = contagens.get(melhor, 0) / total_reg if total_reg else 0
    aviso_vies = (
        f" Atenção: {round(pct_melhor*100)}% dos seus registros são de {melhor} — "
        f"isso pode influenciar o padrão (viés de quando você tende a registrar)."
        if pct_melhor >= 0.5 else ""
    )

    # Picos individuais das novas dimensões por período (variação ≥ 0.15)
    extras_horario = []
    for dim in ("serenidade", "interesse", "sensibilidade"):
        por_dim: Dict[str, List[float]] = defaultdict(list)
        for evt in eventos:
            v = getattr(evt, dim, None)
            if v is None:
                continue
            h = evt.data_hora.hour
            for nome, (inicio, fim) in periodos.items():
                if inicio <= h < fim:
                    por_dim[nome].append(v)
                    break
        validos_dim = {p: v for p, v in por_dim.items() if len(v) >= 2}
        if len(validos_dim) < 2:
            continue
        medias_dim = {p: sum(v) / len(v) for p, v in validos_dim.items()}
        melhor_dim = max(medias_dim, key=medias_dim.get)
        pior_dim = min(medias_dim, key=medias_dim.get)
        diff_dim = medias_dim[melhor_dim] - medias_dim[pior_dim]
        if diff_dim < 0.15:
            continue
        if dim == "sensibilidade":
            extras_horario.append(_frase_dim_periodo(dim, melhor_dim, "alta"))
        elif medias_dim[melhor_dim] > 0.5:
            extras_horario.append(_frase_dim_periodo(dim, melhor_dim, "alta"))
        else:
            extras_horario.append(_frase_dim_periodo(dim, pior_dim, "baixa"))

    descricao_horario = (
        f"Nos seus registros, bem-estar percebido de {melhor} é mais alto "
        f"(média {medias[melhor]:.2f}) do que de {pior} "
        f"(média {medias[pior]:.2f}). "
        f"Diferença de {diff:.0%} nos registros — pode ser um padrão de percepção ou simplesmente de quando você tende a registrar.{aviso_vies}"
    )
    if extras_horario:
        descricao_horario += " " + " ".join(extras_horario)

    return {
        "tipo": "padrao_horario",
        "titulo": f"Você registra estados mais positivos de {melhor}",
        "descricao": descricao_horario,
        "dados": {
            "melhor_periodo": melhor,
            "pior_periodo": pior,
            "media_melhor": round(medias[melhor], 3),
            "media_pior": round(medias[pior], 3),
            "diferenca": round(diff, 3),
        },
        "relevancia": min(0.9, 0.55 + diff * 2),
    }


# ── 3. Estado por nível de percepção ──────────────────────────────────────────

def _estados_por_nivel_percebido(eventos) -> Optional[Dict]:
    """Quais rótulos de estado co-ocorrem com bem-estar baixo ou alto nos registros."""
    por_nome: Dict[str, List] = defaultdict(list)
    for evt in eventos:
        por_nome[evt.evento].append(evt)

    frequentes = {n: evts for n, evts in por_nome.items() if len(evts) >= 2}
    if not frequentes:
        return None

    # Bem-estar percebido médio por rótulo de estado
    por_nivel: Dict[str, Dict] = {}
    for nome, evts in frequentes.items():
        scores = [s for e in evts if (s := _bem_estar(e)) is not None]
        if scores:
            por_nivel[nome] = {
                "media": sum(scores) / len(scores),
                "ocorrencias": len(evts),
            }

    if not por_nivel:
        return None

    media_geral = sum(d["media"] for d in por_nivel.values()) / len(por_nivel)

    # Rótulo que mais co-ocorre com bem-estar baixo nos registros
    com_baixo = {n: d for n, d in por_nivel.items() if d["media"] < media_geral - 0.1}
    # Rótulo que mais co-ocorre com bem-estar alto nos registros
    com_alto = {n: d for n, d in por_nivel.items() if d["media"] > media_geral + 0.1}

    if not com_baixo and not com_alto:
        return None

    # Prefere o contraste maior
    destaque_baixo = min(com_baixo, key=lambda n: com_baixo[n]["media"]) if com_baixo else None
    destaque_alto  = max(com_alto,  key=lambda n: com_alto[n]["media"])  if com_alto  else None

    contraste_baixo = (media_geral - por_nivel[destaque_baixo]["media"]) if destaque_baixo else 0
    contraste_alto  = (por_nivel[destaque_alto]["media"] - media_geral)  if destaque_alto  else 0

    if contraste_baixo >= contraste_alto and destaque_baixo:
        info = por_nivel[destaque_baixo]
        evts_baixo = frequentes[destaque_baixo]
        dims_detalhe = _resumo_dims(evts_baixo)
        return {
            "tipo": "estado_nivel_baixo",
            "titulo": f"'{destaque_baixo}' co-ocorre com bem-estar percebido baixo nos seus registros",
            "descricao": (
                f"Nas {info['ocorrencias']} vezes que você registrou '{destaque_baixo}', "
                f"bem-estar percebido médio foi {info['media']:.2f} "
                f"(média geral dos registros: {media_geral:.2f})"
                + (f" — {dims_detalhe}" if dims_detalhe else "")
                + f". Isso é um padrão nos seus registros, não uma afirmação sobre o que '{destaque_baixo}' causa."
            ),
            "dados": {**info, "evento": destaque_baixo, "media_geral": round(media_geral, 3)},
            "relevancia": min(0.9, 0.6 + contraste_baixo * 2),
        }

    if destaque_alto:
        info = por_nivel[destaque_alto]
        evts_alto = frequentes[destaque_alto]
        dims_detalhe = _resumo_dims(evts_alto)
        return {
            "tipo": "estado_nivel_alto",
            "titulo": f"'{destaque_alto}' co-ocorre com bem-estar percebido alto nos seus registros",
            "descricao": (
                f"Nas {info['ocorrencias']} vezes que você registrou '{destaque_alto}', "
                f"bem-estar percebido médio foi {info['media']:.2f} "
                f"(média geral dos registros: {media_geral:.2f})"
                + (f" — {dims_detalhe}" if dims_detalhe else "")
                + f". Esse padrão aparece nos seus registros — não indica que '{destaque_alto}' gera esse bem-estar."
            ),
            "dados": {**info, "evento": destaque_alto, "media_geral": round(media_geral, 3)},
            "relevancia": min(0.8, 0.5 + contraste_alto * 2),
        }

    return None


# ── 4. Alerta de estado persistente ──────────────────────────────────────────

def _alerta_estado_atual(eventos) -> Optional[Dict]:
    """Detecta quando os últimos registros mostram estado ruim consecutivo."""
    if len(eventos) < 3:
        return None

    ultimos = eventos[-4:]  # últimos 4 eventos
    ruins = []
    for evt in ultimos:
        s = _bem_estar(evt)
        if s is not None and s < 0.4:
            ruins.append(evt)

    if len(ruins) < 3:
        return None

    media_atual = sum(_bem_estar(e) for e in ruins if _bem_estar(e)) / len(ruins)
    media_geral = _media([s for e in eventos if (s := _bem_estar(e)) is not None])

    # Verifica se é pior que a média geral
    if media_geral and media_atual >= media_geral * 0.85:
        return None

    nomes = [e.evento for e in ruins]
    mais_comum = Counter(nomes).most_common(1)[0][0] if nomes else "—"

    return {
        "tipo": "alerta_estado_persistente",
        "titulo": "Atenção: estado baixo nos últimos registros",
        "descricao": (
            f"Seus últimos {len(ruins)} registros apresentam bem-estar percebido consistentemente baixo "
            f"(média {media_atual:.2f}"
            + (f" vs sua média geral de registros de {media_geral:.2f}" if media_geral else "")
            + f"). O estado mais recorrente nos registros é '{mais_comum}'. "
            f"Pode indicar que você tem percebido e registrado estados difíceis com frequência."
        ),
        "dados": {
            "registros_ruins": len(ruins),
            "bem_estar_medio": round(media_atual, 3),
            "bem_estar_geral": round(media_geral, 3) if media_geral else None,
            "evento_mais_comum": mais_comum,
        },
        "relevancia": min(0.95, 0.75 + (0.4 - media_atual)),
    }


# ── 5. Padrão por dia da semana ───────────────────────────────────────────────

def _padrao_dia_semana(eventos) -> Optional[Dict]:
    """Identifica dias da semana com melhor e pior estado habitual."""
    nomes_dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    por_dia: Dict[int, List[float]] = defaultdict(list)

    for evt in eventos:
        s = _bem_estar(evt)
        if s is not None:
            por_dia[evt.data_hora.weekday()].append(s)

    validos = {d: v for d, v in por_dia.items() if len(v) >= 2}
    if len(validos) < 2:
        return None

    medias = {d: sum(v) / len(v) for d, v in validos.items()}
    melhor_dia = max(medias, key=medias.get)
    pior_dia = min(medias, key=medias.get)

    diff = medias[melhor_dia] - medias[pior_dia]
    if diff < 0.1:
        return None

    # Verifica viés de frequência de registro por dia
    total_reg_dias = sum(len(v) for v in por_dia.values())
    pct_pior_dia = len(por_dia[pior_dia]) / total_reg_dias if total_reg_dias else 0
    aviso_vies_dia = (
        f" Atenção: {round(pct_pior_dia*100)}% dos seus registros são de {nomes_dias[pior_dia]} — "
        f"isso pode ser um viés de quando você tende a registrar, não do dia em si."
        if pct_pior_dia >= 0.35 else ""
    )

    # Picos individuais das novas dimensões por dia (variação ≥ 0.15)
    extras_dia = []
    for dim in ("serenidade", "interesse", "sensibilidade"):
        por_dim_dia: Dict[int, List[float]] = defaultdict(list)
        for evt in eventos:
            v = getattr(evt, dim, None)
            if v is not None:
                por_dim_dia[evt.data_hora.weekday()].append(v)
        validos_dim = {d: v for d, v in por_dim_dia.items() if len(v) >= 2}
        if len(validos_dim) < 2:
            continue
        medias_dim = {d: sum(v) / len(v) for d, v in validos_dim.items()}
        melhor_d = max(medias_dim, key=medias_dim.get)
        pior_d = min(medias_dim, key=medias_dim.get)
        diff_dim = medias_dim[melhor_d] - medias_dim[pior_d]
        if diff_dim < 0.15:
            continue
        if dim == "sensibilidade":
            extras_dia.append(_frase_dim_dia(dim, nomes_dias[melhor_d], "alta"))
        elif medias_dim[melhor_d] > 0.5:
            extras_dia.append(_frase_dim_dia(dim, nomes_dias[melhor_d], "alta"))
        else:
            extras_dia.append(_frase_dim_dia(dim, nomes_dias[pior_d], "baixa"))

    descricao_dia = (
        f"Nos {len(por_dia[melhor_dia])} registros de {nomes_dias[melhor_dia]}, "
        f"bem-estar percebido médio nos registros é {medias[melhor_dia]:.2f}. "
        f"Nos {len(por_dia[pior_dia])} registros de {nomes_dias[pior_dia]}, aparece em {medias[pior_dia]:.2f}. "
        f"Diferença de {diff:.0%} — pode refletir um padrão real de percepção ou de quando você tende a registrar.{aviso_vies_dia}"
    )
    if extras_dia:
        descricao_dia += " " + " ".join(extras_dia)

    return {
        "tipo": "padrao_dia_semana",
        "titulo": f"{nomes_dias[melhor_dia].capitalize()} é o dia em que você registra os melhores estados, {nomes_dias[pior_dia]} os mais difíceis",
        "descricao": descricao_dia,
        "dados": {
            "melhor_dia": nomes_dias[melhor_dia],
            "pior_dia": nomes_dias[pior_dia],
            "media_melhor": round(medias[melhor_dia], 3),
            "media_pior": round(medias[pior_dia], 3),
            "diferenca": round(diff, 3),
        },
        "relevancia": min(0.85, 0.5 + diff * 2),
    }


# ── 6. Co-ocorrências percebidas ──────────────────────────────────────────────

def _coocorrencias_percebidas(eventos) -> Optional[Dict]:
    """Quais estados co-ocorrem no mesmo dia com bem-estar percebido baixo ou alto.

    Lógica: agrupa registros por dia; calcula bem-estar percebido médio do dia;
    associa cada rótulo de estado ao bem-estar do dia em que apareceu.
    Sem delta causal — é pura co-ocorrência nos registros.
    """
    from datetime import date as date_type

    por_dia: Dict[date_type, List] = defaultdict(list)
    for evt in eventos:
        por_dia[evt.data_hora.date()].append(evt)

    # Bem-estar percebido de cada dia e quais estados foram registrados nele
    bem_estar_por_estado: Dict[str, List[float]] = defaultdict(list)

    for dia, evts_dia in por_dia.items():
        scores_dia = [s for e in evts_dia if (s := _bem_estar(e)) is not None]
        if not scores_dia:
            continue
        media_dia = sum(scores_dia) / len(scores_dia)
        for evt in evts_dia:
            bem_estar_por_estado[evt.evento].append(media_dia)

    # Apenas rótulos presentes em ao menos 2 dias distintos
    candidatos = {n: v for n, v in bem_estar_por_estado.items() if len(v) >= 2}
    if not candidatos:
        return None

    medias = {n: sum(v) / len(v) for n, v in candidatos.items()}
    media_geral = sum(medias.values()) / len(medias)

    com_baixo = {n: m for n, m in medias.items() if m < media_geral - 0.1}
    com_alto  = {n: m for n, m in medias.items() if m > media_geral + 0.1}

    if not com_baixo and not com_alto:
        return None

    destaque_baixo = min(com_baixo, key=com_baixo.get) if com_baixo else None
    destaque_alto  = max(com_alto,  key=com_alto.get)  if com_alto  else None

    contraste_baixo = (media_geral - medias[destaque_baixo]) if destaque_baixo else 0
    contraste_alto  = (medias[destaque_alto] - media_geral)  if destaque_alto  else 0

    if contraste_baixo >= contraste_alto and destaque_baixo:
        n_dias = len(candidatos[destaque_baixo])
        return {
            "tipo": "coocorrencia_negativa",
            "titulo": f"'{destaque_baixo}' aparece nos dias em que você registra menor bem-estar percebido",
            "descricao": (
                f"Nos {n_dias} dias em que '{destaque_baixo}' foi registrado, "
                f"bem-estar percebido médio do dia foi {medias[destaque_baixo]:.2f} "
                f"(vs média geral de {media_geral:.2f} nos seus registros). "
                f"Isso é uma co-ocorrência nos registros — não uma afirmação sobre o que '{destaque_baixo}' causa ou representa na realidade."
            ),
            "dados": {
                "evento": destaque_baixo,
                "media_bem_estar_dias": round(medias[destaque_baixo], 3),
                "media_geral": round(media_geral, 3),
                "n_dias": n_dias,
            },
            "relevancia": min(0.85, 0.5 + contraste_baixo * 2),
        }

    if destaque_alto:
        n_dias = len(candidatos[destaque_alto])
        return {
            "tipo": "coocorrencia_positiva",
            "titulo": f"'{destaque_alto}' aparece nos dias em que você registra maior bem-estar percebido",
            "descricao": (
                f"Nos {n_dias} dias em que '{destaque_alto}' foi registrado, "
                f"bem-estar percebido médio do dia foi {medias[destaque_alto]:.2f} "
                f"(vs média geral de {media_geral:.2f} nos seus registros). "
                f"Isso é uma co-ocorrência nos registros — não uma afirmação sobre o que '{destaque_alto}' gera ou representa na realidade."
            ),
            "dados": {
                "evento": destaque_alto,
                "media_bem_estar_dias": round(medias[destaque_alto], 3),
                "media_geral": round(media_geral, 3),
                "n_dias": n_dias,
            },
            "relevancia": min(0.8, 0.45 + contraste_alto * 2),
        }

    return None


# ── 7. Ciclos comportamentais ─────────────────────────────────────────────────

def _ciclos_comportamentais(eventos) -> Optional[Dict]:
    """Evento que reaparece em intervalos regulares — ciclo ou rotina."""
    por_nome: Dict[str, List[datetime]] = defaultdict(list)
    for evt in eventos:
        por_nome[evt.evento].append(evt.data_hora)

    ciclos = {}
    for nome, datas in por_nome.items():
        if len(datas) < 2:
            continue
        datas_ord = sorted(datas)
        intervalos = [
            (datas_ord[i + 1] - datas_ord[i]).total_seconds() / 86400
            for i in range(len(datas_ord) - 1)
        ]
        media_int = sum(intervalos) / len(intervalos)
        if media_int <= 0 or media_int > 14:
            continue
        desv_int = _desvio(intervalos)
        consistencia = 1 - (desv_int / media_int) if media_int > 0 and len(intervalos) > 1 else 0.5
        if consistencia >= 0.5:
            ciclos[nome] = {
                "media_dias": round(media_int, 1),
                "ocorrencias": len(datas),
                "consistencia": round(consistencia, 2),
            }

    if not ciclos:
        return None

    melhor = max(ciclos, key=lambda n: ciclos[n]["consistencia"] * ciclos[n]["ocorrencias"])
    info = ciclos[melhor]

    if info["media_dias"] <= 1.5:
        descricao_freq = "diariamente"
    elif info["media_dias"] <= 3:
        descricao_freq = f"a cada {info['media_dias']} dias"
    else:
        descricao_freq = f"a cada ~{info['media_dias']} dias"

    return {
        "tipo": "ciclo_comportamental",
        "titulo": f"'{melhor}' aparece {descricao_freq} — rotina detectada",
        "descricao": (
            f"'{melhor}' aparece registrado {info['ocorrencias']} vezes com intervalos regulares "
            f"({descricao_freq}). "
            f"Esse padrão de registro pode refletir uma rotina — mas não sabemos se representa a frequência real desse estado na sua vida."
        ),
        "dados": {**info, "evento": melhor},
        "relevancia": min(0.8, 0.45 + info["consistencia"] * 0.35 + min(info["ocorrencias"], 5) * 0.04),
    }


# ── 8. Padrões relacionais ───────────────────────────────────────────────────

def _densidade_relacional(eventos) -> Optional[Dict]:
    relacoes = _coletar_relacoes_unicas(eventos)
    total_eventos = len(eventos)
    if total_eventos < 4 or not relacoes:
        return None

    ids_conectados = set()
    for rel in relacoes:
        ids_conectados.add(rel["origem_id"])
        ids_conectados.add(rel["destino_id"])

    proporcao = len(ids_conectados) / total_eventos if total_eventos else 0

    if proporcao <= 0.45:
        return {
            "tipo": "densidade_relacional_baixa",
            "titulo": "Seu mapa ainda tem muitas anotações soltas",
            "descricao": (
                f"Apenas {round(proporcao * 100)}% das anotações recentes estão ligadas a outras no grafo. "
                "Isso sugere que ainda há pouco encadeamento entre os registros, então mudanças nas relações tendem a alterar bastante o mapa."
            ),
            "dados": {
                "proporcao_conectada": round(proporcao, 3),
                "eventos_conectados": len(ids_conectados),
                "total_eventos": total_eventos,
            },
            "relevancia": min(0.85, 0.55 + (0.5 - proporcao)),
        }

    if proporcao >= 0.7:
        return {
            "tipo": "densidade_relacional_alta",
            "titulo": "Seu mapa está ficando bem conectado",
            "descricao": (
                f"{round(proporcao * 100)}% das anotações recentes já aparecem conectadas no grafo. "
                "As relações estão formando um mapa mais coeso entre os estados registrados."
            ),
            "dados": {
                "proporcao_conectada": round(proporcao, 3),
                "eventos_conectados": len(ids_conectados),
                "total_eventos": total_eventos,
            },
            "relevancia": min(0.9, 0.45 + proporcao * 0.5),
        }

    return None


def _predominio_tipo_relacao(eventos) -> Optional[Dict]:
    relacoes = _coletar_relacoes_unicas(eventos)
    if len(relacoes) < 3:
        return None

    manuais = sum(1 for r in relacoes if r["manual"])
    automaticas = len(relacoes) - manuais
    proporcao_auto = automaticas / len(relacoes)
    proporcao_manual = manuais / len(relacoes)

    if proporcao_auto >= 0.65:
        return {
            "tipo": "predominio_relacoes_automaticas",
            "titulo": "O grafo depende majoritariamente de relações automáticas",
            "descricao": (
                f"{round(proporcao_auto * 100)}% das relações recentes foram inferidas automaticamente. "
                "Isso deixa o mapa mais sensível às heurísticas de similaridade do que à curadoria manual."
            ),
            "dados": {
                "automaticas": automaticas,
                "manuais": manuais,
                "proporcao_automaticas": round(proporcao_auto, 3),
            },
            "relevancia": min(0.82, 0.45 + proporcao_auto * 0.45),
        }

    if proporcao_manual >= 0.65:
        return {
            "tipo": "predominio_relacoes_manuais",
            "titulo": "Você está curando manualmente boa parte do seu mapa",
            "descricao": (
                f"{round(proporcao_manual * 100)}% das relações recentes são manuais. "
                "Isso indica que o grafo reflete mais suas associações explícitas do que apenas inferências automáticas."
            ),
            "dados": {
                "automaticas": automaticas,
                "manuais": manuais,
                "proporcao_manuais": round(proporcao_manual, 3),
            },
            "relevancia": min(0.82, 0.45 + proporcao_manual * 0.45),
        }

    return None


def _associacao_dominante(eventos) -> Optional[Dict]:
    relacoes = _coletar_relacoes_unicas(eventos)
    if not relacoes:
        return None

    melhor = max(
        relacoes,
        key=lambda r: (r["score_evidencia"], r["num_fatores"], r["intensidade"], r["confiabilidade"]),
    )
    if melhor["score_evidencia"] < 2.2:
        return None

    return {
        "tipo": "associacao_dominante",
        "titulo": f"{melhor['par']} aparece como a associação mais consistente do mapa",
        "descricao": (
            f"Entre as relações recentes, '{melhor['par']}' reúne {melhor['num_fatores']} evidência(s), "
            f"intensidade percebida de {melhor['intensidade']:.2f} e confiabilidade de {melhor['confiabilidade']:.2f}. "
            "Hoje, essa é a conexão mais forte do seu mapa."
        ),
        "dados": {
            "par": melhor["par"],
            "num_fatores": melhor["num_fatores"],
            "intensidade": round(melhor["intensidade"], 3),
            "confiabilidade": round(melhor["confiabilidade"], 3),
            "score_evidencia": melhor["score_evidencia"],
        },
        "relevancia": min(0.9, 0.45 + melhor["score_evidencia"] * 0.08),
    }


# ── 9. Hub emocional ─────────────────────────────────────────────────────────

def _hub_emocional(eventos) -> Optional[Dict]:
    """Evento com mais relações fortes — ponto central do grafo emocional."""
    conexoes: Dict[str, List[float]] = defaultdict(list)

    for evt in eventos:
        todas = list(evt.relacoes_origem) + list(evt.relacoes_destino)
        for r in todas:
            if r.intensidade and r.intensidade > 0:
                conexoes[evt.evento].append(r.intensidade)

    if not conexoes:
        return None

    # Score: número de conexões × intensidade média
    scores = {
        nome: len(vals) * (sum(vals) / len(vals))
        for nome, vals in conexoes.items()
        if len(vals) >= 2
    }
    if not scores:
        return None

    hub = max(scores, key=scores.get)
    vals = conexoes[hub]
    media_int = sum(vals) / len(vals)

    return {
        "tipo": "hub_emocional",
        "titulo": f"'{hub}' aparece como ponto central no seu mapa de percepções",
        "descricao": (
            f"'{hub}' tem {len(vals)} associações com outros estados nos seus registros, "
            f"com intensidade média percebida de {media_int:.2f}. "
            f"Esse estado parece ser frequentemente percebido em conexão com outros — "
            f"entender ele melhor pode trazer clareza sobre padrões nos seus registros."
        ),
        "dados": {"evento": hub, "total_relacoes": len(vals), "intensidade_media": round(media_int, 3)},
        "relevancia": min(0.9, 0.5 + scores[hub] * 0.1),
    }


# ── 10. Evolução de um estado ─────────────────────────────────────────────────

def _evolucao_estado(eventos) -> Optional[Dict]:
    """Mesmo evento registrado várias vezes — detecta se está melhorando ou piorando."""
    por_nome: Dict[str, list] = defaultdict(list)
    for evt in sorted(eventos, key=lambda e: e.data_hora):
        por_nome[evt.evento].append(evt)

    candidatos = {n: evts for n, evts in por_nome.items() if len(evts) >= 3}
    if not candidatos:
        return None

    melhor_nome, melhor_tendencia, melhor_dir = None, 0.0, ""
    for nome, evts in candidatos.items():
        scores = [_bem_estar(e) for e in evts]
        scores = [s for s in scores if s is not None]
        if len(scores) < 3:
            continue
        # Tendência linear simples: compara primeira metade com segunda
        metade = len(scores) // 2
        media_antiga = sum(scores[:metade]) / metade
        media_recente = sum(scores[metade:]) / len(scores[metade:])
        delta = media_recente - media_antiga
        if abs(delta) > abs(melhor_tendencia):
            melhor_tendencia = delta
            melhor_nome = nome
            melhor_dir = "melhora" if delta > 0 else "piora"

    if not melhor_nome or abs(melhor_tendencia) < 0.05:
        return None

    evts = candidatos[melhor_nome]
    metade_e = len(evts) // 2

    # Tendência individual das novas dimensões (|delta| ≥ 0.15)
    extras_evolucao = []
    for dim in ("serenidade", "interesse", "sensibilidade"):
        vals_dim = [getattr(e, dim, None) for e in evts]
        vals_dim = [v for v in vals_dim if v is not None]
        if len(vals_dim) < 3:
            continue
        m_ant = sum(vals_dim[:metade_e]) / metade_e if metade_e > 0 else None
        m_rec = sum(vals_dim[metade_e:]) / len(vals_dim[metade_e:]) if vals_dim[metade_e:] else None
        if m_ant is None or m_rec is None:
            continue
        delta_dim = m_rec - m_ant
        if abs(delta_dim) < 0.15:
            continue
        if delta_dim < 0:
            if dim == "serenidade":
                extras_evolucao.append(f"Nos seus registros de '{melhor_nome}', serenidade caiu nas ocorrências mais recentes.")
            elif dim == "interesse":
                extras_evolucao.append(f"Nos seus registros de '{melhor_nome}', interesse (vontade de engajamento) caiu nas ocorrências mais recentes.")
            else:
                extras_evolucao.append(f"Nos seus registros de '{melhor_nome}', sensibilidade ao ambiente diminuiu nas ocorrências mais recentes.")
        else:
            if dim == "serenidade":
                extras_evolucao.append(f"Nos seus registros de '{melhor_nome}', serenidade subiu nas ocorrências mais recentes.")
            elif dim == "interesse":
                extras_evolucao.append(f"Nos seus registros de '{melhor_nome}', interesse (vontade de engajamento) subiu nas ocorrências mais recentes.")
            else:
                extras_evolucao.append(f"Nos seus registros de '{melhor_nome}', sensibilidade ao ambiente aumentou nas ocorrências mais recentes.")

    descricao_evo = (
        f"Nos {len(evts)} registros de '{melhor_nome}', "
        f"há uma tendência de {melhor_dir} de {abs(melhor_tendencia):.2f} no bem-estar percebido. "
        + ("Nos registros recentes, esse estado aparece associado a percepções mais positivas." if melhor_dir == "melhora"
           else "Nos registros recentes, esse estado aparece associado a percepções mais difíceis — pode valer atenção.")
    )
    if extras_evolucao:
        descricao_evo += " " + " ".join(extras_evolucao)

    return {
        "tipo": "evolucao_estado",
        "titulo": f"'{melhor_nome}' aparece em {melhor_dir} nos seus registros ao longo do tempo",
        "descricao": descricao_evo,
        "dados": {"evento": melhor_nome, "tendencia": round(melhor_tendencia, 3),
                  "direcao": melhor_dir, "ocorrencias": len(evts)},
        "relevancia": min(0.9, 0.6 + abs(melhor_tendencia) * 2),
    }


# ── 11. Cluster de estados relacionados ───────────────────────────────────────

def _cluster_relacoes(eventos) -> Optional[Dict]:
    """Grupo de estados que se relacionam entre si — cluster emocional."""
    from collections import defaultdict

    # Monta grafo de adjacência usando as relações
    grafo: Dict[str, set] = defaultdict(set)
    for evt in eventos:
        todas = list(evt.relacoes_origem) + list(evt.relacoes_destino)
        for r in todas:
            if not r.intensidade or r.intensidade <= 0:
                continue
            origem = evt.evento
            # Pega nome do outro evento
            outro = None
            if hasattr(r, 'evento_destino') and r.evento_destino and r.origem_id == evt.id:
                outro = r.evento_destino.evento
            elif hasattr(r, 'evento_origem') and r.evento_origem and r.destino_id == evt.id:
                outro = r.evento_origem.evento
            if outro:
                grafo[origem].add(outro)
                grafo[outro].add(origem)

    if not grafo:
        return None

    # k-core com k=3: cada estado precisa de ao menos 3 conexões diretas dentro
    # do grupo. Para clusters de 4 nós isso equivale a um clique (todos se conectam).
    nos = set(grafo.keys())
    alterou = True
    while alterou:
        alterou = False
        for no in list(nos):
            if len(grafo[no] & nos) < 3:
                nos.discard(no)
                alterou = True

    if len(nos) < 4:
        return None

    nomes = sorted(nos)
    return {
        "tipo": "cluster_emocional",
        "titulo": f"{len(nos)} estados formam um cluster emocional",
        "descricao": (
            f"Os estados {', '.join(f'\'{n}\'' for n in nomes[:4])}"
            + (" e outros" if len(nomes) > 4 else "")
            + f" aparecem associados entre si de forma densa no seu mapa de registros — "
            f"cada um com ao menos três conexões diretas dentro do grupo. "
            f"Esse cluster sugere que esses estados tendem a ser percebidos em contextos parecidos."
        ),
        "dados": {"estados": nomes, "total": len(nos)},
        "relevancia": min(0.85, 0.5 + len(nos) * 0.05),
    }


# ── 12. Qualidade das relações ────────────────────────────────────────────────

def gerar_qualidade_relacoes(eventos) -> Dict[str, Any]:
    """Ranqua relações mais evidentes e separa coincidências prováveis."""
    from collections import defaultdict

    todas_relacoes = [r for r in _coletar_relacoes_unicas(eventos) if r["fatores"]]

    if not todas_relacoes:
        return {"total": 0, "fortes": [], "fracas": [], "distribuicao": {}}

    relacoes_por_par = {}
    for rel in todas_relacoes:
        atual = relacoes_por_par.get(rel["par"])
        if not atual or (
            rel["score_evidencia"],
            rel["num_fatores"],
            rel["intensidade"],
            rel["confiabilidade"],
        ) > (
            atual["score_evidencia"],
            atual["num_fatores"],
            atual["intensidade"],
            atual["confiabilidade"],
        ):
            relacoes_por_par[rel["par"]] = rel

    relacoes_unicas = list(relacoes_por_par.values())

    # Relações mais evidentes: ordena por um score composto, não só pela contagem de fatores.
    fortes = sorted(
        relacoes_unicas,
        key=lambda x: (-x["score_evidencia"], -x["num_fatores"], -x["intensidade"], -x["confiabilidade"]),
    )[:5]
    fracas = sorted([r for r in relacoes_unicas if r["num_fatores"] == 1],
                    key=lambda x: x["intensidade"])[:5]

    distribuicao = defaultdict(int)
    for r in todas_relacoes:
        distribuicao[r["num_fatores"]] += 1

    total = len(todas_relacoes)
    pct_fracas = round(distribuicao[1] / total * 100) if total else 0
    pct_fortes = round(sum(v for k, v in distribuicao.items() if k >= 3) / total * 100) if total else 0

    return {
        "total": total,
        "pct_fracas": pct_fracas,
        "pct_fortes": pct_fortes,
        "fortes": fortes,
        "fracas": fracas,
        "distribuicao": dict(distribuicao),
    }


# ── Entrada principal ─────────────────────────────────────────────────────────

def gerar_insights_relacoes(eventos) -> Dict[str, Any]:
    """Retorna os 3 insights baseados no grafo de relações."""
    eventos_ord = sorted(eventos, key=lambda e: e.data_hora)
    hub = None
    evolucao = None
    cluster = None
    try:
        hub = _hub_emocional(eventos_ord)
    except Exception:
        pass
    try:
        evolucao = _evolucao_estado(eventos_ord)
    except Exception:
        pass
    try:
        cluster = _cluster_relacoes(eventos_ord)
    except Exception:
        pass
    return {"hub": hub, "evolucao": evolucao, "cluster": cluster}


def gerar_insights_comportamentais(eventos, max_insights: int = 5) -> List[Dict[str, Any]]:
    if len(eventos) < 3:
        return []

    eventos_ord = sorted(eventos, key=lambda e: e.data_hora)

    candidatos = []
    for fn in [
        _alerta_estado_atual,
        _alerta_interesse_baixo,
        _alerta_serenidade_baixa,
        _alerta_sensibilidade_alta,
        _tendencia_recente,
        _estados_por_nivel_percebido,
        _coocorrencias_percebidas,
        _densidade_relacional,
        _predominio_tipo_relacao,
        _associacao_dominante,
        _padrao_horario,
        _padrao_dia_semana,
        _ciclos_comportamentais,
    ]:
        try:
            resultado = fn(eventos_ord)
            if resultado:
                candidatos.append(resultado)
        except Exception:
            continue

    candidatos.sort(key=lambda x: x.get("relevancia", 0), reverse=True)
    return candidatos[:max_insights]
