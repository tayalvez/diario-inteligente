"""API de Experiências — estados internos do usuário."""
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.models.database import get_db, Experiencia
from app.schemas.experiencia import (
    ExperienciaCriar, ExperienciaAtualizar,
    ExperienciaResposta, PresetResposta, EstadoAgregado,
)

router = APIRouter(prefix="/api/experiencias", tags=["Experiências"])

# ── Presets ────────────────────────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "cansada":        {"dim_energia": 0.2, "dim_foco": 0.3, "dim_estresse": 0.6, "dim_humor": 0.4},
    "estressada":     {"dim_estresse": 0.8, "dim_humor": 0.3, "dim_energia": 0.4, "dim_foco": None},
    "ansiosa":        {"dim_estresse": 0.7, "dim_humor": 0.3, "dim_energia": 0.5, "dim_foco": 0.3},
    "tranquila":      {"dim_estresse": 0.1, "dim_humor": 0.7, "dim_energia": 0.6, "dim_foco": 0.6},
    "animada":        {"dim_humor": 0.8, "dim_energia": 0.8, "dim_estresse": 0.1, "dim_foco": 0.7},
    "feliz":          {"dim_humor": 0.9, "dim_energia": 0.7, "dim_estresse": 0.1, "dim_foco": None},
    "triste":         {"dim_humor": 0.2, "dim_energia": 0.3, "dim_estresse": 0.4, "dim_foco": 0.2},
    "irritada":       {"dim_estresse": 0.8, "dim_humor": 0.2, "dim_energia": 0.6, "dim_foco": None},
    "focada":         {"dim_foco": 0.9, "dim_energia": 0.7, "dim_humor": 0.6, "dim_estresse": 0.1},
    "confusa":        {"dim_foco": 0.2, "dim_humor": 0.4, "dim_energia": 0.5, "dim_estresse": 0.5},
    "motivada":       {"dim_energia": 0.9, "dim_humor": 0.7, "dim_foco": 0.8, "dim_estresse": 0.1},
    "entediada":      {"dim_energia": 0.3, "dim_foco": 0.2, "dim_humor": 0.3, "dim_estresse": 0.2},
    "sobrecarregada": {"dim_estresse": 0.9, "dim_energia": 0.3, "dim_foco": 0.2, "dim_humor": 0.3},
    "empolgada":      {"dim_humor": 0.85, "dim_energia": 0.9, "dim_foco": 0.7, "dim_estresse": 0.1},
    "realizada":      {"dim_humor": 0.85, "dim_energia": 0.7, "dim_estresse": 0.1, "dim_foco": 0.8},
    "grata":          {"dim_humor": 0.8, "dim_estresse": 0.1, "dim_energia": 0.7, "dim_foco": None},
}


def _agregar(experiencias: list) -> dict:
    """energia/humor/foco = média; estresse = máximo."""
    buckets: dict[str, list[float]] = {"energia": [], "humor": [], "estresse": [], "foco": []}
    for e in experiencias:
        if e.dim_energia  is not None: buckets["energia"].append(e.dim_energia)
        if e.dim_humor    is not None: buckets["humor"].append(e.dim_humor)
        if e.dim_estresse is not None: buckets["estresse"].append(e.dim_estresse)
        if e.dim_foco     is not None: buckets["foco"].append(e.dim_foco)

    def avg(lst): return round(sum(lst) / len(lst), 3) if lst else None
    def mx(lst):  return round(max(lst), 3) if lst else None

    return {
        "energia":  avg(buckets["energia"]),
        "humor":    avg(buckets["humor"]),
        "estresse": mx(buckets["estresse"]),
        "foco":     avg(buckets["foco"]),
    }


def _to_resp(e: Experiencia) -> ExperienciaResposta:
    return ExperienciaResposta(
        id=e.id, label=e.label, descricao=e.descricao,
        timestamp=e.timestamp.isoformat(),
        hora=e.hora, dia_semana=e.dia_semana,
        dim_energia=e.dim_energia, dim_humor=e.dim_humor,
        dim_estresse=e.dim_estresse, dim_foco=e.dim_foco,
        source=e.source, confidence=e.confidence,
        sentimento_score=e.sentimento_score,
        criado_em=e.criado_em.isoformat(),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/presets", response_model=List[PresetResposta])
def listar_presets():
    return [PresetResposta(label=k, **{k2: v for k2, v in v.items()}) for k, v in PRESETS.items()]


@router.get("/estado-hoje", response_model=Optional[EstadoAgregado])
def estado_hoje(db: Session = Depends(get_db)):
    inicio = datetime.combine(date.today(), datetime.min.time())
    fim    = datetime.combine(date.today(), datetime.max.time())
    exps = db.query(Experiencia).filter(
        Experiencia.timestamp >= inicio, Experiencia.timestamp <= fim
    ).all()
    if not exps:
        return None
    estado = _agregar(exps)
    return EstadoAgregado(data=date.today().isoformat(), total_experiencias=len(exps), **estado)


@router.get("/historico", response_model=List[EstadoAgregado])
def historico_estados(dias: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    data_inicio = date.today() - timedelta(days=dias - 1)
    exps = db.query(Experiencia).filter(
        Experiencia.timestamp >= datetime.combine(data_inicio, datetime.min.time())
    ).order_by(Experiencia.timestamp.asc()).all()

    por_dia: dict[date, list] = {}
    for e in exps:
        d = e.timestamp.date()
        por_dia.setdefault(d, []).append(e)

    result = []
    for d in sorted(por_dia.keys()):
        estado = _agregar(por_dia[d])
        result.append(EstadoAgregado(
            data=d.isoformat(), total_experiencias=len(por_dia[d]), **estado
        ))
    return result


@router.get("/", response_model=List[ExperienciaResposta])
def listar_experiencias(
    dias: Optional[int] = Query(None, ge=1, le=365),
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Experiencia).order_by(Experiencia.timestamp.desc())
    if dias:
        corte = datetime.combine(date.today() - timedelta(days=dias - 1), datetime.min.time())
        q = q.filter(Experiencia.timestamp >= corte)
    return [_to_resp(e) for e in q.limit(limite).all()]


@router.post("/", response_model=ExperienciaResposta, status_code=201)
def criar_experiencia(dados: ExperienciaCriar, db: Session = Depends(get_db)):
    ts = datetime.fromisoformat(dados.timestamp) if dados.timestamp else datetime.utcnow()

    # Aplica preset se não vier dimensão explícita
    preset = PRESETS.get(dados.label.lower(), {})
    exp = Experiencia(
        label=dados.label.lower(),
        descricao=dados.descricao,
        timestamp=ts,
        hora=ts.hour,
        dia_semana=ts.weekday(),
        dim_energia=dados.dim_energia  if dados.dim_energia  is not None else preset.get("dim_energia"),
        dim_humor=dados.dim_humor      if dados.dim_humor     is not None else preset.get("dim_humor"),
        dim_estresse=dados.dim_estresse if dados.dim_estresse is not None else preset.get("dim_estresse"),
        dim_foco=dados.dim_foco        if dados.dim_foco      is not None else preset.get("dim_foco"),
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return _to_resp(exp)


@router.put("/{exp_id}", response_model=ExperienciaResposta)
def atualizar_experiencia(exp_id: int, dados: ExperienciaAtualizar, db: Session = Depends(get_db)):
    exp = db.query(Experiencia).filter(Experiencia.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiência não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo == "timestamp" and valor:
            ts = datetime.fromisoformat(valor)
            exp.timestamp = ts
            exp.hora = ts.hour
            exp.dia_semana = ts.weekday()
        else:
            setattr(exp, campo, valor)
    db.commit()
    db.refresh(exp)
    return _to_resp(exp)


@router.delete("/{exp_id}", status_code=204)
def excluir_experiencia(exp_id: int, db: Session = Depends(get_db)):
    exp = db.query(Experiencia).filter(Experiencia.id == exp_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiência não encontrada")
    db.delete(exp)
    db.commit()
    return Response(status_code=204)
