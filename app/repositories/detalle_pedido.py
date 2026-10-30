from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.detalle_pedido import (
    DetallePedido,
    DetallePedidoCreate,
    DetallePedidoUpdate,
)
from app.repositories.base import BaseRepository


class DetallePedidoRepository(
    BaseRepository[DetallePedido, DetallePedidoCreate, DetallePedidoUpdate]
):
    """Capa de Acceso a Datos para la entidad DetallePedido (líneas de un pedido).

    Hereda get_by_id, get_multi y delete de BaseRepository.
    Para crear un detalle se usa create_for_pedido (no create), porque id_pedido
    llega por la URL y precio_unitario lo decide el servicio, no el cliente.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DetallePedido, session)

    # ==========================================
    # OPERACIONES DE LECTURA (READ)
    # ==========================================

    async def get_by_pedido(self, pedido_id: int) -> list[DetallePedido]:
        """Lista todas las líneas de un pedido ordenadas por ID."""
        statement = (
            select(DetallePedido)
            .where(DetallePedido.id_pedido == pedido_id)
            .order_by(DetallePedido.id)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_and_pedido(
        self, detalle_id: int, pedido_id: int
    ) -> DetallePedido | None:
        """Busca un detalle solo si pertenece al pedido indicado. Retorna None si no."""
        statement = select(DetallePedido).where(
            DetallePedido.id == detalle_id,
            DetallePedido.id_pedido == pedido_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    # ==========================================
    # OPERACIÓN DE CREACIÓN (CREATE)
    # ==========================================

    async def create_for_pedido(
        self,
        *,
        pedido_id: int,
        detalle_in: DetallePedidoCreate,
        precio_unitario: Decimal,
    ) -> DetallePedido:
        """Inserta una línea en el pedido guardando el precio del momento.

        precio_unitario lo entrega el servicio (copiado del precio actual del plato);
        el subtotal se deriva de él para mantener la fila consistente.
        """
        db_detalle = DetallePedido.model_validate(
            detalle_in,
            update={
                "id_pedido": pedido_id,
                "precio_unitario": precio_unitario,
                "subtotal": precio_unitario * detalle_in.cantidad,
            },
        )
        self.session.add(db_detalle)
        await self.session.commit()
        await self.session.refresh(db_detalle)
        return db_detalle

    # ==========================================
    # OPERACIÓN DE ACTUALIZACIÓN (UPDATE)
    # ==========================================

    async def update(
        self, db_obj: DetallePedido, obj_in: DetallePedidoUpdate
    ) -> DetallePedido:
        """Actualiza parcialmente un detalle y recalcula su subtotal.

        El precio_unitario no cambia: se conserva el precio cobrado al momento del pedido.
        """
        update_data: dict[str, Any] = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.subtotal = db_obj.precio_unitario * db_obj.cantidad
        db_obj.updated_at = datetime.now(timezone.utc)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
