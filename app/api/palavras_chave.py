from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import get_db, PalavraChave, RegistroPalavra, Evento
from app.schemas.palavra_chave import (
    PalavraChaveCriar, PalavraChaveResposta,
    RegistroPalavraCriar, RegistroPalavraResposta,
    ItemNuvem, CORES_PADRAO,
)

router = APIRouter(prefix="/api/palavras-chave", tags=["palavras-chave"])


def _palavra_resposta(p: PalavraChave, db: Session) -> PalavraChaveResposta:
    total = db.query(func.count(RegistroPalavra.id)).filter(RegistroPalavra.palavra_id == p.id).scalar() or 0
    return PalavraChaveResposta(
        id=p.id, texto=p.texto, categoria=p.categoria,
        cor=p.cor, total_usos=total, criado_em=p.criado_em,
    )


def _registro_resposta(r: RegistroPalavra) -> RegistroPalavraResposta:
    return RegistroPalavraResposta(
        id=r.id, palavra_id=r.palavra_id,
        palavra_texto=r.palavra.texto,
        palavra_cor=r.palavra.cor,
        palavra_categoria=r.palavra.categoria,
        data_hora=r.data_hora, nota=r.nota,
        evento_id=r.evento_id,
        evento_titulo=r.evento.titulo if r.evento else None,
        criado_em=r.criado_em,
    )


def _obter_ou_criar_palavra(db: Session, payload: RegistroPalavraCriar) -> PalavraChave:
    """Retorna palavra existente ou cria nova inline."""
    if payload.palavra_id:
        p = db.query(PalavraChave).filter(PalavraChave.id == payload.palavra_id).first()
        if not p:
            raise HTTPException(404, "Palavra-chave não encontrada")
        return p

    if not payload.nova_palavra_texto:
        raise HTTPException(400, "Informe palavra_id ou nova_palavra_texto")

    texto = payload.nova_palavra_texto.strip()
    existente = db.query(PalavraChave).filter(
        func.lower(PalavraChave.texto) == texto.lower()
    ).first()
    if existente:
        return existente

    cor = CORES_PADRAO.get(payload.nova_palavra_categoria, "#DCD3F5")
    nova = PalavraChave(texto=texto, categoria=payload.nova_palavra_categoria, cor=cor)
    db.add(nova)
    db.flush()
    return nova


# ── Palavras-chave ────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PalavraChaveResposta])
def listar_palavras(db: Session = Depends(get_db)):
    palavras = db.query(PalavraChave).order_by(PalavraChave.texto).all()
    return [_palavra_resposta(p, db) for p in palavras]


@router.post("/", response_model=PalavraChaveResposta, status_code=201)
def criar_palavra(payload: PalavraChaveCriar, db: Session = Depends(get_db)):
    existe = db.query(PalavraChave).filter(
        func.lower(PalavraChave.texto) == payload.texto.lower().strip()
    ).first()
    if existe:
        raise HTTPException(400, "Palavra-chave já existe")

    cor = payload.cor or CORES_PADRAO.get(payload.categoria, "#DCD3F5")
    p = PalavraChave(texto=payload.texto.strip(), categoria=payload.categoria, cor=cor)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _palavra_resposta(p, db)


@router.delete("/{palavra_id}", status_code=204)
def excluir_palavra(palavra_id: int, db: Session = Depends(get_db)):
    p = db.query(PalavraChave).filter(PalavraChave.id == palavra_id).first()
    if not p:
        raise HTTPException(404, "Palavra não encontrada")
    db.delete(p)
    db.commit()


# ── Registros ─────────────────────────────────────────────────────────────────

@router.get("/registros", response_model=List[RegistroPalavraResposta])
def listar_registros(
    dias: int = 7,
    db: Session = Depends(get_db),
):
    data_inicio = datetime.utcnow() - timedelta(days=dias)
    registros = (
        db.query(RegistroPalavra)
        .filter(RegistroPalavra.data_hora >= data_inicio)
        .order_by(RegistroPalavra.data_hora.desc())
        .all()
    )
    return [_registro_resposta(r) for r in registros]


@router.post("/registros", response_model=RegistroPalavraResposta, status_code=201)
def registrar_palavra(payload: RegistroPalavraCriar, db: Session = Depends(get_db)):
    p = _obter_ou_criar_palavra(db, payload)

    if payload.evento_id:
        if not db.query(Evento).filter(Evento.id == payload.evento_id).first():
            raise HTTPException(404, "Evento não encontrado")

    r = RegistroPalavra(
        palavra_id=p.id,
        data_hora=payload.data_hora,
        nota=payload.nota,
        evento_id=payload.evento_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _registro_resposta(r)


@router.delete("/registros/{registro_id}", status_code=204)
def excluir_registro(registro_id: int, db: Session = Depends(get_db)):
    r = db.query(RegistroPalavra).filter(RegistroPalavra.id == registro_id).first()
    if not r:
        raise HTTPException(404, "Registro não encontrado")
    db.delete(r)
    db.commit()


# ── Nuvem de frequência ───────────────────────────────────────────────────────

@router.get("/nuvem", response_model=List[ItemNuvem])
def nuvem(dias: int = 30, db: Session = Depends(get_db)):
    data_inicio = datetime.utcnow() - timedelta(days=dias)
    rows = (
        db.query(
            PalavraChave.texto,
            PalavraChave.categoria,
            PalavraChave.cor,
            func.count(RegistroPalavra.id).label("total"),
        )
        .join(RegistroPalavra, RegistroPalavra.palavra_id == PalavraChave.id)
        .filter(RegistroPalavra.data_hora >= data_inicio)
        .group_by(PalavraChave.id)
        .order_by(func.count(RegistroPalavra.id).desc())
        .all()
    )
    return [ItemNuvem(texto=r.texto, categoria=r.categoria, cor=r.cor, total=r.total) for r in rows]
