"""Schemas Pydantic para Eventos e Relações."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RelacaoCriar(BaseModel):
    evento_id: int
    intensidade: float = Field(default=0.5, ge=0.0, le=1.0)
    confiabilidade: float = Field(default=1.0, ge=0.0, le=1.0)


class RelacaoResposta(BaseModel):
    id: int
    origem_id: int
    destino_id: int
    intensidade: float
    confiabilidade: float
    motivo: Optional[str] = None
    criado_em: datetime
    outro_evento_id: Optional[int] = None
    outro_evento_label: Optional[str] = None
    outro_evento_data_hora: Optional[datetime] = None
    model_config = {"from_attributes": True}


class EventoCriar(BaseModel):
    evento: str = Field(..., min_length=1, max_length=200)
    data_hora: Optional[datetime] = None
    energia: float = Field(..., ge=0.0, le=1.0)
    humor: float = Field(..., ge=0.0, le=1.0)
    estresse: float = Field(..., ge=0.0, le=1.0)
    sensibilidade: float = Field(..., ge=0.0, le=1.0)
    serenidade: float = Field(..., ge=0.0, le=1.0)
    interesse: float = Field(..., ge=0.0, le=1.0)
    descricao: Optional[str] = None
    contexto: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    dimensoes_extras: Optional[Dict[str, float]] = None
    relacoes: Optional[List[RelacaoCriar]] = None


class EventoAtualizar(BaseModel):
    evento: Optional[str] = None
    data_hora: Optional[datetime] = None
    energia: Optional[float] = Field(None, ge=0.0, le=1.0)
    humor: Optional[float] = Field(None, ge=0.0, le=1.0)
    estresse: Optional[float] = Field(None, ge=0.0, le=1.0)
    sensibilidade: Optional[float] = Field(None, ge=0.0, le=1.0)
    serenidade: Optional[float] = Field(None, ge=0.0, le=1.0)
    interesse: Optional[float] = Field(None, ge=0.0, le=1.0)
    descricao: Optional[str] = None
    contexto: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    dimensoes_extras: Optional[Dict[str, float]] = None


class EventoResposta(BaseModel):
    id: int
    evento: str
    data_hora: datetime
    energia: float
    humor: float
    estresse: float
    sensibilidade: float
    serenidade: float
    interesse: float
    descricao: Optional[str]
    contexto: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    dimensoes_extras: Optional[Dict[str, float]]
    hora: Optional[int]
    dia_semana: Optional[int]
    sentimento_score: Optional[float]
    relacoes_contagem: int = 0
    relacoes: Optional[List[RelacaoResposta]] = None
    criado_em: datetime
    model_config = {"from_attributes": True}


class PresetResposta(BaseModel):
    label: str
    energia: float
    humor: float
    estresse: float
    sensibilidade: float
    serenidade: float
    interesse: float
    dimensoes_extras: Optional[Dict[str, float]] = None


class EstadoAgregado(BaseModel):
    data: str
    energia: Optional[float]
    humor: Optional[float]
    estresse: Optional[float]
    sensibilidade: Optional[float]
    serenidade: Optional[float]
    interesse: Optional[float]
    total_eventos: int
