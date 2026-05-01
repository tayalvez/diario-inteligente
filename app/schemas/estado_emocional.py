from typing import Optional
from pydantic import BaseModel


class EstadoSnapshot(BaseModel):
    data: str
    humor: Optional[float]
    energia: Optional[float]
    estresse: Optional[float]
    evento_id: Optional[int]
    evento_titulo: Optional[str]
    timestamp: Optional[str]
