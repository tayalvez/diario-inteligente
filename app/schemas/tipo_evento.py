"""Schemas Pydantic para Tipos de Evento."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

PhosphorWeight = Literal["regular", "bold", "fill", "duotone", "light", "thin"]


class TipoEventoCriar(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    icone_nome: str = Field(..., min_length=1, max_length=100)
    icone_weight: PhosphorWeight = "regular"


class TipoEventoAtualizar(BaseModel):
    nome: Optional[str] = None
    icone_nome: Optional[str] = None
    icone_weight: Optional[PhosphorWeight] = None


class TipoEventoResposta(BaseModel):
    id: int
    nome: str
    icone_nome: str
    icone_weight: str
    padrao: bool = False
    ativo: bool = True
    model_config = {"from_attributes": True}
