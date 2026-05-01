"""Módulo de NLP — análise de sentimento e geração de embeddings."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# ── Sentimento ────────────────────────────────────────────────────────────────

def analisar_sentimento(texto: str) -> Dict[str, Any]:
    """Analisa o sentimento de um texto via TextBlob com fallback por palavras-chave."""
    if not texto or not texto.strip():
        return {"score": 0.0, "label": "neutro", "confianca": 0.0}

    try:
        from textblob import TextBlob
        blob = TextBlob(texto)
        score_raw = blob.sentiment.polarity  # -1 a 1
        score_normalizado = round((score_raw + 1) / 2 * 9 + 1, 2)  # 1–10

        if score_raw > 0.1:
            label = "positivo"
        elif score_raw < -0.1:
            label = "negativo"
        else:
            label = "neutro"

        return {
            "score": score_normalizado,
            "label": label,
            "confianca": round(abs(score_raw), 2),
            "metodo": "textblob",
        }
    except Exception:
        pass

    return _analise_por_palavras(texto)


def _analise_por_palavras(texto: str) -> Dict[str, Any]:
    """Análise simplificada por palavras-chave em português."""
    texto_lower = texto.lower()

    palavras_positivas = [
        "ótimo", "bem", "feliz", "alegre", "animado", "boa", "bom", "excelente",
        "maravilhoso", "incrível", "grato", "gratidão", "produtivo", "energia",
        "motivado", "realizado", "tranquilo", "calmo", "positivo", "esperançoso",
        "conquista", "sucesso", "satisfeito", "descansado", "legal", "divertido"
    ]

    palavras_negativas = [
        "ruim", "mal", "triste", "cansado", "estressado", "ansioso", "preocupado",
        "frustrado", "difícil", "horrível", "péssimo", "fracasso", "problema",
        "dor", "doente", "esgotado", "negativo", "deprimido", "chateado",
        "irritado", "bravo", "exausto", "insone", "medo"
    ]

    pontos_pos = sum(1 for p in palavras_positivas if p in texto_lower)
    pontos_neg = sum(1 for p in palavras_negativas if p in texto_lower)

    if pontos_pos > pontos_neg:
        score = min(9, 6 + pontos_pos)
        label = "positivo"
    elif pontos_neg > pontos_pos:
        score = max(1, 4 - pontos_neg)
        label = "negativo"
    else:
        score = 5.0
        label = "neutro"

    return {
        "score": float(score),
        "label": label,
        "confianca": 0.4,
        "metodo": "palavras_chave",
    }


# ── Embeddings ────────────────────────────────────────────────────────────────

_modelo_embedding = None
_modelo_pronto = False
MODEL_REPO_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_LOCAL_DIR = Path(__file__).resolve().parents[2] / "models" / "paraphrase-multilingual-MiniLM-L12-v2"


def resolver_fonte_modelo() -> str:
    """
    Resolve de onde o modelo de embeddings deve ser carregado.

    Ordem de prioridade:
    1. EMBEDDING_MODEL_DIR, se apontar para um diretório existente
    2. models/paraphrase-multilingual-MiniLM-L12-v2 dentro do projeto
    3. EMBEDDING_MODEL_NAME, apenas quando EMBEDDING_ALLOW_REMOTE_DOWNLOAD=1
    """
    env_model_dir = os.getenv("EMBEDDING_MODEL_DIR")
    if env_model_dir:
        model_dir = Path(env_model_dir).expanduser().resolve()
        if model_dir.exists():
            return str(model_dir)
        raise RuntimeError(
            f"EMBEDDING_MODEL_DIR aponta para caminho inexistente: {model_dir}"
        )

    if MODEL_LOCAL_DIR.exists():
        return str(MODEL_LOCAL_DIR)

    allow_remote = os.getenv("EMBEDDING_ALLOW_REMOTE_DOWNLOAD", "").strip() == "1"
    if allow_remote:
        return os.getenv("EMBEDDING_MODEL_NAME", MODEL_REPO_ID)

    raise RuntimeError(
        "Modelo de embedding nao encontrado localmente. "
        f"Baixe o modelo para '{MODEL_LOCAL_DIR}' ou defina EMBEDDING_MODEL_DIR. "
        "Para permitir download remoto em desenvolvimento, use "
        "EMBEDDING_ALLOW_REMOTE_DOWNLOAD=1."
    )


def _obter_modelo():
    global _modelo_embedding, _modelo_pronto
    if _modelo_embedding is None:
        from sentence_transformers import SentenceTransformer
        _modelo_embedding = SentenceTransformer(resolver_fonte_modelo())
        _modelo_pronto = True
    return _modelo_embedding


def modelo_pronto() -> bool:
    return _modelo_pronto


def gerar_embedding(texto: str) -> Optional[List[float]]:
    """
    Gera vetor de embedding para o texto usando sentence-transformers.
    Retorna None imediatamente se o modelo ainda não foi carregado.
    """
    if not texto or not texto.strip():
        return None
    if not _modelo_pronto:
        return None
    try:
        modelo = _obter_modelo()
        vetor = modelo.encode(texto.strip(), normalize_embeddings=True)
        return vetor.tolist()
    except Exception as e:
        print(f"[embedding] ERRO ao gerar embedding: {type(e).__name__}: {e}")
        return None


def similaridade_coseno(vec_a: List[float], vec_b: List[float]) -> float:
    """Produto interno de vetores já normalizados (equivale ao coseno)."""
    try:
        import numpy as np
        return float(np.dot(vec_a, vec_b))
    except Exception:
        return 0.0
