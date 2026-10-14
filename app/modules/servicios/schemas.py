from pydantic import BaseModel, Field


class ServicioCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=255)
    duracion_min: int = Field(default=30, ge=5, le=480)
    precio_gs: int = Field(default=0, ge=0)
    comision_pct: float = Field(default=0, ge=0, le=100)


class ServicioOut(ServicioCreate):
    id: str
