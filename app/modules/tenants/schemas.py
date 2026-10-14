from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    ruc: str = Field(pattern=r"^\d{6,9}-\d$")
    razon_social: str = Field(min_length=2, max_length=255)
    timbrado: str = ""
    admin_nombre: str = Field(min_length=2)
    admin_email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    admin_password: str = Field(min_length=8)


class TenantOut(BaseModel):
    id: str
    ruc: str
    razon_social: str
    estado: str
