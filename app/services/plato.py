from decimal import Decimal

from fastapi import HTTPException, status

# 1. Modelos ORM y DTOs de entrada
from app.models.plato import CategoriaPlato, Plato, PlatoCreate, PlatoUpdate

# 2. Repositorio correspondiente
from app.repositories.plato import PlatoRepository


class PlatoService:
    """
    Capa de Lógica de Negocio para el Menú (Platos).
    Plato no depende de otras entidades para crearse o actualizarse,
    por eso solo recibe su propio repositorio.
    """

    def __init__(self, plato_repo: PlatoRepository) -> None:
        self.plato_repo = plato_repo

    # ==========================================
    # OPERACIONES DE LECTURA (READ)
    # ==========================================

    async def get_by_id(self, plato_id: int) -> Plato:
        """Busca un plato por ID o lanza 404 si no existe."""
        plato = await self.plato_repo.get_by_id(plato_id)
        if not plato:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plato no encontrado",
            )
        return plato

    async def list_all(
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
        """Lista el menú con filtros opcionales (ej: GET /dishes?categoria=bebida)."""
        return await self.plato_repo.get_filtered(
            search=search,
            categoria=categoria,
            solo_disponibles=solo_disponibles,
            precio_min=precio_min,
            precio_max=precio_max,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # OPERACIÓN DE CREACIÓN (CREATE)
    # ==========================================

    async def create(self, plato_in: PlatoCreate) -> Plato:
        """Agrega un plato al menú.

        El nombre no es único en el modelo y las validaciones de formato
        (precio > 0, longitud del nombre) ya las garantiza PlatoCreate.
        """
        return await self.plato_repo.create(plato_in)

    # ==========================================
    # OPERACIÓN DE ACTUALIZACIÓN (UPDATE)
    # ==========================================

    async def update(self, plato_id: int, plato_in: PlatoUpdate) -> Plato:
        """Actualiza el plato (ej: PATCH {"disponible": false} para marcarlo agotado)."""
        plato = await self.get_by_id(plato_id)
        return await self.plato_repo.update(plato, plato_in)

    # ==========================================
    # OPERACIÓN DE ELIMINACIÓN (DELETE)
    # ==========================================

    async def delete(self, plato_id: int) -> None:
        """Elimina un plato del menú previa verificación de su existencia."""
        plato = await self.get_by_id(plato_id)
        await self.plato_repo.delete(plato)
