"""API de Dashboard — estatísticas baseadas em eventos."""
from datetime import date, timedelta, datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db, Evento

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _calcular_streaks(datas_rows) -> tuple[int, int]:
    """Recebe rows com .dia (string ISO) e devolve (streak_atual, streak_maximo)."""
    if not datas_rows:
        return 0, 0

    from datetime import date as date_type
    datas = sorted([date_type.fromisoformat(str(r.dia)) for r in datas_rows], reverse=True)

    # Streak atual: só permite "ontem" como ponto de partida, dias seguidos após isso
    streak_atual = 0
    esperado = date.today()
    for i, d in enumerate(datas):
        if d == esperado:
            streak_atual += 1
            esperado -= timedelta(days=1)
        elif i == 0 and d == date.today() - timedelta(days=1):
            # Usuário não registrou hoje — começa pelo dia anterior
            streak_atual += 1
            esperado = d - timedelta(days=1)
        else:
            break

    # Streak máximo histórico
    streak_maximo = 1 if datas else 0
    streak_temp = 1
    for i in range(1, len(datas)):
        if (datas[i - 1] - datas[i]).days == 1:
            streak_temp += 1
            streak_maximo = max(streak_maximo, streak_temp)
        else:
            streak_temp = 1

    return streak_atual, streak_maximo


@router.get("/resumo")
def resumo_dashboard(
    dias: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    data_inicio = datetime.combine(date.today() - timedelta(days=dias), datetime.min.time())

    # Uma única query com todas as agregações
    agg = db.query(
        func.count(Evento.id),
        func.avg(Evento.energia),
        func.avg(Evento.humor),
        func.avg(Evento.estresse),
        func.avg(Evento.sensibilidade),
        func.avg(Evento.serenidade),
        func.avg(Evento.interesse),
    ).filter(Evento.data_hora >= data_inicio).one()

    total_eventos        = agg[0] or 0
    media_energia        = round(float(agg[1]), 3) if agg[1] is not None else None
    media_humor          = round(float(agg[2]), 3) if agg[2] is not None else None
    media_estresse       = round(float(agg[3]), 3) if agg[3] is not None else None
    media_sensibilidade  = round(float(agg[4]), 3) if agg[4] is not None else None
    media_serenidade     = round(float(agg[5]), 3) if agg[5] is not None else None
    media_interesse      = round(float(agg[6]), 3) if agg[6] is not None else None

    # Top eventos por nome via GROUP BY no banco
    top_rows = (
        db.query(Evento.evento, func.count(Evento.id).label("total"))
        .filter(Evento.data_hora >= data_inicio)
        .group_by(Evento.evento)
        .order_by(func.count(Evento.id).desc())
        .limit(5)
        .all()
    )
    top_eventos = [{"nome": r.evento, "total": r.total} for r in top_rows]

    return {
        "periodo_dias": dias,
        "total_eventos": total_eventos,
        "media_energia": media_energia,
        "media_humor": media_humor,
        "media_estresse": media_estresse,
        "media_sensibilidade": media_sensibilidade,
        "media_serenidade": media_serenidade,
        "media_interesse": media_interesse,
        "top_eventos": top_eventos,
    }


@router.get("/resumo-completo")
def resumo_completo(
    dias: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retorna resumo + streak + estado de hoje em uma única chamada."""
    data_inicio = datetime.combine(date.today(), datetime.min.time())

    # Resumo do período
    resumo = resumo_dashboard(dias, db)

    # Estado de hoje (uma query)
    hoje_agg = db.query(
        func.count(Evento.id),
        func.avg(Evento.energia),
        func.avg(Evento.humor),
        func.avg(Evento.estresse),
        func.avg(Evento.sensibilidade),
        func.avg(Evento.serenidade),
        func.avg(Evento.interesse),
    ).filter(
        Evento.data_hora >= data_inicio,
        Evento.data_hora <= datetime.combine(date.today(), datetime.max.time()),
    ).one()

    estado_hoje = None
    if hoje_agg[0]:
        estado_hoje = {
            "data": date.today().isoformat(),
            "total_eventos": hoje_agg[0],
            "energia":       round(float(hoje_agg[1]), 3) if hoje_agg[1] is not None else None,
            "humor":         round(float(hoje_agg[2]), 3) if hoje_agg[2] is not None else None,
            "estresse":      round(float(hoje_agg[3]), 3) if hoje_agg[3] is not None else None,
            "sensibilidade": round(float(hoje_agg[4]), 3) if hoje_agg[4] is not None else None,
            "serenidade":    round(float(hoje_agg[5]), 3) if hoje_agg[5] is not None else None,
            "interesse":     round(float(hoje_agg[6]), 3) if hoje_agg[6] is not None else None,
        }

    # Streak (query leve — só datas)
    datas_rows = (
        db.query(func.date(Evento.data_hora).label("dia"))
        .group_by(func.date(Evento.data_hora))
        .order_by(func.date(Evento.data_hora).desc())
        .all()
    )

    streak_atual, streak_maximo = _calcular_streaks(datas_rows)

    return {
        **resumo,
        "estado_hoje": estado_hoje,
        "streak_atual": streak_atual,
        "streak_maximo": streak_maximo,
    }


@router.get("/streak")
def calcular_streak(db: Session = Depends(get_db)):
    datas_rows = (
        db.query(func.date(Evento.data_hora).label("dia"))
        .group_by(func.date(Evento.data_hora))
        .order_by(func.date(Evento.data_hora).desc())
        .all()
    )
    streak_atual, streak_maximo = _calcular_streaks(datas_rows)
    return {"streak_atual": streak_atual, "streak_maximo": streak_maximo}
