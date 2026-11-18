"""Capa de Routers (Controladores HTTP) de RestAdmin API.

Puerta de entrada HTTP: recibe peticiones, delega en los servicios y
devuelve respuestas con el response_model y status_code adecuados.

api_router agrupa todos los routers para registrarlos en main.py
con una sola línea.
"""

from fastapi import APIRouter

from app.routers import detalles_pedido, mesas, pedidos, platos

api_router = APIRouter()
api_router.include_router(mesas.router)
api_router.include_router(platos.router)
api_router.include_router(pedidos.router)
api_router.include_router(detalles_pedido.router)

__all__ = ["api_router"]
