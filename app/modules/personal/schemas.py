from pydantic import BaseModel, Field


class PersonalCreate(BaseModel):
    nombre: str = Field(min_length=2)
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(min_length=8)
    rol: str = Field(pattern=r"^(ADMIN|RECEPCION|ESTILISTA)$")
    comision_default_pct: float = Field(default=0, ge=0, le=100)


class PersonalOut(BaseModel):
    id: str
    nombre: str
    email: str
    rol: str
    comision_default_pct: float
    activo: int = 1


class PersonalUpdate(BaseModel):
    nombre: str = Field(min_length=2)
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    rol: str = Field(pattern=r"^(ADMIN|RECEPCION|ESTILISTA)$")
    comision_default_pct: float = Field(default=0, ge=0, le=100)
    activo: int = Field(default=1, ge=0, le=1)
    password: str = ""  # opcional: si viene con 8+ caracteres se cambia
