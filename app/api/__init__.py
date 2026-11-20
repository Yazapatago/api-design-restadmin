"""Paquete de la API: dependencias compartidas por los routers."""

from app.api.deps import (
    DetallePedidoRepoDep,
    DetallePedidoServiceDep,
    MesaRepoDep,
    MesaServiceDep,
    PedidoRepoDep,
    PedidoServiceDep,
    PlatoRepoDep,
    PlatoServiceDep,
    SessionDep,
)

__all__ = [
    "SessionDep",
    "MesaRepoDep",
    "PlatoRepoDep",
    "PedidoRepoDep",
    "DetallePedidoRepoDep",
    "MesaServiceDep",
    "PlatoServiceDep",
    "PedidoServiceDep",
    "DetallePedidoServiceDep",
]