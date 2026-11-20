from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional
from pydantic import ConfigDict
from sqlmodel import AutoString, Field, Relationship, SQLModel
from app.models.detalle_pedido import DetallePedidoCreate, DetallePedidoPublic


if TYPE_CHECKING:
    from app.models.detalle_pedido import DetallePedido
    from app.models.mesa import Mesa


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
    """Propiedades que el cliente puede enviar."""

    observaciones: str | None = Field(
        default=None, max_length=500, description="Comentarios generales del pedido"
    )

    # Clave foránea obligatoria: cada pedido pertenece a una sola mesa.
    # RESTRICT: no se puede borrar una mesa que tenga pedidos (historial de ventas).
    id_mesa: int = Field(
        foreign_key="mesas.id",
        ondelete="RESTRICT",
        index=True,
        description="ID de la mesa que registra el pedido",
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

    # LADO 'MUCHOS' (Mesa -> Pedido 1:N): la mesa a la que pertenece el pedido.
    mesa: Optional["Mesa"] = Relationship(back_populates="pedidos")

    # LADO '1' (Pedido -> DetallePedido 1:N): líneas del pedido.
    # Un detalle no existe sin su pedido: al borrar el pedido se borran sus detalles
    # (cascade_delete en el ORM + ondelete="CASCADE" en la FK de DetallePedido).
    detalles: list["DetallePedido"] = Relationship(
        back_populates="pedido",
        cascade_delete=True,
    )


# ==========================================
# 3. DTOs de la API
# ==========================================
class PedidoCreate(PedidoBase):
    """Schema para crear (POST) un pedido, opcionalmente con sus platos.

    Ej: {"id_mesa": 3, "items": [{"id_plato": 7, "cantidad": 2}]}
    Si no se envían items, el pedido se crea vacío y los platos se agregan
    después con POST /orders/{id}/items.
    """

    # Ejemplo que muestran Swagger (/docs) y Scalar (/scalar) en el cuerpo de la petición
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id_mesa": 1,
                    "observaciones": "Cliente con prisa, traer la bebida primero",
                    "items": [
                        {"id_plato": 1, "cantidad": 2, "notas": "Sin chicharrón"},
                        {"id_plato": 2, "cantidad": 2, "notas": "Limonada de coco bien fría"},
                    ],
                }
            ]
        }
    )

    items: list[DetallePedidoCreate] = Field(
        default_factory=list, description="Platos iniciales del pedido"
    )


class PedidoReplace(PedidoBase):
    """Schema para reemplazar (PUT) los datos generales de un pedido.

    No incluye items: los platos se gestionan con /orders/{id}/items.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"id_mesa": 3, "observaciones": "Se pasaron a la mesa de la ventana"}]
        }
    )


class PedidoUpdate(SQLModel):
    """Schema para actualizar parcialmente (PATCH): todo opcional."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"estado": "en_preparacion"}]}
    )

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


class PedidoConDetallesPublic(PedidoPublic):
    """Respuesta de GET /orders/{id}: el pedido con sus detalles.

    DetallePedidoPublic solo expone id_pedido e id_plato (no los objetos
    completos), así la serialización termina aquí y no hay ciclos.
    """

    detalles: list[DetallePedidoPublic] = []