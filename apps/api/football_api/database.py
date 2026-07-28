"""Motor SQLAlchemy y ciclo de vida de sesiones de base de datos."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from football_api.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa común para que Alembic descubra todos los modelos."""

    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Inyecta una sesión por petición y garantiza su cierre."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
