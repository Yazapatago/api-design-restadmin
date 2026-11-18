from fastapi import APIRouter, Query, status

from app.api.deps import DetallePedidoServiceDep, PedidoServiceDep
from app.models.detalle_pedido import DetallePedido, DetallePedidoCreate, DetallePedidoPublic
from app.models.pedido import (
    EstadoPedido,
    Pedido,
    PedidoConDetallesPublic,
    PedidoCreate,
    PedidoPublic,
    PedidoUpdate,
)

router = APIRouter(prefix="/orders", tags=["Pedidos"])


# ==========================================
# CREATE
# ==========================================
@router.post("/", response_model=PedidoPublic, status_code=status.HTTP_201_CREATED)
async def create_pedido(pedido_in: PedidoCreate, service: PedidoServiceDep) -> Pedido:
    """Crea un pedido para una mesa. 404 si la mesa no existe."""
    return await service.create(pedido_in)


# ==========================================
# READ
# ==========================================
@router.get("/", response_model=list[PedidoPublic])
async def list_pedidos(
    service: PedidoServiceDep,
    id_mesa: int | None = None,
    estado: EstadoPedido | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Pedido]:
    """Lista pedidos (ej: ?estado=pendiente para la cocina)."""
    return await service.list_all(
        id_mesa=id_mesa, estado=estado, skip=skip, limit=limit
    )


@router.get("/{pedido_id}", response_model=PedidoConDetallesPublic)
async def get_pedido(pedido_id: int, service: PedidoServiceDep) -> Pedido:
    """Obtiene un pedido con sus detalles y total. 404 si no existe."""
    return await service.get_with_detalles(pedido_id)


# ==========================================
# UPDATE (PATCH: solo los campos enviados)
# ==========================================
@router.patch("/{pedido_id}", response_model=PedidoPublic)
async def update_pedido(
    pedido_id: int, pedido_in: PedidoUpdate, service: PedidoServiceDep
) -> Pedido:
    """Actualiza parcialmente un pedido (ej: {"estado": "entregado"})."""
    return await service.update(pedido_id, pedido_in)


# ==========================================
# DELETE
# ==========================================
@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pedido(pedido_id: int, service: PedidoServiceDep) -> None:
    """Elimina un pedido. 400 si no está en estado pendiente."""
    await service.delete(pedido_id)


# ==========================================
# RELACIÓN: Pedido -> Detalles (items)
# ==========================================
@router.get("/{pedido_id}/items", response_model=list[DetallePedidoPublic])
async def list_items_de_pedido(
    pedido_id: int, service: DetallePedidoServiceDep
) -> list[DetallePedido]:
    """Platos de un pedido. 404 si el pedido no existe."""
    return await service.list_by_pedido(pedido_id)


@router.post(
    "/{pedido_id}/items",
    response_model=DetallePedidoPublic,
    status_code=status.HTTP_201_CREATED,
)
async def add_item_a_pedido(
    pedido_id: int, detalle_in: DetallePedidoCreate, service: DetallePedidoServiceDep
) -> DetallePedido:
    """Agrega un plato al pedido. El precio se copia del plato y se recalcula el total."""
    return await service.create(pedido_id, detalle_in)


@router.delete("/{pedido_id}/items/{detalle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_de_pedido(
    pedido_id: int, detalle_id: int, service: DetallePedidoServiceDep
) -> None:
    """Quita un plato del pedido. 404 si el detalle no pertenece a ese pedido."""
    await service.delete_from_pedido(pedido_id, detalle_id)
