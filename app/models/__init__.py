"""Modelos de RestAdmin API.

Importar todo aquí garantiza que SQLModel.metadata registre las tablas
antes de llamar a SQLModel.metadata.create_all(engine).
"""

from app.models.detalle_pedido import (
    DetallePedido,
    DetallePedidoBase,
    DetallePedidoCreate,
    DetallePedidoPublic,
    DetallePedidoUpdate,
)
from app.models.mesa import (
    EstadoMesa,
    Mesa,
    MesaBase,
    MesaCreate,
    MesaPublic,
    MesaUpdate,
)
from app.models.pedido import (
    EstadoPedido,
    Pedido,
    PedidoBase,
    PedidoConDetallesPublic,
    PedidoCreate,
    PedidoPublic,
    PedidoUpdate,
)
from app.models.plato import (
    CategoriaPlato,
    Plato,
    PlatoBase,
    PlatoCreate,
    PlatoPublic,
    PlatoUpdate,
)

__all__ = [
    # Mesa
    "EstadoMesa", "Mesa", "MesaBase", "MesaCreate", "MesaUpdate", "MesaPublic",
    # Plato
    "CategoriaPlato", "Plato", "PlatoBase", "PlatoCreate", "PlatoUpdate", "PlatoPublic",
    # Pedido
    "EstadoPedido", "Pedido", "PedidoBase", "PedidoCreate", "PedidoUpdate", "PedidoPublic",
    "PedidoConDetallesPublic",
    # DetallePedido
    "DetallePedido", "DetallePedidoBase", "DetallePedidoCreate",
    "DetallePedidoUpdate", "DetallePedidoPublic",
]
