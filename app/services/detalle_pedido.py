from fastapi import HTTPException, status

from app.models.detalle_pedido import (
    DetallePedido,
    DetallePedidoCreate,
    DetallePedidoUpdate,
)
from app.models.pedido import EstadoPedido
from app.repositories.detalle_pedido import DetallePedidoRepository
from app.repositories.pedido import PedidoRepository
from app.repositories.plato import PlatoRepository


class DetallePedidoService:
    """Capa de Lógica de Negocio para Detalles de Pedido.

    Coordina la validación del pedido y del plato, la copia del precio unitario
    del momento y el recálculo automático del total del pedido.
    """

    def __init__(
        self,
        detalle_repo: DetallePedidoRepository,
        pedido_repo: PedidoRepository,
        plato_repo: PlatoRepository,
    ) -> None:
        self.detalle_repo = detalle_repo
        self.pedido_repo = pedido_repo
        self.plato_repo = plato_repo

    async def get_by_id(self, detalle_id: int) -> DetallePedido:
        """Busca un detalle de pedido por ID o lanza 404 si no existe."""
        detalle = await self.detalle_repo.get_by_id(detalle_id)
        if not detalle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Detalle de pedido no encontrado",
            )
        return detalle

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DetallePedido]:
        """Obtiene la lista de detalles de pedido paginados."""
        return await self.detalle_repo.get_multi(skip=skip, limit=limit)

    async def list_by_pedido(self, pedido_id: int) -> list[DetallePedido]:
        """Obtiene todas las líneas de un pedido validando que el pedido exista."""
        pedido = await self.pedido_repo.get_by_id(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        return await self.detalle_repo.get_by_pedido(pedido_id)

    async def create(
        self,
        pedido_id: int,
        detalle_in: DetallePedidoCreate,
    ) -> DetallePedido:
        """Agrega un plato a un pedido copiando su precio actual y actualizando el total."""
        # 1. Validar que el pedido exista y admita modificaciones
        pedido = await self.pedido_repo.get_by_id(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        if pedido.estado in (EstadoPedido.PAGADO, EstadoPedido.CANCELADO):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pueden agregar platos a un pedido en estado '{pedido.estado.value}'",
            )

        # 2. Validar que el plato exista y esté disponible
        plato = await self.plato_repo.get_by_id(detalle_in.id_plato)
        if not plato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El plato indicado no existe",
            )
        if not plato.disponible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El plato solicitado no está disponible",
            )

        # 3. Crear el detalle con el precio del momento y recalcular el total del pedido
        detalle = await self.detalle_repo.create_for_pedido(
            pedido_id=pedido_id,
            detalle_in=detalle_in,
            precio_unitario=plato.precio,
        )
        await self.pedido_repo.update_total(pedido)
        return detalle

    async def update(
        self,
        detalle_id: int,
        detalle_in: DetallePedidoUpdate,
    ) -> DetallePedido:
        """Actualiza un detalle de pedido y recalcula el total del pedido asociado."""
        detalle = await self.get_by_id(detalle_id)
        detalle_actualizado = await self.detalle_repo.update(detalle, detalle_in)

        if detalle_actualizado.id_pedido is not None:
            pedido = await self.pedido_repo.get_by_id(detalle_actualizado.id_pedido)
            if pedido:
                await self.pedido_repo.update_total(pedido)

        return detalle_actualizado

    async def delete(self, detalle_id: int) -> None:
        """Elimina un detalle por su ID y recalcula el total del pedido asociado."""
        detalle = await self.get_by_id(detalle_id)
        pedido_id = detalle.id_pedido

        await self.detalle_repo.delete(detalle)

        if pedido_id is not None:
            pedido = await self.pedido_repo.get_by_id(pedido_id)
            if pedido:
                await self.pedido_repo.update_total(pedido)

    async def delete_from_pedido(self, pedido_id: int, detalle_id: int) -> None:
        """Elimina un detalle verificando que pertenezca al pedido indicado y recalcula el total."""
        detalle = await self.detalle_repo.get_by_id_and_pedido(detalle_id, pedido_id)
        if not detalle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El detalle no existe en el pedido indicado",
            )

        await self.detalle_repo.delete(detalle)

        pedido = await self.pedido_repo.get_by_id(pedido_id)
        if pedido:
            await self.pedido_repo.update_total(pedido)
