from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.pedido import Pedido
    from app.models.plato import Plato


# ==========================================
# 1. Base común (propiedades compartidas)
# ==========================================
class DetallePedidoBase(SQLModel):
    """Propiedades que el cliente puede enviar.

    id_pedido no va aquí: llega por la URL (POST /orders/{id}/items).
    """

    cantidad: int = Field(gt=0, description="Unidades pedidas del plato")
    notas: str | None = Field(
        default=None, max_length=255, description="Indicaciones para cocina (ej: sin cebolla)"
    )

    # Clave foránea obligatoria: cada detalle hace referencia a un solo plato.
    # RESTRICT: no se puede borrar un plato que ya aparece en pedidos (historial).
    id_plato: int = Field(
        foreign_key="platos.id",
        ondelete="RESTRICT",
        index=True,
        description="ID del plato pedido",
    )


# ==========================================
# 2. Modelo de base de datos (tabla ORM)
# ==========================================
class DetallePedido(DetallePedidoBase, table=True):
    """Tabla 'detalles_pedido'.

    Resuelve la relación N:M Pedido <-> Plato guardando además la cantidad y el
    precio del momento. precio_unitario y subtotal los calcula el servidor:
    precio_unitario se copia del precio del plato al momento del pedido.
    """

    __tablename__ = "detalles_pedido"

    id: int | None = Field(default=None, primary_key=True)

    # Clave foránea obligatoria: cada detalle pertenece a un solo pedido.
    # CASCADE: si se borra el pedido, la BD borra también sus detalles.
    # Opcional en Python (el ORM la llena al hacer pedido.detalles.append(...)
    # antes de que el pedido tenga id), pero NOT NULL en la BD.
    id_pedido: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="pedidos.id",
        ondelete="CASCADE",
        index=True,
        description="ID del pedido al que pertenece el detalle",
    )

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

    # LADO 'MUCHOS' (Pedido -> DetallePedido 1:N): el pedido dueño de la línea.
    pedido: Optional["Pedido"] = Relationship(back_populates="detalles")

    # LADO 'MUCHOS' (Plato -> DetallePedido 1:N): el plato de la línea.
    plato: Optional["Plato"] = Relationship(back_populates="detalles")


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
    id_pedido: int
    precio_unitario: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime
