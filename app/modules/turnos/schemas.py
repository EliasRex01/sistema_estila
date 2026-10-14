from datetime import datetime

from pydantic import BaseModel, Field


class TurnoCreate(BaseModel):
    cliente_id: str
    profesional_id: str
    servicio_id: str
    inicio: datetime
    canal: str = Field(default="MOSTRADOR", pattern=r"^(MOSTRADOR|WEB|WHATSAPP)$")


class TurnoOut(TurnoCreate):
    id: str
    fin: datetime
    estado: str
    motivo_cancelacion: str = ""


class TurnoCancelar(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)
