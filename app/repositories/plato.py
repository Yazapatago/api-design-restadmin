from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.plato import CategoriaPlato, Plato, PlatoCreate, PlatoUpdate
from app.repositories.base import BaseRepository


class PlatoRepository(BaseRepository[Plato, PlatoCreate, PlatoUpdate]):
    """Capa de Acceso a Datos para la entidad Plato (menú).

    Hereda get_by_id, get_multi, create, update y delete de BaseRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Plato, session)

    async def get_filtered(
        self,
        *,
        search: str | None = None,
        categoria: CategoriaPlato | None = None,
        solo_disponibles: bool = False,
        precio_min: Decimal | None = None,
        precio_max: Decimal | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Plato]:
        """Consulta dinámica del menú aplicando únicamente los filtros que se envíen."""
        statement = select(Plato)

        # Filtro 1: Búsqueda parcial por nombre (insensible a mayúsculas/minúsculas)
        if search:
            statement = statement.where(col(Plato.nombre).ilike(f"%{search}%"))

        # Filtro 2: Categoría (entrada, plato_fuerte, bebida, postre)
        if categoria is not None:
            statement = statement.where(Plato.categoria == categoria)

        # Filtro 3: Solo platos que se pueden pedir (no agotados)
        if solo_disponibles:
            statement = statement.where(Plato.disponible == True)  # noqa: E712

        # Filtro 4: Precio mínimo
        if precio_min is not None:
            statement = statement.where(Plato.precio >= precio_min)

        # Filtro 5: Precio máximo
        if precio_max is not None:
            statement = statement.where(Plato.precio <= precio_max)

        # Ordenamiento y paginación al final
        statement = statement.order_by(Plato.id).offset(skip).limit(limit)

        result = await self.session.execute(statement)
        return list(result.scalars().all())
