from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_rls_tenant(db, tenant_id: str) -> None:
    """Fija app.tenant_id para RLS en Postgres; no-op en SQLite dev."""
    if engine.dialect.name == "postgresql" and tenant_id:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
