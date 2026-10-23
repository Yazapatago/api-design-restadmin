from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlmodel import AutoString, Field, SQLModel


# ==========================================
# Valores permitidos (según el README)
# ==========================================
class CategoriaPlato(str, Enum):
    """Categorías del menú. Se guardan como texto en la BD."""

    ENTRADA = "entrada"
    PLATO_FUERTE = "plato_fuerte"
    BEBIDA = "bebida"
    POSTRE = "postre"


# ==========================================
# 1. Base común (propiedades compartidas)
# ==========================================
class PlatoBase(SQLModel):
    """Propiedades base compartidas por la tabla y los DTOs."""

    nombre: str = Field(
        min_length=2, max_length=100, index=True, description="Nombre del plato"
    )
    descripcion: str | None = Field(
        default=None, max_length=500, description="Descripción opcional"
    )
    categoria: CategoriaPlato = Field(
        sa_type=AutoString,
        description="entrada, plato_fuerte, bebida o postre",
    )
    precio: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Precio actual del menú (mayor a 0)",
    )
    disponible: bool = Field(default=True, description="Si se puede pedir o está agotado")


# ==========================================
# 2. Modelo de base de datos (tabla ORM)
# ==========================================
class Plato(PlatoBase, table=True):
    """Tabla 'platos'."""

    __tablename__ = "platos"

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
class PlatoCreate(PlatoBase):
    """Schema para crear (POST) o reemplazar (PUT) un plato."""

    pass


class PlatoUpdate(SQLModel):
    """Schema para actualizar parcialmente (PATCH): todo opcional."""

    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria: CategoriaPlato | None = Field(default=None)
    precio: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    disponible: bool | None = Field(default=None)


class PlatoPublic(PlatoBase):
    """Schema de respuesta pública."""

    id: int
    created_at: datetime
    updated_at: datetime
