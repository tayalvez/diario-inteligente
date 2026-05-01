from typing import Optional, List
from pydantic import BaseModel, Field


class ExperienciaCriar(BaseModel):
    label: str
    descricao: Optional[str] = None
    timestamp: Optional[str] = None
    dim_energia:  Optional[float] = Field(None, ge=0, le=1)
    dim_humor:    Optional[float] = Field(None, ge=0, le=1)
    dim_estresse: Optional[float] = Field(None, ge=0, le=1)
    dim_foco:     Optional[float] = Field(None, ge=0, le=1)


class ExperienciaAtualizar(BaseModel):
    label: Optional[str] = None
    descricao: Optional[str] = None
    timestamp: Optional[str] = None
    dim_energia:  Optional[float] = Field(None, ge=0, le=1)
    dim_humor:    Optional[float] = Field(None, ge=0, le=1)
    dim_estresse: Optional[float] = Field(None, ge=0, le=1)
    dim_foco:     Optional[float] = Field(None, ge=0, le=1)


class ExperienciaResposta(BaseModel):
    id: int
    label: str
    descricao: Optional[str]
    timestamp: str
    hora: Optional[int]
    dia_semana: Optional[int]
    dim_energia:  Optional[float]
    dim_humor:    Optional[float]
    dim_estresse: Optional[float]
    dim_foco:     Optional[float]
    source: str
    confidence: float
    sentimento_score: Optional[float]
    criado_em: str

    model_config = {"from_attributes": True}


class PresetResposta(BaseModel):
    label: str
    dim_energia:  Optional[float]
    dim_humor:    Optional[float]
    dim_estresse: Optional[float]
    dim_foco:     Optional[float]


class EstadoAgregado(BaseModel):
    data: str
    energia:  Optional[float]
    humor:    Optional[float]
    estresse: Optional[float]
    foco:     Optional[float]
    total_experiencias: int
