"""Sistema de Inyección de Dependencias de RestAdmin API.

Único lugar donde se instancian repositorios y servicios. Los routers solo
declaran qué servicio necesitan (ej: `service: MesaServiceDep`) y FastAPI
se encarga de construirlo en cada petición.

Cadena de construcción:
    get_session() -> AsyncSession -> Repositorios -> Servicio

FastAPI cachea las dependencias por petición: si un endpoint pide dos
servicios, ambos comparten la MISMA sesión de base de datos.
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
# Sesión de base de datos
# ==========================================
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ==========================================
# Fábricas de servicios (una por entidad)
# ==========================================
def get_mesa_service(session: SessionDep) -> MesaService:
    """Construye MesaService con sus repositorios (Mesa + Pedido)."""
    return MesaService(MesaRepository(session), PedidoRepository(session))


def get_plato_service(session: SessionDep) -> PlatoService:
    """Construye PlatoService con su repositorio."""
    return PlatoService(PlatoRepository(session))


def get_pedido_service(session: SessionDep) -> PedidoService:
    """Construye PedidoService con sus repositorios (Pedido + Mesa)."""
    return PedidoService(PedidoRepository(session), MesaRepository(session))


def get_detalle_pedido_service(session: SessionDep) -> DetallePedidoService:
    """Construye DetallePedidoService con sus repositorios (Detalle + Pedido + Plato)."""
    return DetallePedidoService(
        DetallePedidoRepository(session),
        PedidoRepository(session),
        PlatoRepository(session),
    )


# ==========================================
# Alias listos para usar en los routers
# ==========================================
MesaServiceDep = Annotated[MesaService, Depends(get_mesa_service)]
PlatoServiceDep = Annotated[PlatoService, Depends(get_plato_service)]
PedidoServiceDep = Annotated[PedidoService, Depends(get_pedido_service)]
DetallePedidoServiceDep = Annotated[
    DetallePedidoService, Depends(get_detalle_pedido_service)
]
