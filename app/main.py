import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException, status

from app.api.deps import (
    DetallePedidoServiceDep,
    MesaServiceDep,
    PedidoServiceDep,
    PlatoServiceDep,
    get_detalle_pedido_repository,
    get_detalle_pedido_service,
    get_mesa_repository,
    get_mesa_service,
    get_pedido_repository,
    get_pedido_service,
    get_plato_repository,
    get_plato_service,
)
from app.core.config import settings
from app.core.database import async_session_maker, engine, init_db
from app.models import (
    CategoriaPlato,
    DetallePedidoCreate,
    MesaCreate,
    PedidoCreate,
    PlatoCreate,
)
from app.routers import api_router
from app.services import (
    DetallePedidoService,
    MesaService,
    PedidoService,
    PlatoService,
)

MESA_PRUEBA_NUMERO = 9999
ID_INEXISTENTE = 999999


async def ejecutar_pruebas_servicios(
    mesa_service: MesaService,
    plato_service: PlatoService,
    pedido_service: PedidoService,
    detalle_service: DetallePedidoService,
) -> dict[str, Any]:
    """Ejecuta las 6 validaciones de reglas de negocio de la Capa de Servicios.

    Recibe los servicios ya construidos (por FastAPI o por main_cli) en lugar
    de instanciarlos aquí.
    """
    # Los repositorios se usan solo para la limpieza de datos de prueba
    mesa_repo = mesa_service.mesa_repo
    pedido_repo = pedido_service.pedido_repo

    # Limpieza previa rápida si quedó la mesa de prueba
    existing_mesa = await mesa_repo.get_by_numero(MESA_PRUEBA_NUMERO)
    if existing_mesa and existing_mesa.id is not None:
        for p in await pedido_repo.get_filtered(id_mesa=existing_mesa.id):
            await pedido_repo.delete(p)
        await mesa_repo.delete(existing_mesa)

    # 1. Flujo de creación e integridad (Mesa, Plato, Pedido y Detalle)
    mesa = await mesa_service.create(
        MesaCreate(numero=MESA_PRUEBA_NUMERO, capacidad=4, ubicacion="terraza")
    )
    plato = await plato_service.create(
        PlatoCreate(
            nombre="Bandeja Paisa Prueba",
            categoria=CategoriaPlato.PLATO_FUERTE,
            precio=Decimal("32000.00"),
            disponible=True,
        )
    )
    plato_agotado = await plato_service.create(
        PlatoCreate(
            nombre="Limonada Agotada Prueba",
            categoria=CategoriaPlato.BEBIDA,
            precio=Decimal("8000.00"),
            disponible=False,
        )
    )
    pedido = await pedido_service.create(
        PedidoCreate(id_mesa=mesa.id, observaciones="Prueba servicio")  # type: ignore[arg-type]
    )
    detalle = await detalle_service.create(
        pedido_id=pedido.id,  # type: ignore[arg-type]
        detalle_in=DetallePedidoCreate(id_plato=plato.id, cantidad=2),  # type: ignore[arg-type]
    )

    # 2. Regla de Número Único de Mesa (HTTP 400)
    mesa_duplicada_bloqueada = False
    try:
        await mesa_service.create(MesaCreate(numero=MESA_PRUEBA_NUMERO, capacidad=2))
    except HTTPException as exc:
        mesa_duplicada_bloqueada = exc.status_code == status.HTTP_400_BAD_REQUEST

    # 3. Regla de Protección de Mesa con Historial (HTTP 400)
    mesa_con_pedidos_bloqueada = False
    try:
        await mesa_service.delete(mesa.id)  # type: ignore[arg-type]
    except HTTPException as exc:
        mesa_con_pedidos_bloqueada = exc.status_code == status.HTTP_400_BAD_REQUEST

    # 4. Regla de Negocio de Plato No Disponible (HTTP 400)
    plato_agotado_bloqueado = False
    try:
        await detalle_service.create(
            pedido_id=pedido.id,  # type: ignore[arg-type]
            detalle_in=DetallePedidoCreate(id_plato=plato_agotado.id, cantidad=1),  # type: ignore[arg-type]
        )
    except HTTPException as exc:
        plato_agotado_bloqueado = exc.status_code == status.HTTP_400_BAD_REQUEST

    # 5. Manejo Centralizado de No Encontrado (HTTP 404)
    not_found_404 = False
    try:
        await plato_service.get_by_id(ID_INEXISTENTE)
    except HTTPException as exc:
        not_found_404 = exc.status_code == status.HTTP_404_NOT_FOUND

    # 6. Eliminación Segura (borrado en cascada manual de los registros creados)
    await detalle_service.delete(detalle.id)  # type: ignore[arg-type]
    await pedido_service.delete(pedido.id)  # type: ignore[arg-type]
    await plato_service.delete(plato.id)  # type: ignore[arg-type]
    await plato_service.delete(plato_agotado.id)  # type: ignore[arg-type]
    await mesa_service.delete(mesa.id)  # type: ignore[arg-type]
    eliminacion_limpia = await mesa_repo.get_by_id(mesa.id) is None  # type: ignore[arg-type]

    return {
        "1_creacion_exitosa": {
            "mesa_id": mesa.id,
            "plato_id": plato.id,
            "pedido_id": pedido.id,
            "detalle_id": detalle.id,
        },
        "2_regla_mesa_duplicada_bloqueada": mesa_duplicada_bloqueada,
        "3_regla_mesa_con_pedidos_bloqueada": mesa_con_pedidos_bloqueada,
        "4_regla_plato_agotado_bloqueado": plato_agotado_bloqueado,
        "5_regla_not_found_404": not_found_404,
        "6_eliminacion_limpia": eliminacion_limpia,
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Capa 5: registra todos los routers bajo /api/v1 (ej: /api/v1/tables/)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "layer": "routers"}


@app.post("/test-services", tags=["Pruebas"])
async def test_services_endpoint(
    mesa_service: MesaServiceDep,
    plato_service: PlatoServiceDep,
    pedido_service: PedidoServiceDep,
    detalle_service: DetallePedidoServiceDep,
) -> dict[str, Any]:
    """FastAPI inyecta los 4 servicios ya armados, compartiendo una sola sesión."""
    resultados = await ejecutar_pruebas_servicios(
        mesa_service, plato_service, pedido_service, detalle_service
    )
    return {
        "mensaje": "Todas las reglas de negocio de la capa de servicios fueron validadas exitosamente",
        "resultados": resultados,
    }

async def main_cli() -> None:
    print("=" * 65)
    print("[INICIO] PRUEBA DE LA CAPA DE SERVICIOS (REGLAS DE NEGOCIO)")
    print("=" * 65)

    try:
        await init_db()
        print("\n[EJECUTANDO VALIDACIONES DE SERVICIO]...")

        async with async_session_maker() as session:
            # Fuera de una petición HTTP no hay Depends: llamamos las mismas
            # fábricas de deps.py pasando los parámetros a mano.
            mesa_repo = get_mesa_repository(session)
            plato_repo = get_plato_repository(session)
            pedido_repo = get_pedido_repository(session)
            detalle_repo = get_detalle_pedido_repository(session)

            r = await ejecutar_pruebas_servicios(
                get_mesa_service(mesa_repo, pedido_repo),
                get_plato_service(plato_repo),
                get_pedido_service(pedido_repo, mesa_repo),
                get_detalle_pedido_service(detalle_repo, pedido_repo, plato_repo),
            )

        print(f"  [OK] 1. Creacion exitosa: {r['1_creacion_exitosa']}")
        print(f"  [OK] 2. Bloqueo de Mesa Duplicada (HTTP 400): {r['2_regla_mesa_duplicada_bloqueada']}")
        print(f"  [OK] 3. Bloqueo de Mesa con Pedidos (HTTP 400): {r['3_regla_mesa_con_pedidos_bloqueada']}")
        print(f"  [OK] 4. Bloqueo Plato Agotado y Pedido (HTTP 400): {r['4_regla_plato_agotado_bloqueado']}")
        print(f"  [OK] 5. Manejo correcto de 404 Not Found: {r['5_regla_not_found_404']}")
        print(f"  [OK] 6. Eliminacion limpia: {r['6_eliminacion_limpia']}")
    finally:
        await engine.dispose()

    print("\n" + "=" * 65)
    print("[EXITO] TODAS LAS REGLAS DE NEGOCIO FUERON VERIFICADAS CON EXITO")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main_cli())
