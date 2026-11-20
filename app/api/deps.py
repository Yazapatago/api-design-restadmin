"""Sistema de Inyección de Dependencias de RestAdmin API.

Único lugar donde se instancian repositorios y servicios. Los routers solo
declaran qué servicio necesitan (ej: `service: MesaServiceDep`) y FastAPI
se encarga de construirlo en cada petición.

Cadena de construcción (3 niveles):
    get_session() -> AsyncSession -> Repositorios -> Servicios

FastAPI cachea las dependencias por petición: si un endpoint pide dos
servicios, ambos comparten la MISMA sesión y los MISMOS repositorios.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories import (
    DetallePedidoRepository,
    MesaRepository,
    PedidoRepository,
    PlatoRepository,
)
from app.services import (
    DetallePedidoService,
    MesaService,
    PedidoService,
    PlatoService,
)

# ==========================================
# Nivel 1: Sesión de base de datos (Capa 1 - Core)
# ==========================================
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ==========================================
# Nivel 2: Fábricas de repositorios (Capa 3)
# ==========================================
def get_mesa_repository(session: SessionDep) -> MesaRepository:
    """Construye MesaRepository con la sesión de la petición."""
    return MesaRepository(session)


def get_plato_repository(session: SessionDep) -> PlatoRepository:
    """Construye PlatoRepository con la sesión de la petición."""
    return PlatoRepository(session)


def get_pedido_repository(session: SessionDep) -> PedidoRepository:
    """Construye PedidoRepository con la sesión de la petición."""
    return PedidoRepository(session)


def get_detalle_pedido_repository(session: SessionDep) -> DetallePedidoRepository:
    """Construye DetallePedidoRepository con la sesión de la petición."""
    return DetallePedidoRepository(session)


MesaRepoDep = Annotated[MesaRepository, Depends(get_mesa_repository)]
PlatoRepoDep = Annotated[PlatoRepository, Depends(get_plato_repository)]
PedidoRepoDep = Annotated[PedidoRepository, Depends(get_pedido_repository)]
DetallePedidoRepoDep = Annotated[
    DetallePedidoRepository, Depends(get_detalle_pedido_repository)
]


# ==========================================
# Nivel 3: Fábricas de servicios (Capa 4)
# ==========================================
def get_mesa_service(
    mesa_repo: MesaRepoDep,
    pedido_repo: PedidoRepoDep,
) -> MesaService:
    """Construye MesaService (necesita Pedido para proteger el historial)."""
    return MesaService(mesa_repo=mesa_repo, pedido_repo=pedido_repo)


def get_plato_service(plato_repo: PlatoRepoDep) -> PlatoService:
    """Construye PlatoService con su repositorio."""
    return PlatoService(plato_repo=plato_repo)


def get_pedido_service(
    pedido_repo: PedidoRepoDep,
    mesa_repo: MesaRepoDep,
) -> PedidoService:
    """Construye PedidoService (necesita Mesa para validar que exista)."""
    return PedidoService(pedido_repo=pedido_repo, mesa_repo=mesa_repo)


def get_detalle_pedido_service(
    detalle_repo: DetallePedidoRepoDep,
    pedido_repo: PedidoRepoDep,
    plato_repo: PlatoRepoDep,
) -> DetallePedidoService:
    """Construye DetallePedidoService (necesita Pedido y Plato para validar)."""
    return DetallePedidoService(
        detalle_repo=detalle_repo,
        pedido_repo=pedido_repo,
        plato_repo=plato_repo,
    )


MesaServiceDep = Annotated[MesaService, Depends(get_mesa_service)]
PlatoServiceDep = Annotated[PlatoService, Depends(get_plato_service)]
PedidoServiceDep = Annotated[PedidoService, Depends(get_pedido_service)]
DetallePedidoServiceDep = Annotated[
    DetallePedidoService, Depends(get_detalle_pedido_service)
]