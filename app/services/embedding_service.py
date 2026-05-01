"""Serviço de processamento assíncrono de embedding e sentimento por evento."""
import json
from sqlalchemy.orm import Session
from app.models.database import Evento


def processar_evento(evento_id: int, db: Session) -> None:
    """
    Gera embedding e analisa sentimento de um evento.
    Chamado em background após criar/atualizar um evento.
    """
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        return

    texto = " ".join(filter(None, [evento.descricao, evento.contexto]))
    if not texto.strip():
        return

    try:
        from app.ml.nlp import analisar_sentimento, gerar_embedding

        sentimento = analisar_sentimento(texto)
        evento.sentimento_score = sentimento.get("score")
        evento.sentimento_label = sentimento.get("label")

        vetor = gerar_embedding(texto)
        if vetor is not None:
            evento.embedding = json.dumps(vetor)

        db.commit()
    except Exception:
        db.rollback()
