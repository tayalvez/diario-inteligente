import json
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ml.nlp import gerar_embedding
from app.models.database import Evento, SessionLocal


def iter_eventos_sem_embedding(eventos: Iterable[Evento]):
    for evento in eventos:
        if evento.descricao and evento.descricao.strip() and not evento.embedding:
            yield evento


def main() -> None:
    db = SessionLocal()
    atualizados = 0
    falhas = 0

    try:
        eventos = (
            db.query(Evento)
            .order_by(Evento.data_hora.asc(), Evento.id.asc())
            .all()
        )

        for evento in iter_eventos_sem_embedding(eventos):
            vetor = gerar_embedding(evento.descricao.strip())
            if vetor:
                evento.embedding = json.dumps(vetor, ensure_ascii=False)
                atualizados += 1
            else:
                falhas += 1

        db.commit()
        print(
            json.dumps(
                {
                    "eventos_processados": len(eventos),
                    "embeddings_atualizados": atualizados,
                    "falhas": falhas,
                },
                ensure_ascii=False,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
