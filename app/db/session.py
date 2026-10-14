"""Motor + sesion + contexto de tenant.

Motores soportados:
- SQLite (dev local).
- Oracle (local XE/Free y Autonomous DB en la nube) con VPD (ver sql/vpd_oracle.sql).
- Postgres (legado, sql/rls.sql).

En Oracle, TODA tabla operativa se filtra por VPD segun el contexto APP_CTX,
que se fija por pedido y se limpia al devolver la conexion al pool.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _build_engine():
    if settings.ORACLE_DSN:
        # ADB con TLS sin wallet (Vercel/pruebas): usuario/clave por connect_args, sin URL-encoding.
        return create_engine(
            "oracle+oracledb:///",
            pool_pre_ping=True,
            connect_args={"user": settings.ORACLE_USER, "password": settings.ORACLE_PASSWORD, "dsn": settings.ORACLE_DSN},
        )
    if settings.DATABASE_URL.startswith("sqlite"):
        return create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False})
    # Oracle con wallet/alias (DATABASE_URL=oracle+oracledb://USER:CLAVE@ALIAS + TNS_ADMIN)
    # o Postgres legado.
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _dialecto() -> str:
    return engine.dialect.name


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_rls_tenant(db, tenant_id: str) -> None:
    """Fija el tenant para aislamiento. Exige VPD/RLS instalado; falla rapido si no (mejor que filtrar mal)."""
    d = _dialecto()
    if d == "postgresql" and tenant_id:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
    elif d == "oracle" and tenant_id:
        db.execute(text("BEGIN estila_ctx_pkg.set_tenant(:tid); END;"), {"tid": tenant_id})


@contextmanager
def auth_mode(db):
    """Consultas globales previas al tenant (login, alta de tenant, unicidad de email).
    En Oracle usa AUTH_MODE del VPD; en otros motores no hace nada."""
    if _dialecto() != "oracle":
        yield
        return
    db.execute(text("BEGIN estila_ctx_pkg.set_auth(1); END;"))
    try:
        yield
    finally:
        db.execute(text("BEGIN estila_ctx_pkg.set_auth(0); END;"))


if _dialecto() == "oracle":

    @event.listens_for(engine, "checkin")
    def _limpiar_contexto(dbapi_conn, _rec):
        # Higiene del pool: ninguna conexion vuelve con tenant ajeno.
        try:
            cur = dbapi_conn.cursor()
            cur.execute("BEGIN estila_ctx_pkg.clear_all; END;")
            cur.close()
        except Exception:
            pass
