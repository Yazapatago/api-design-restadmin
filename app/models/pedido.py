from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlmodel import AutoString, Field, SQLModel


# ==========================================
# Valores permitidos (según el README)
# ==========================================
class EstadoPedido(str, Enum):
    """Estados del ciclo de vida de un pedido. Se guardan como texto en la BD."""

    PENDIENTE = "pendiente"
    EN_PREPARACION = "en_preparacion"
    ENTREGADO = "entregado"
    PAGADO = "pagado"
    CANCELADO = "cancelado"


# ==========================================
# 1. Base común (propiedades compartidas)
# ==========================================
class PedidoBase(SQLModel):
    """Propiedades que el cliente puede enviar.

    Nota: id_mesa (FK) se agregará en la clase de relaciones.
    """

    observaciones: str | None = Field(
        default=None, max_length=500, description="Comentarios generales del pedido"
    )


# ==========================================
# 2. Modelo de base de datos (tabla ORM)
# ==========================================
class Pedido(PedidoBase, table=True):
    """Tabla 'pedidos'.

    estado, total y fecha_hora los controla el servidor, no el cliente.
    """

    __tablename__ = "pedidos"

    id: int | None = Field(default=None, primary_key=True)
    fecha_hora: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    estado: EstadoPedido = Field(default=EstadoPedido.PENDIENTE, sa_type=AutoString)
    total: Decimal = Field(
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
class PedidoCreate(PedidoBase):
    """Schema para crear (POST) o reemplazar (PUT) un pedido.

    Los 'items' del README dependen de relaciones y se agregarán después.
    """

    pass


class PedidoUpdate(SQLModel):
    """Schema para actualizar parcialmente (PATCH): todo opcional."""

    observaciones: str | None = Field(default=None, max_length=500)
    estado: EstadoPedido | None = Field(default=None)


class PedidoPublic(PedidoBase):
    """Schema de respuesta pública."""

    id: int
    fecha_hora: datetime
    estado: EstadoPedido
    total: Decimal
    created_at: datetime
    updated_at: datetime
