"""API de Tipos de Evento — CRUD de diretórios semânticos."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db, TipoEvento, DimensaoEvento
from app.schemas.tipo_evento import TipoEventoCriar, TipoEventoAtualizar, TipoEventoResposta

router = APIRouter(prefix="/api/tipos-evento", tags=["Tipos de Evento"])


@router.get("/", response_model=List[TipoEventoResposta])
def listar_tipos(db: Session = Depends(get_db)):
    """Retorna todos os tipos ativos (padrão + customizados)."""
    return db.query(TipoEvento).filter(TipoEvento.ativo == True).order_by(TipoEvento.nome).all()


@router.get("/{tipo_id}", response_model=TipoEventoResposta)
def obter_tipo(tipo_id: int, db: Session = Depends(get_db)):
    tipo = db.query(TipoEvento).filter(TipoEvento.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo não encontrado")
    return tipo


@router.get("/{tipo_id}/dimensoes-sugeridas")
def dimensoes_sugeridas(tipo_id: int, limite: int = 10, db: Session = Depends(get_db)):
    """Retorna as dimensões mais usadas em eventos desse tipo (baseado no histórico)."""
    from app.models.database import Evento
    resultado = (
        db.query(DimensaoEvento.nome, func.count(DimensaoEvento.id).label("total"))
        .join(Evento, Evento.id == DimensaoEvento.evento_id)
        .filter(Evento.tipo_id == tipo_id)
        .group_by(DimensaoEvento.nome)
        .order_by(func.count(DimensaoEvento.id).desc())
        .limit(limite)
        .all()
    )
    return {"dimensoes": [{"nome": r.nome, "total": r.total} for r in resultado]}


@router.post("/", response_model=TipoEventoResposta, status_code=201)
def criar_tipo(dados: TipoEventoCriar, db: Session = Depends(get_db)):
    """Cria um tipo de evento customizado."""
    existente = db.query(TipoEvento).filter(TipoEvento.nome == dados.nome).first()
    if existente:
        if existente.ativo:
            raise HTTPException(status_code=409, detail="Já existe um tipo com este nome.")
        # Reativa se estava inativo
        existente.icone_nome = dados.icone_nome
        existente.icone_weight = dados.icone_weight
        existente.ativo = True
        db.commit()
        db.refresh(existente)
        return existente

    novo = TipoEvento(nome=dados.nome, icone_nome=dados.icone_nome,
                      icone_weight=dados.icone_weight, padrao=False)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.put("/{tipo_id}", response_model=TipoEventoResposta)
def atualizar_tipo(tipo_id: int, dados: TipoEventoAtualizar, db: Session = Depends(get_db)):
    tipo = db.query(TipoEvento).filter(TipoEvento.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo não encontrado")
    if tipo.padrao:
        raise HTTPException(status_code=400, detail="Tipos padrão não podem ser alterados.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(tipo, campo, valor)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.delete("/{tipo_id}", status_code=204)
def excluir_tipo(tipo_id: int, db: Session = Depends(get_db)):
    """Soft delete de um tipo customizado."""
    tipo = db.query(TipoEvento).filter(TipoEvento.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo não encontrado")
    if tipo.padrao:
        raise HTTPException(status_code=400, detail="Tipos padrão não podem ser removidos.")
    tipo.ativo = False
    db.commit()
    return Response(status_code=204)
