from pydantic import BaseModel, Field


class ClienteCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=255)
    ci_ruc: str = ""
    telefono: str = ""
    direccion: str = ""
    ficha_json: str = "{}"  # alergias, preferencias, contraindicaciones (RF10)


class ClienteOut(ClienteCreate):
    id: str
    n_visitas: int = 0
