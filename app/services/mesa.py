from fastapi import HTTPException, status

# 1. Modelos ORM y DTOs de entrada
from app.models.mesa import EstadoMesa, Mesa, MesaCreate, MesaUpdate

# 2. Repositorios: el de Mesa y el de Pedido (para proteger el historial al borrar)
from app.repositories.mesa import MesaRepository
from app.repositories.pedido import PedidoRepository


class MesaService:
    """
    Capa de Lógica de Negocio para Mesas.
    Valida que el número de mesa sea único y que no se borren mesas con historial.
    """

    def __init__(
        self,
        mesa_repo: MesaRepository,
        pedido_repo: PedidoRepository,  # Para saber si la mesa tiene pedidos
    ) -> None:
        self.mesa_repo = mesa_repo
        self.pedido_repo = pedido_repo

    # ==========================================
    # OPERACIONES DE LECTURA (READ)
    # ==========================================

    async def get_by_id(self, mesa_id: int) -> Mesa:
        """Busca una mesa por ID o lanza 404 si no existe."""
        mesa = await self.mesa_repo.get_by_id(mesa_id)
        if not mesa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesa no encontrada",
            )
        return mesa

    async def list_all(
        self,
        *,
        estado: EstadoMesa | None = None,
        capacidad_minima: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Mesa]:
        """Lista mesas con filtros opcionales (ej: GET /tables?estado=libre)."""
        return await self.mesa_repo.get_filtered(
            estado=estado,
            capacidad_minima=capacidad_minima,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # OPERACIÓN DE CREACIÓN (CREATE)
    # ==========================================

    async def create(self, mesa_in: MesaCreate) -> Mesa:
        """
        Regla de negocio:
        - No pueden existir dos mesas con el mismo número.
        """
        existing = await self.mesa_repo.get_by_numero(mesa_in.numero)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una mesa con el número {mesa_in.numero}",
            )
        return await self.mesa_repo.create(mesa_in)

    # ==========================================
    # OPERACIÓN DE ACTUALIZACIÓN (UPDATE)
    # ==========================================

    async def update(self, mesa_id: int, mesa_in: MesaUpdate) -> Mesa:
        """
        Regla de negocio:
        - La mesa debe existir.
        - Si cambia el número, no debe chocar con otra mesa.
        """
        mesa = await self.get_by_id(mesa_id)

        if mesa_in.numero is not None and mesa_in.numero != mesa.numero:
            existing = await self.mesa_repo.get_by_numero(mesa_in.numero)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El número de mesa {mesa_in.numero} ya está en uso",
                )

        return await self.mesa_repo.update(mesa, mesa_in)

    # ==========================================
    # OPERACIÓN DE ELIMINACIÓN (DELETE)
    # ==========================================

    async def delete(self, mesa_id: int) -> None:
        """
        Regla de negocio:
        - No se puede borrar una mesa con pedidos registrados (historial de ventas).
          La FK Pedido.id_mesa es RESTRICT: se valida aquí para responder 400
          en lugar de dejar que la BD lance un IntegrityError (500).
        """
        mesa = await self.get_by_id(mesa_id)

        pedidos = await self.pedido_repo.get_filtered(id_mesa=mesa_id, limit=1)
        if pedidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la mesa porque tiene pedidos registrados",
            )

        await self.mesa_repo.delete(mesa)
