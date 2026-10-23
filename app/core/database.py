"""Conexión a PostgreSQL.

La URL se lee de la variable de entorno DATABASE_URL.
Formato: postgresql+psycopg://usuario:contraseña@host:puerto/base_de_datos
"""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  (registra las tablas en SQLModel.metadata)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/restadmin",
)

# echo=True imprime el SQL generado en consola (útil para aprender; desactívalo en producción)
engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)


def create_db_and_tables() -> None:
    """Crea las tablas que aún no existen (no modifica las existentes)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesión por petición y la cierra al final."""
    with Session(engine) as session:
        yield session
