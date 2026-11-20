from decimal import Decimal

from fastapi import HTTPException, status

from app.models.detalle_pedido import DetallePedidoCreate
from app.models.pedido import (
    EstadoPedido,
    Pedido,
    PedidoCreate,
    PedidoReplace,
    PedidoUpdate,
)
from app.repositories.mesa import MesaRepository
from app.repositories.pedido import PedidoRepository
from app.repositories.plato import PlatoRepository


class PedidoService:
    """Capa de Lógica de Negocio para Pedidos.

    Coordina la validación de la mesa asociada, los platos iniciales del pedido,
    su ciclo de vida y el acceso a datos mediante PedidoRepository,
    MesaRepository y PlatoRepository.
    """

    def __init__(
        self,
        pedido_repo: PedidoRepository,
        mesa_repo: MesaRepository,
        plato_repo: PlatoRepository,  # Para validar los items al crear el pedido
    ) -> None:
        self.pedido_repo = pedido_repo
        self.mesa_repo = mesa_repo
        self.plato_repo = plato_repo

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

    async def _validar_mesa(self, mesa_id: int) -> None:
        """Lanza 404 si la mesa indicada no existe."""
        mesa = await self.mesa_repo.get_by_id(mesa_id)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La mesa indicada no existe",
            )

    async def create(self, pedido_in: PedidoCreate) -> Pedido:
        """Crea un pedido con sus platos iniciales (items) en una sola operación.

        Reglas de negocio:
        - La mesa debe existir (404).
        - Cada plato debe existir (404) y estar disponible (400).
        - Se valida TODO antes de guardar: si un plato falla, no se crea nada.
        - El precio unitario se copia del precio actual de cada plato.
        """
        await self._validar_mesa(pedido_in.id_mesa)

        items: list[tuple[DetallePedidoCreate, Decimal]] = []
        for item in pedido_in.items:
            plato = await self.plato_repo.get_by_id(item.id_plato)
            if not plato:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El plato {item.id_plato} no existe",
                )
            if not plato.disponible:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El plato '{plato.nombre}' no está disponible",
                )
            items.append((item, plato.precio))

        pedido = await self.pedido_repo.create_with_items(
            pedido_in=pedido_in, items=items
        )
        # Se devuelve con sus detalles cargados para la respuesta
        return await self.get_with_detalles(pedido.id)  # type: ignore[arg-type]

    async def update(self, pedido_id: int, pedido_in: PedidoUpdate) -> Pedido:
        """Actualiza parcialmente un pedido previa verificación de su existencia."""
        pedido = await self.get_by_id(pedido_id)
        return await self.pedido_repo.update(pedido, pedido_in)

    async def replace(self, pedido_id: int, pedido_in: PedidoReplace) -> Pedido:
        """PUT: reemplaza mesa y observaciones. La nueva mesa debe existir."""
        pedido = await self.get_by_id(pedido_id)
        await self._validar_mesa(pedido_in.id_mesa)
        return await self.pedido_repo.replace(pedido, pedido_in)

    async def delete(self, pedido_id: int) -> None:
        """Elimina un pedido solo si existe y se encuentra en estado pendiente."""
        pedido = await self.get_by_id(pedido_id)
        if pedido.estado != EstadoPedido.PENDIENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden eliminar pedidos en estado pendiente",
            )

        await self.pedido_repo.delete(pedido)