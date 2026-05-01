"""Similaridade entre eventos para enriquecimento automático do grafo."""
import json
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple

LIMIAR = 0.10
TOLERANCIA_DIMENSAO = 0


def _tags(evt) -> Set[str]:
    if not evt.tags_json:
        return set()
    try:
        return {str(tag).strip().lower() for tag in (json.loads(evt.tags_json) or []) if str(tag).strip()}
    except Exception:
        return set()


def _dimensoes_extras(evt) -> Dict[str, float]:
    if not getattr(evt, "dimensoes_extras_json", None):
        return {}
    try:
        dados = json.loads(evt.dimensoes_extras_json) or {}
        return {str(chave): float(valor) for chave, valor in dados.items()}
    except Exception:
        return {}


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^\w\s]", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def _palavras(texto: str) -> Set[str]:
    if not texto:
        return set()
    stop = {
        "de", "a", "o", "e", "em", "com", "que", "para", "por", "um", "uma",
        "no", "na", "do", "da", "dos", "das", "pra", "pro", "foi", "mais",
    }
    return {
        palavra for palavra in _normalizar_texto(texto).split()
        if len(palavra) > 2 and palavra not in stop
    }


def _embedding_similarity(a, b) -> float:
    if not a.embedding or not b.embedding:
        return 0.0
    try:
        from app.ml.nlp import similaridade_coseno

        va = json.loads(a.embedding) if isinstance(a.embedding, str) else a.embedding
        vb = json.loads(b.embedding) if isinstance(b.embedding, str) else b.embedding
        return max(0.0, round(similaridade_coseno(va, vb), 4))
    except Exception:
        return 0.0


def _embedding_similarity_texto(texto_a: str, texto_b: str) -> float:
    texto_a = (texto_a or "").strip()
    texto_b = (texto_b or "").strip()
    if not texto_a or not texto_b:
        return 0.0
    try:
        from app.ml.nlp import gerar_embedding, similaridade_coseno

        vec_a = gerar_embedding(texto_a)
        vec_b = gerar_embedding(texto_b)
        if not vec_a or not vec_b:
            return 0.0
        return max(0.0, round(similaridade_coseno(vec_a, vec_b), 4))
    except Exception:
        return 0.0


def _sim_texto(a: str, b: str) -> float:
    norm_a = _normalizar_texto(a)
    norm_b = _normalizar_texto(b)
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0

    menor, maior = sorted((norm_a, norm_b), key=len)
    if len(menor) >= 10 and menor in maior:
        return 0.95

    palavras_a = _palavras(a)
    palavras_b = _palavras(b)
    jaccard = len(palavras_a & palavras_b) / len(palavras_a | palavras_b) if palavras_a and palavras_b else 0.0
    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    return round(max(jaccard, ratio * 0.85), 4)


def _motivo_tags(a, b) -> Tuple[float, float, str]:
    comuns = sorted(_tags(a) & _tags(b))
    qtd = len(comuns)
    if qtd == 0:
        return 0.0, 0.0, ""
    intensidade = min(0.12 + max(0, qtd - 1) * 0.06, 0.30)
    prefixo = "tag em comum" if qtd == 1 else "tags em comum"
    return intensidade, min(0.75 + qtd * 0.05, 0.95), f"{prefixo}: {', '.join(comuns)}"


def _motivo_titulo(a, b) -> Tuple[float, float, str]:
    titulo_a = (a.evento or "").strip()
    titulo_b = (b.evento or "").strip()
    if not titulo_a or not titulo_b:
        return 0.0, 0.0, ""

    norm_a = _normalizar_texto(titulo_a)
    norm_b = _normalizar_texto(titulo_b)
    if not norm_a or not norm_b:
        return 0.0, 0.0, ""

    if norm_a == norm_b:
        return 0.22, 0.95, f"título com a mesma intenção: '{a.evento}'"

    tokens_a = norm_a.split()
    tokens_b = norm_b.split()
    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()

    if ratio >= 0.88:
        return 0.18, 0.88, f"títulos muito parecidos: '{a.evento}' e '{b.evento}'"

    return 0.0, 0.0, ""


def _motivo_dimensoes(a, b) -> Tuple[float, float, str]:
    iguais: List[str] = []
    dimensoes = [
        ("humor", getattr(a, "humor", None), getattr(b, "humor", None)),
        ("energia", getattr(a, "energia", None), getattr(b, "energia", None)),
        ("estresse", getattr(a, "estresse", None), getattr(b, "estresse", None)),
        ("sensibilidade", getattr(a, "sensibilidade", None), getattr(b, "sensibilidade", None)),
        ("serenidade", getattr(a, "serenidade", None), getattr(b, "serenidade", None)),
        ("interesse", getattr(a, "interesse", None), getattr(b, "interesse", None)),
    ]

    extras_a = _dimensoes_extras(a)
    extras_b = _dimensoes_extras(b)
    for chave in sorted(set(extras_a) & set(extras_b)):
        dimensoes.append((chave, extras_a[chave], extras_b[chave]))

    for nome, va, vb in dimensoes:
        if va is None or vb is None:
            continue
        if abs(float(va) - float(vb)) <= TOLERANCIA_DIMENSAO:
            iguais.append(nome)

    qtd = len(iguais)
    if qtd < 4:
        return 0.0, 0.0, ""

    intensidade = min(0.18 + max(0, qtd - 4) * 0.05, 0.30)
    return intensidade, min(0.80 + qtd * 0.03, 0.95), f"{qtd} dimensões iguais: {', '.join(iguais)}"


def _motivo_descricao(a, b) -> Tuple[float, float, str]:
    desc_a = (a.descricao or "").strip()
    desc_b = (b.descricao or "").strip()
    if not desc_a or not desc_b:
        return 0.0, 0.0, ""

    sim_desc = _sim_texto(desc_a, desc_b)
    sim_emb = _embedding_similarity(a, b)
    if sim_emb <= 0.0:
        sim_emb = _embedding_similarity_texto(desc_a, desc_b)

    palavras_comuns = sorted(_palavras(desc_a) & _palavras(desc_b))
    detalhe = f" (palavras em comum: {', '.join(palavras_comuns)})" if palavras_comuns else ""

    if sim_desc >= 0.95:
        return 0.30, 0.95, f"descrições com o mesmo sentido/intenção{detalhe}"
    if sim_desc >= 0.60:
        return 0.24, 0.88, f"descrições muito parecidas{detalhe}"
    if sim_emb >= 0.76:
        return 0.22, 0.82, f"descrições com sentido/intenção parecidos{detalhe}"
    if sim_emb >= 0.67 and sim_desc >= 0.35:
        return 0.16, 0.74, f"descrições semanticamente próximas{detalhe}"
    return 0.0, 0.0, ""


def calcular_similaridade(a, b) -> Tuple[float, float, str]:
    """Retorna (similaridade_total, confiabilidade, motivo)."""
    evidencias = [
        _motivo_tags(a, b),
        _motivo_titulo(a, b),
        _motivo_dimensoes(a, b),
        _motivo_descricao(a, b),
    ]

    validas = [(intensidade, confiabilidade, motivo) for intensidade, confiabilidade, motivo in evidencias if intensidade > 0 and motivo]
    if not validas:
        return 0.0, 0.0, ""

    intensidade_total = min(1.0, round(sum(item[0] for item in validas), 4))
    peso_total = sum(item[0] for item in validas)
    confiabilidade = 0.0
    if peso_total > 0:
        confiabilidade = sum(intensidade * conf for intensidade, conf, _ in validas) / peso_total

    motivo = "; ".join(item[2] for item in validas)
    return intensidade_total, round(confiabilidade, 4), motivo


def gerar_relacoes_similaridade(eventos, relacoes_existentes: Set[Tuple[int, int]]) -> List[Dict]:
    """
    Analisa todos os pares de eventos e retorna relações de similaridade
    com score >= LIMIAR, sem duplicar relações existentes.
    """
    n = len(eventos)
    if n < 2:
        return []

    candidatos: Dict[int, List[Tuple[float, int, float, str]]] = {e.id: [] for e in eventos}

    for i in range(n):
        for j in range(i + 1, n):
            a, b = eventos[i], eventos[j]

            if (a.id, b.id) in relacoes_existentes or (b.id, a.id) in relacoes_existentes:
                continue

            sim, conf, motivo = calcular_similaridade(a, b)
            if sim < LIMIAR:
                continue

            candidatos[a.id].append((sim, b.id, conf, motivo))
            candidatos[b.id].append((sim, a.id, conf, motivo))

    novas_relacoes: List[Dict] = []
    criadas: Set[Tuple[int, int]] = set()

    for evt_id, lista in candidatos.items():
        lista.sort(key=lambda item: (item[0], item[2]), reverse=True)
        for score, outro_id, conf, motivo in lista:
            par = (min(evt_id, outro_id), max(evt_id, outro_id))
            if par in criadas:
                continue

            criadas.add(par)
            novas_relacoes.append(
                {
                    "origem_id": evt_id,
                    "destino_id": outro_id,
                    "intensidade": round(score, 4),
                    "confiabilidade": round(conf, 4),
                    "motivo": motivo,
                }
            )

    novas_relacoes.sort(key=lambda item: (item["intensidade"], item["confiabilidade"]), reverse=True)
    return novas_relacoes
