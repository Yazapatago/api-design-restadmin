"""Capa de Acceso a Datos (Repositorios) de RestAdmin API.

Única capa que habla directamente con la base de datos.
"""

from app.repositories.base import BaseRepository
from app.repositories.detalle_pedido import DetallePedidoRepository
from app.repositories.mesa import MesaRepository
from app.repositories.pedido import PedidoRepository
from app.repositories.plato import PlatoRepository

__all__ = [
    "BaseRepository",
    "MesaRepository",
    "PlatoRepository",
    "PedidoRepository",
    "DetallePedidoRepository",
]
