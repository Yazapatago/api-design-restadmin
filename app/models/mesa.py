from datetime import datetime, timezone
from enum import Enum

from sqlmodel import AutoString, Field, SQLModel


# ==========================================
# Valores permitidos (según el README)
# ==========================================
class EstadoMesa(str, Enum):
    """Estados posibles de una mesa. Se guardan como texto en la BD."""

    LIBRE = "libre"
    OCUPADA = "ocupada"
    RESERVADA = "reservada"


# ==========================================
# 1. Base común (propiedades compartidas)
# ==========================================
class MesaBase(SQLModel):
    """Propiedades base compartidas por la tabla y los DTOs."""

    numero: int = Field(
        gt=0, unique=True, index=True, description="Número visible de la mesa"
    )
    capacidad: int = Field(gt=0, description="Cantidad máxima de personas")
    ubicacion: str | None = Field(
        default=None, max_length=50, description="Zona del restaurante (ej: terraza)"
    )
    estado: EstadoMesa = Field(
        default=EstadoMesa.LIBRE,
        sa_type=AutoString,
        description="Estado actual: libre, ocupada o reservada",
    )


# ==========================================
# 2. Modelo de base de datos (tabla ORM)
# ==========================================
class Mesa(MesaBase, table=True):
    """Tabla 'mesas'."""

    __tablename__ = "mesas"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )


# ==========================================
# 3. DTOs de la API
# ==========================================
class MesaCreate(MesaBase):
    """Schema para crear (POST) o reemplazar (PUT) una mesa."""

    pass


class MesaUpdate(SQLModel):
    """Schema para actualizar parcialmente (PATCH): todo opcional."""

    numero: int | None = Field(default=None, gt=0)
    capacidad: int | None = Field(default=None, gt=0)
    ubicacion: str | None = Field(default=None, max_length=50)
    estado: EstadoMesa | None = Field(default=None)


class MesaPublic(MesaBase):
    """Schema de respuesta pública."""

    id: int
    created_at: datetime
    updated_at: datetime
