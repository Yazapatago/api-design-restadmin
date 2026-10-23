from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


# ==========================================
# 1. Base común (propiedades compartidas)
# ==========================================
class DetallePedidoBase(SQLModel):
    """Propiedades que el cliente puede enviar.

    Nota: id_pedido e id_plato (FK) se agregarán en la clase de relaciones.
    """

    cantidad: int = Field(gt=0, description="Unidades pedidas del plato")
    notas: str | None = Field(
        default=None, max_length=255, description="Indicaciones para cocina (ej: sin cebolla)"
    )


# ==========================================
# 2. Modelo de base de datos (tabla ORM)
# ==========================================
class DetallePedido(DetallePedidoBase, table=True):
    """Tabla 'detalles_pedido'.

    precio_unitario y subtotal los calcula el servidor. Cuando exista la FK
    a Plato, precio_unitario se copiará del precio del plato al momento del pedido.
    """

    __tablename__ = "detalles_pedido"

    id: int | None = Field(default=None, primary_key=True)
    precio_unitario: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2
    )
    subtotal: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )


# ==========================================
# 3. DTOs de la API
# ==========================================
class DetallePedidoCreate(DetallePedidoBase):
    """Schema para crear o reemplazar (PUT) un detalle."""

    pass


class DetallePedidoUpdate(SQLModel):
    """Schema para actualizar parcialmente (PATCH): todo opcional."""

    cantidad: int | None = Field(default=None, gt=0)
    notas: str | None = Field(default=None, max_length=255)


class DetallePedidoPublic(DetallePedidoBase):
    """Schema de respuesta pública."""

    id: int
    precio_unitario: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime
