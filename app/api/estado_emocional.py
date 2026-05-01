"""API de Estado Emocional — derivado diretamente dos eventos."""
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import get_db, Evento

router = APIRouter(prefix="/api/estado-emocional", tags=["Estado Emocional"])


class EstadoSnapshot(BaseModel):
    data: str
    humor: Optional[float]
    energia: Optional[float]
    estresse: Optional[float]
    evento_id: Optional[int]
    evento_titulo: Optional[str]
    timestamp: Optional[str]


def _ultimo_estado_do_dia(eventos_do_dia: list) -> EstadoSnapshot | None:
    """Retorna o estado do último evento do dia que tenha ao menos um valor definido."""
    for ev in reversed(eventos_do_dia):
        if ev.humor is not None or ev.energia is not None or ev.estresse is not None:
            return EstadoSnapshot(
                data=ev.timestamp.date().isoformat(),
                humor=ev.humor,
                energia=ev.energia,
                estresse=ev.estresse,
                evento_id=ev.id,
                evento_titulo=ev.titulo,
                timestamp=ev.timestamp.isoformat(),
            )
    return None


@router.get("/hoje", response_model=Optional[EstadoSnapshot])
def estado_hoje(db: Session = Depends(get_db)):
    inicio = datetime.combine(date.today(), datetime.min.time())
    fim    = datetime.combine(date.today(), datetime.max.time())
    eventos = (
        db.query(Evento)
        .filter(Evento.timestamp >= inicio, Evento.timestamp <= fim)
        .order_by(Evento.timestamp.asc())
        .all()
    )
    return _ultimo_estado_do_dia(eventos)


@router.get("/historico", response_model=list[EstadoSnapshot])
def historico_estados(dias: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Retorna o último estado registrado por dia no período."""
    data_inicio = date.today() - timedelta(days=dias - 1)
    eventos = (
        db.query(Evento)
        .filter(
            Evento.timestamp >= datetime.combine(data_inicio, datetime.min.time()),
            (Evento.humor.isnot(None)) | (Evento.energia.isnot(None)) | (Evento.estresse.isnot(None)),
        )
        .order_by(Evento.timestamp.asc())
        .all()
    )

    # Agrupa por dia, mantém o último por dia
    por_dia: dict[date, Evento] = {}
    for ev in eventos:
        por_dia[ev.timestamp.date()] = ev

    return [
        EstadoSnapshot(
            data=d.isoformat(),
            humor=ev.humor,
            energia=ev.energia,
            estresse=ev.estresse,
            evento_id=ev.id,
            evento_titulo=ev.titulo,
            timestamp=ev.timestamp.isoformat(),
        )
        for d, ev in sorted(por_dia.items())
    ]
