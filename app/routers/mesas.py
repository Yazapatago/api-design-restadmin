from fastapi import APIRouter, Query, status

from app.api.deps import MesaServiceDep, PedidoServiceDep
from app.models.mesa import EstadoMesa, Mesa, MesaCreate, MesaPublic, MesaUpdate
from app.models.pedido import EstadoPedido, Pedido, PedidoPublic

router = APIRouter(prefix="/tables", tags=["Mesas"])


# ==========================================
# CREATE
# ==========================================
@router.post("/", response_model=MesaPublic, status_code=status.HTTP_201_CREATED)
async def create_mesa(mesa_in: MesaCreate, service: MesaServiceDep) -> Mesa:
    """Registra una nueva mesa. 400 si el número ya existe."""
    return await service.create(mesa_in)


# ==========================================
# READ
# ==========================================
@router.get("/", response_model=list[MesaPublic])
async def list_mesas(
    service: MesaServiceDep,
    estado: EstadoMesa | None = None,
    capacidad_minima: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Mesa]:
    """Lista mesas con filtros opcionales (ej: ?estado=libre)."""
    return await service.list_all(
        estado=estado, capacidad_minima=capacidad_minima, skip=skip, limit=limit
    )


@router.get("/{mesa_id}", response_model=MesaPublic)
async def get_mesa(mesa_id: int, service: MesaServiceDep) -> Mesa:
    """Obtiene una mesa por ID. 404 si no existe."""
    return await service.get_by_id(mesa_id)


# ==========================================
# UPDATE (PATCH: solo los campos enviados)
# ==========================================
@router.patch("/{mesa_id}", response_model=MesaPublic)
async def update_mesa(
    mesa_id: int, mesa_in: MesaUpdate, service: MesaServiceDep
) -> Mesa:
    """Actualiza parcialmente una mesa (ej: {"estado": "ocupada"})."""
    return await service.update(mesa_id, mesa_in)


# ==========================================
# DELETE
# ==========================================
@router.delete("/{mesa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesa(mesa_id: int, service: MesaServiceDep) -> None:
    """Elimina una mesa. 400 si tiene pedidos registrados."""
    await service.delete(mesa_id)


# ==========================================
# RELACIÓN: Mesa -> Pedidos
# ==========================================
@router.get("/{mesa_id}/orders", response_model=list[PedidoPublic])
async def list_pedidos_de_mesa(
    mesa_id: int,
    service: PedidoServiceDep,
    estado: EstadoPedido | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Pedido]:
    """Pedidos de una mesa (ej: ?estado=pendiente). 404 si la mesa no existe."""
    return await service.list_all(
        id_mesa=mesa_id, estado=estado, skip=skip, limit=limit
    )
