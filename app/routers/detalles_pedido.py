from fastapi import APIRouter, Query, status

from app.api.deps import DetallePedidoServiceDep
from app.models.detalle_pedido import (
    DetallePedido,
    DetallePedidoCreate,
    DetallePedidoPublic,
    DetallePedidoUpdate,
)

# Sin POST aquí: un detalle no existe sin su pedido, se crea con
# POST /orders/{id}/items (ver routers/pedidos.py).
router = APIRouter(prefix="/order-items", tags=["Detalles de Pedido"])


# ==========================================
# READ
# ==========================================
@router.get("/", response_model=list[DetallePedidoPublic])
async def list_detalles(
    service: DetallePedidoServiceDep,
    id_plato: int | None = Query(
        default=None, description="Ver las ventas de un plato (ej: ?id_plato=7)"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[DetallePedido]:
    """Lista los detalles de pedido. 404 si se filtra por un plato que no existe."""
    return await service.list_all(id_plato=id_plato, skip=skip, limit=limit)


@router.get("/{detalle_id}", response_model=DetallePedidoPublic)
async def get_detalle(detalle_id: int, service: DetallePedidoServiceDep) -> DetallePedido:
    """Obtiene un detalle por ID. 404 si no existe."""
    return await service.get_by_id(detalle_id)


# ==========================================
# UPDATE
#   PUT:   reemplaza todos los datos (campos omitidos vuelven a su valor por defecto)
#   PATCH: solo cambia los campos enviados
# ==========================================
@router.put("/{detalle_id}", response_model=DetallePedidoPublic)
async def replace_detalle(
    detalle_id: int, detalle_in: DetallePedidoCreate, service: DetallePedidoServiceDep
) -> DetallePedido:
    """Reemplaza plato, cantidad y notas. Recalcula subtotal y total del pedido."""
    return await service.replace(detalle_id, detalle_in)


@router.patch("/{detalle_id}", response_model=DetallePedidoPublic)
async def update_detalle(
    detalle_id: int, detalle_in: DetallePedidoUpdate, service: DetallePedidoServiceDep
) -> DetallePedido:
    """Cambia cantidad o notas (ej: {"cantidad": 3}). Recalcula subtotal y total."""
    return await service.update(detalle_id, detalle_in)


# ==========================================
# DELETE
# ==========================================
@router.delete("/{detalle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detalle(detalle_id: int, service: DetallePedidoServiceDep) -> None:
    """Elimina un detalle y recalcula el total del pedido."""
    await service.delete(detalle_id)