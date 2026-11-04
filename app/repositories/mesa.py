from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.mesa import EstadoMesa, Mesa, MesaCreate, MesaUpdate
from app.repositories.base import BaseRepository


class MesaRepository(BaseRepository[Mesa, MesaCreate, MesaUpdate]):
    """Capa de Acceso a Datos para la entidad Mesa.

    Hereda get_by_id, get_multi, create, update y delete de BaseRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Mesa, session)

    async def get_by_numero(self, numero: int) -> Mesa | None:
        """Busca una mesa por su número visible (unique). Retorna None si no existe."""
        statement = select(Mesa).where(Mesa.numero == numero)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        *,
        estado: EstadoMesa | None = None,
        capacidad_minima: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Mesa]:
        """Lista mesas aplicando únicamente los filtros que se envíen."""
        statement = select(Mesa)

        # Filtro 1: Estado (libre, ocupada, reservada)
        if estado is not None:
            statement = statement.where(Mesa.estado == estado)

        # Filtro 2: Mesas donde caben al menos 'capacidad_minima' personas
        if capacidad_minima is not None:
            statement = statement.where(Mesa.capacidad >= capacidad_minima)

        # Ordenamiento y paginación al final
        statement = statement.order_by(Mesa.numero).offset(skip).limit(limit)

        result = await self.session.execute(statement)
        return list(result.scalars().all())
