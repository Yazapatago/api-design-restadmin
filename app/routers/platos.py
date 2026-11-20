from decimal import Decimal

from fastapi import APIRouter, Query, status

from app.api.deps import PlatoServiceDep
from app.models.plato import CategoriaPlato, Plato, PlatoCreate, PlatoPublic, PlatoUpdate

router = APIRouter(prefix="/dishes", tags=["Platos"])


# ==========================================
# CREATE
# ==========================================
@router.post("/", response_model=PlatoPublic, status_code=status.HTTP_201_CREATED)
async def create_plato(plato_in: PlatoCreate, service: PlatoServiceDep) -> Plato:
    """Agrega un plato al menú."""
    return await service.create(plato_in)


# ==========================================
# READ
# ==========================================
@router.get("/", response_model=list[PlatoPublic])
async def list_platos(
    service: PlatoServiceDep,
    search: str | None = Query(default=None, description="Búsqueda parcial por nombre"),
    categoria: CategoriaPlato | None = None,
    disponible: bool | None = Query(
        default=None, description="true = disponibles, false = agotados"
    ),
    precio_min: Decimal | None = Query(default=None, ge=0),
    precio_max: Decimal | None = Query(default=None, ge=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Plato]:
    """Lista el menú con filtros opcionales (ej: ?categoria=bebida&disponible=true)."""
    return await service.list_all(
        search=search,
        categoria=categoria,
        disponible=disponible,
        precio_min=precio_min,
        precio_max=precio_max,
        skip=skip,
        limit=limit,
    )


@router.get("/{plato_id}", response_model=PlatoPublic)
async def get_plato(plato_id: int, service: PlatoServiceDep) -> Plato:
    """Obtiene un plato por ID. 404 si no existe."""
    return await service.get_by_id(plato_id)


# ==========================================
# UPDATE
#   PUT:   reemplaza todos los datos (campos omitidos vuelven a su valor por defecto)
#   PATCH: solo cambia los campos enviados
# ==========================================
@router.put("/{plato_id}", response_model=PlatoPublic)
async def replace_plato(
    plato_id: int, plato_in: PlatoCreate, service: PlatoServiceDep
) -> Plato:
    """Reemplaza todos los datos de un plato. 404 si no existe."""
    return await service.replace(plato_id, plato_in)


@router.patch("/{plato_id}", response_model=PlatoPublic)
async def update_plato(
    plato_id: int, plato_in: PlatoUpdate, service: PlatoServiceDep
) -> Plato:
    """Actualiza parcialmente un plato (ej: {"disponible": false} para marcarlo agotado)."""
    return await service.update(plato_id, plato_in)


# ==========================================
# DELETE
# ==========================================
@router.delete("/{plato_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plato(plato_id: int, service: PlatoServiceDep) -> None:
    """Elimina un plato del menú."""
    await service.delete(plato_id)