"""Modelos Estila segun diccionario de datos §8. Toda tabla operativa lleva tenant_id.

Motor principal: Oracle (ADB/XE). Nota Oracle: '' se almacena como NULL,
por eso las respuestas API/plantillas normalizan con `or ""`.
`func.current_timestamp()` vale en Oracle, Postgres y SQLite."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ruc: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # ej. 80012345-6
    razon_social: Mapped[str] = mapped_column(String(255))  # nombre legal/comercial
    timbrado: Mapped[str] = mapped_column(String(20), default="")
    cert_p12_path_enc: Mapped[str] = mapped_column(Text, default="")  # ruta cifrada (RNF04)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())


class UsuarioPersonal(Base):
    __tablename__ = "usuarios_personal"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(20), default="ESTILISTA")  # ADMIN/RECEPCION/ESTILISTA
    comision_default_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    horario_json: Mapped[str] = mapped_column(Text, default="{}")
    activo: Mapped[int] = mapped_column(Integer, default=1)


class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    ci_ruc: Mapped[str] = mapped_column(String(20), default="", index=True)
    telefono: Mapped[str] = mapped_column(String(50), default="")
    direccion: Mapped[str] = mapped_column(String(255), default="")
    n_visitas: Mapped[int] = mapped_column(Integer, default=0)
    ficha_json: Mapped[str] = mapped_column(Text, default="{}")  # alergias, preferencias
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())


class Servicio(Base):
    __tablename__ = "servicios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    duracion_min: Mapped[int] = mapped_column(Integer, default=30)
    precio_gs: Mapped[int] = mapped_column(Integer, default=0)  # guaranies (RNF11)
    comision_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


class Producto(Base):
    __tablename__ = "productos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    costo_gs: Mapped[int] = mapped_column(Integer, default=0)
    precio_venta_gs: Mapped[int] = mapped_column(Integer, default=0)
    punto_reposicion: Mapped[int] = mapped_column(Integer, default=5)


class Turno(Base):
    __tablename__ = "turnos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    profesional_id: Mapped[str] = mapped_column(ForeignKey("usuarios_personal.id"), index=True)
    servicio_id: Mapped[str] = mapped_column(ForeignKey("servicios.id"), index=True)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20), default="RESERVADO")
    # RESERVADO/CONFIRMADO/CANCELADO/ATENDIDO/BLOQUEADO
    motivo_cancelacion: Mapped[str] = mapped_column(String(255), default="")
    canal: Mapped[str] = mapped_column(String(20), default="MOSTRADOR")


class VentaCabecera(Base):
    __tablename__ = "ventas_cabecera"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    cliente_id: Mapped[str] = mapped_column(String(36), default="")
    medio_pago: Mapped[str] = mapped_column(String(20), default="EFECTIVO")
    total_gs: Mapped[int] = mapped_column(Integer, default=0)
    estado_sifen: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())


class VentaDetalle(Base):
    __tablename__ = "ventas_detalle"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    venta_id: Mapped[str] = mapped_column(ForeignKey("ventas_cabecera.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))  # SERVICIO/PRODUCTO
    ref_id: Mapped[str] = mapped_column(String(36))
    cantidad: Mapped[int] = mapped_column(Integer, default=1)
    precio_gs: Mapped[int] = mapped_column(Integer, default=0)
    profesional_id: Mapped[str] = mapped_column(String(36), default="")


class Caja(Base):
    __tablename__ = "cajas"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    usuario_apertura: Mapped[str] = mapped_column(String(36))
    monto_apertura_gs: Mapped[int] = mapped_column(Integer, default=0)
    monto_cierre_gs: Mapped[int] = mapped_column(Integer, default=0)
    diferencia_gs: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(20), default="ABIERTA")


class Comision(Base):
    __tablename__ = "comisiones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    profesional_id: Mapped[str] = mapped_column(ForeignKey("usuarios_personal.id"), index=True)
    periodo: Mapped[str] = mapped_column(String(20))  # YYYY-MM o etiqueta
    servicios_computados: Mapped[int] = mapped_column(Integer, default=0)
    monto_gs: Mapped[int] = mapped_column(Integer, default=0)


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    usuario_id: Mapped[str] = mapped_column(String(36), default="")
    accion: Mapped[str] = mapped_column(String(100))
    detalle: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())
