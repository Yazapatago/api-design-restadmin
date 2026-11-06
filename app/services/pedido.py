from fastapi import HTTPException, status

from app.models.pedido import EstadoPedido, Pedido, PedidoCreate, PedidoUpdate
from app.repositories.mesa import MesaRepository
from app.repositories.pedido import PedidoRepository


class PedidoService:
    """Capa de Lógica de Negocio para Pedidos.

    Coordina la validación de la mesa asociada, el ciclo de vida del pedido
    y el acceso a datos mediante PedidoRepository y MesaRepository.
    """

    def __init__(
        self,
        pedido_repo: PedidoRepository,
        mesa_repo: MesaRepository,
    ) -> None:
        self.pedido_repo = pedido_repo
        self.mesa_repo = mesa_repo

    async def get_by_id(self, pedido_id: int) -> Pedido:
        """Busca un pedido por ID o lanza 404 si no existe."""
        pedido = await self.pedido_repo.get_by_id(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        return pedido

    async def get_with_detalles(self, pedido_id: int) -> Pedido:
        """Busca un pedido junto con sus detalles o lanza 404 si no existe."""
        pedido = await self.pedido_repo.get_with_detalles(pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )
        return pedido

    async def list_all(
        self,
        *,
        id_mesa: int | None = None,
        estado: EstadoPedido | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Pedido]:
        """Obtiene la lista de pedidos paginados aplicando filtros opcionales."""
        if id_mesa is not None:
            mesa = await self.mesa_repo.get_by_id(id_mesa)
            if not mesa:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La mesa indicada no existe",
                )

        return await self.pedido_repo.get_filtered(
            id_mesa=id_mesa,
            estado=estado,
            skip=skip,
            limit=limit,
        )

    async def create(self, pedido_in: PedidoCreate) -> Pedido:
        """Crea un nuevo pedido validando previamente que la mesa exista."""
        mesa = await self.mesa_repo.get_by_id(pedido_in.id_mesa)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La mesa indicada no existe",
            )

        return await self.pedido_repo.create(pedido_in)

    async def update(self, pedido_id: int, pedido_in: PedidoUpdate) -> Pedido:
        """Actualiza parcialmente un pedido previa verificación de su existencia."""
        pedido = await self.get_by_id(pedido_id)
        return await self.pedido_repo.update(pedido, pedido_in)

    async def delete(self, pedido_id: int) -> None:
        """Elimina un pedido solo si existe y se encuentra en estado pendiente."""
        pedido = await self.get_by_id(pedido_id)
        if pedido.estado != EstadoPedido.PENDIENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar pedidos en estado pendiente",
            )

        await self.pedido_repo.delete(pedido)
