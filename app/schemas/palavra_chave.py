from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


CATEGORIAS = ["emocao", "conceito", "pessoa", "lugar", "outro"]

CORES_PADRAO = {
    "emocao":   "#F5C6CE",
    "conceito": "#DCD3F5",
    "pessoa":   "#CDEEE3",
    "lugar":    "#F7EEDC",
    "outro":    "#C5DEED",
}


class PalavraChaveCriar(BaseModel):
    texto: str = Field(..., min_length=1, max_length=100)
    categoria: str = "conceito"
    cor: Optional[str] = None


class PalavraChaveResposta(BaseModel):
    id: int
    texto: str
    categoria: str
    cor: str
    total_usos: int = 0
    criado_em: datetime
    model_config = {"from_attributes": True}


class RegistroPalavraCriar(BaseModel):
    # palavra_id OU nova_palavra_texto devem ser fornecidos
    palavra_id: Optional[int] = None
    nova_palavra_texto: Optional[str] = Field(None, max_length=100)
    nova_palavra_categoria: str = "conceito"
    data_hora: datetime
    nota: Optional[str] = None
    evento_id: Optional[int] = None


class RegistroPalavraResposta(BaseModel):
    id: int
    palavra_id: int
    palavra_texto: str
    palavra_cor: str
    palavra_categoria: str
    data_hora: datetime
    nota: Optional[str]
    evento_id: Optional[int]
    evento_titulo: Optional[str]
    criado_em: datetime
    model_config = {"from_attributes": True}


class ItemNuvem(BaseModel):
    texto: str
    categoria: str
    cor: str
    total: int
