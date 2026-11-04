import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker, engine, get_session, init_db
from app.models import (
    CategoriaPlato,
    DetallePedidoCreate,
    DetallePedidoUpdate,
    EstadoMesa,
    EstadoPedido,
    MesaCreate,
    MesaUpdate,
    PedidoCreate,
    PedidoUpdate,
    PlatoCreate,
    PlatoUpdate,
)
from app.repositories import (
    DetallePedidoRepository,
    MesaRepository,
    PedidoRepository,
    PlatoRepository,
)

# Datos reservados para las pruebas: la limpieza previa borra lo que coincida con
# ellos, por eso no deben parecerse a datos reales del restaurante.
MESA_PRUEBA_NUMERO = 9999
PREFIJO_PLATO_PRUEBA = "PRUEBA REPO"

class PruebaRepositorioError(Exception):
    """Un repositorio respondió algo distinto a lo esperado durante la prueba."""

def verificar(condicion: bool, descripcion: str) -> None:
    """Detiene la prueba si el resultado de un repositorio no es el esperado."""
    if not condicion:
        raise PruebaRepositorioError(f"Verificacion fallida: {descripcion}")

async def ejecutar_pruebas_repositorios(session: AsyncSession) -> dict[str, Any]:
    """
    Prueba integral de la Capa 3 (Repositorios):
    Ejecuta operaciones CRUD (Create, Read, Update, Delete) sobre MesaRepository,
    PlatoRepository, PedidoRepository y DetallePedidoRepository usando únicamente
    AsyncSession. Al terminar elimina todos los registros que creó.
    """
    mesa_repo = MesaRepository(session)
    plato_repo = PlatoRepository(session)
    pedido_repo = PedidoRepository(session)
    detalle_repo = DetallePedidoRepository(session)

    # Limpieza previa por si una ejecución anterior falló a mitad de camino.
    # Orden obligatorio por las FK RESTRICT: pedidos (y sus detalles) -> mesa -> platos.
    existing_mesa = await mesa_repo.get_by_numero(MESA_PRUEBA_NUMERO)
    if existing_mesa and existing_mesa.id is not None:
        old_pedidos = await pedido_repo.get_filtered(id_mesa=existing_mesa.id)
        for pedido_viejo in old_pedidos:
            await pedido_repo.delete(pedido_viejo)
        await mesa_repo.delete(existing_mesa)

    old_platos = await plato_repo.get_filtered(search=PREFIJO_PLATO_PRUEBA)
    for plato_viejo in old_platos:
        await plato_repo.delete(plato_viejo)

    # =========================================================================
    # 1. CREATE (Inserción en Base de Datos mediante Repositorios)
    # =========================================================================
    nueva_mesa = await mesa_repo.create(
        MesaCreate(
            numero=MESA_PRUEBA_NUMERO,
            capacidad=4,
            ubicacion="terraza",
        )
    )

    plato_1 = await plato_repo.create(
        PlatoCreate(
            nombre=f"{PREFIJO_PLATO_PRUEBA} Bandeja paisa",
            descripcion="Frijoles, arroz, chicharrón y carne molida",
            categoria=CategoriaPlato.PLATO_FUERTE,
            precio=Decimal("32000.00"),
        )
    )

    plato_2 = await plato_repo.create(
        PlatoCreate(
            nombre=f"{PREFIJO_PLATO_PRUEBA} Limonada de coco",
            categoria=CategoriaPlato.BEBIDA,
            precio=Decimal("8000.00"),
        )
    )

    nuevo_pedido = await pedido_repo.create(
        PedidoCreate(
            id_mesa=nueva_mesa.id,  # type: ignore[arg-type]
            observaciones="Cliente con prisa",
        )
    )

    # El precio_unitario se copia del precio actual del plato (precio del momento).
    detalle_1 = await detalle_repo.create_for_pedido(
        pedido_id=nuevo_pedido.id,  # type: ignore[arg-type]
        detalle_in=DetallePedidoCreate(
            id_plato=plato_1.id,  # type: ignore[arg-type]
            cantidad=2,
            notas="sin cebolla",
        ),
        precio_unitario=plato_1.precio,
    )

    detalle_2 = await detalle_repo.create_for_pedido(
        pedido_id=nuevo_pedido.id,  # type: ignore[arg-type]
        detalle_in=DetallePedidoCreate(
            id_plato=plato_2.id,  # type: ignore[arg-type]
            cantidad=1,
        ),
        precio_unitario=plato_2.precio,
    )

    nuevo_pedido = await pedido_repo.update_total(nuevo_pedido)

    # Se guardan ahora porque la sección DELETE elimina los registros.
    mesa_id = nueva_mesa.id
    plato_1_id = plato_1.id
    plato_2_id = plato_2.id
    pedido_id = nuevo_pedido.id
    detalle_1_id = detalle_1.id
    detalle_2_id = detalle_2.id

    verificar(detalle_1.subtotal == Decimal("64000.00"), "subtotal del detalle 1 = 2 x 32000")
    verificar(nuevo_pedido.total == Decimal("72000.00"), "total del pedido = 64000 + 8000")

    datos_creacion = {
        "mesa_id": mesa_id,
        "platos_creados": [plato_1.nombre, plato_2.nombre],
        "pedido_id": pedido_id,
        "detalles_creados": [detalle_1_id, detalle_2_id],
        "pedido_total": nuevo_pedido.total,
    }

    # =========================================================================
    # 2. READ (Consultas por ID, por campos únicos y listados con filtros)
    # =========================================================================
    mesa_por_id = await mesa_repo.get_by_id(mesa_id)  # type: ignore[arg-type]
    mesa_por_numero = await mesa_repo.get_by_numero(MESA_PRUEBA_NUMERO)
    mesas_paginadas = await mesa_repo.get_multi(skip=0, limit=1)
    mesas_filtradas = await mesa_repo.get_filtered(
        estado=EstadoMesa.LIBRE,
        capacidad_minima=4,
    )

    # La búsqueda en minúsculas comprueba que el filtro no distingue mayúsculas.
    platos_filtrados = await plato_repo.get_filtered(
        search=PREFIJO_PLATO_PRUEBA.lower(),
        categoria=CategoriaPlato.PLATO_FUERTE,
        solo_disponibles=True,
        precio_min=Decimal("30000"),
        precio_max=Decimal("40000"),
    )

    pedidos_filtrados = await pedido_repo.get_filtered(
        id_mesa=mesa_id,
        estado=EstadoPedido.PENDIENTE,
    )
    pedido_con_detalles = await pedido_repo.get_with_detalles(pedido_id)  # type: ignore[arg-type]

    detalles_del_pedido = await detalle_repo.get_by_pedido(pedido_id)  # type: ignore[arg-type]
    detalle_en_su_pedido = await detalle_repo.get_by_id_and_pedido(
        detalle_1_id,  # type: ignore[arg-type]
        pedido_id,  # type: ignore[arg-type]
    )
    detalle_en_otro_pedido = await detalle_repo.get_by_id_and_pedido(
        detalle_1_id,  # type: ignore[arg-type]
        pedido_id + 1,  # type: ignore[operator]
    )

    verificar(mesa_por_id is not None, "get_by_id encuentra la mesa")
    verificar(mesa_por_numero is not None, "get_by_numero encuentra la mesa")
    verificar(len(mesas_paginadas) == 1, "get_multi respeta limit=1")
    verificar(
        any(mesa.id == mesa_id for mesa in mesas_filtradas),
        "get_filtered de mesas incluye la mesa libre",
    )
    verificar(
        [plato.id for plato in platos_filtrados] == [plato_1_id],
        "get_filtered de platos retorna solo el plato fuerte en el rango de precio",
    )
    verificar(
        [pedido.id for pedido in pedidos_filtrados] == [pedido_id],
        "get_filtered de pedidos retorna el pedido pendiente de la mesa",
    )
    verificar(
        pedido_con_detalles is not None and len(pedido_con_detalles.detalles) == 2,
        "get_with_detalles carga las 2 lineas del pedido",
    )
    verificar(len(detalles_del_pedido) == 2, "get_by_pedido retorna las 2 lineas")
    verificar(detalle_en_su_pedido is not None, "get_by_id_and_pedido encuentra el detalle")
    verificar(detalle_en_otro_pedido is None, "get_by_id_and_pedido no cruza pedidos")

    datos_lectura = {
        "mesa_por_id": mesa_por_id.numero if mesa_por_id else None,
        "mesa_por_numero": mesa_por_numero.ubicacion if mesa_por_numero else None,
        "mesas_paginadas_limit_1": len(mesas_paginadas),
        "mesas_filtradas_count": len(mesas_filtradas),
        "platos_filtrados": [plato.nombre for plato in platos_filtrados],
        "pedidos_filtrados_count": len(pedidos_filtrados),
        "pedido_con_detalles_count": (
            len(pedido_con_detalles.detalles) if pedido_con_detalles else None
        ),
        "detalles_del_pedido_count": len(detalles_del_pedido),
        "detalle_en_otro_pedido": detalle_en_otro_pedido,
    }

    # =========================================================================
    # 3. UPDATE (Actualización parcial con exclude_unset=True)
    # =========================================================================
    mesa_actualizada = await mesa_repo.update(
        nueva_mesa,
        MesaUpdate(estado=EstadoMesa.OCUPADA),
    )

    plato_actualizado = await plato_repo.update(
        plato_1,
        PlatoUpdate(precio=Decimal("34000.00"), disponible=False),
    )

    pedido_actualizado = await pedido_repo.update(
        nuevo_pedido,
        PedidoUpdate(estado=EstadoPedido.EN_PREPARACION),
    )

    # Cambiar la cantidad recalcula el subtotal con el precio del momento (32000),
    # aunque el precio del plato ya haya cambiado a 34000 en el menú.
    detalle_actualizado = await detalle_repo.update(
        detalle_1,
        DetallePedidoUpdate(cantidad=3),
    )
    pedido_actualizado = await pedido_repo.update_total(pedido_actualizado)

    verificar(mesa_actualizada.capacidad == 4, "update de mesa no toca los campos omitidos")
    verificar(
        detalle_actualizado.precio_unitario == Decimal("32000.00"),
        "el detalle conserva el precio del momento",
    )
    verificar(detalle_actualizado.subtotal == Decimal("96000.00"), "subtotal = 3 x 32000")
    verificar(pedido_actualizado.total == Decimal("104000.00"), "total = 96000 + 8000")

    datos_actualizacion = {
        "mesa_nuevo_estado": mesa_actualizada.estado,
        "plato_nuevo_precio": plato_actualizado.precio,
        "plato_disponible": plato_actualizado.disponible,
        "pedido_nuevo_estado": pedido_actualizado.estado,
        "detalle_nueva_cantidad": detalle_actualizado.cantidad,
        "detalle_precio_del_momento": detalle_actualizado.precio_unitario,
        "detalle_nuevo_subtotal": detalle_actualizado.subtotal,
        "pedido_nuevo_total": pedido_actualizado.total,
    }

    # =========================================================================
    # 4. DELETE (Eliminación física y verificación de retorno None)
    # =========================================================================
    await detalle_repo.delete(detalle_2)
    detalle_eliminado_check = await detalle_repo.get_by_id(detalle_2_id)  # type: ignore[arg-type]

    # Se vuelve a consultar el pedido: su lista de detalles ya estaba cargada en esta
    # sesión y aún contiene el detalle eliminado, lo que haría fallar a update_total.
    pedido_a_eliminar = await pedido_repo.get_with_detalles(pedido_id)  # type: ignore[arg-type]
    verificar(
        pedido_a_eliminar is not None and len(pedido_a_eliminar.detalles) == 1,
        "al pedido le queda 1 linea tras eliminar un detalle",
    )
    pedido_a_eliminar = await pedido_repo.update_total(pedido_a_eliminar)  # type: ignore[arg-type]
    total_tras_quitar_detalle = pedido_a_eliminar.total

    await pedido_repo.delete(pedido_a_eliminar)
    pedido_eliminado_check = await pedido_repo.get_by_id(pedido_id)  # type: ignore[arg-type]
    detalles_tras_cascade = await detalle_repo.get_by_pedido(pedido_id)  # type: ignore[arg-type]

    await plato_repo.delete(plato_1)
    await plato_repo.delete(plato_2)
    plato_1_eliminado_check = await plato_repo.get_by_id(plato_1_id)  # type: ignore[arg-type]
    plato_2_eliminado_check = await plato_repo.get_by_id(plato_2_id)  # type: ignore[arg-type]

    await mesa_repo.delete(nueva_mesa)
    mesa_eliminada_check = await mesa_repo.get_by_id(mesa_id)  # type: ignore[arg-type]

    verificar(detalle_eliminado_check is None, "el detalle eliminado ya no existe")
    verificar(total_tras_quitar_detalle == Decimal("96000.00"), "total sin el detalle eliminado")
    verificar(pedido_eliminado_check is None, "el pedido eliminado ya no existe")
    verificar(detalles_tras_cascade == [], "el cascade elimina los detalles del pedido")
    verificar(
        plato_1_eliminado_check is None and plato_2_eliminado_check is None,
        "los platos eliminados ya no existen",
    )
    verificar(mesa_eliminada_check is None, "la mesa eliminada ya no existe")

    return {
        "1_create": datos_creacion,
        "2_read": datos_lectura,
        "3_update": datos_actualizacion,
        "4_delete": {
            "detalle_eliminado_id": detalle_2_id,
            "get_by_id_detalle_tras_eliminar": detalle_eliminado_check,
            "pedido_total_tras_quitar_detalle": total_tras_quitar_detalle,
            "pedido_eliminado_id": pedido_id,
            "get_by_id_pedido_tras_eliminar": pedido_eliminado_check,
            "detalles_tras_cascade": len(detalles_tras_cascade),
            "platos_eliminados_ids": [plato_1_id, plato_2_id],
            "mesa_eliminada_id": mesa_id,
            "get_by_id_mesa_tras_eliminar": mesa_eliminada_check,
        },
    }

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Ciclo de vida de la aplicación: crea las tablas de la BD al arrancar."""
    await init_db()
    yield

app = FastAPI(
    title=f"{settings.PROJECT_NAME} - Hasta Capa Repositorio",
    version=settings.VERSION,
    description=(
        "Proyecto con Capas 1 (Core), 2 (Modelos/DTOs) y 3 (Repositorios). "
        "Sin servicios ni routers externos."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Endpoint para comprobación del estado del servicio."""
    return {"status": "healthy", "layer": "repository"}

@app.post("/test-repositories", tags=["Pruebas Capa Repositorio"])
async def test_repositories_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """
    Ejecuta desde Swagger UI (`/docs`) una prueba completa de CRUD sobre
    `MesaRepository`, `PlatoRepository`, `PedidoRepository` y
    `DetallePedidoRepository`.
    """
    try:
        resultados = await ejecutar_pruebas_repositorios(session)
    except PruebaRepositorioError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "mensaje": "Prueba de la capa de repositorios completada exitosamente",
        "resultados": resultados,
    }

async def main_cli() -> None:
    """Función para probar los repositorios directamente desde la consola."""
    print("=" * 65)
    print("[INICIO] PRUEBA DE LA CAPA DE REPOSITORIOS (CRUD ASINCRONO)")
    print("=" * 65)

    try:
        await init_db()
        print("[OK] 1. Base de datos y tablas inicializadas (init_db).")

        async with async_session_maker() as session:
            resultados = await ejecutar_pruebas_repositorios(session)

        creacion = resultados["1_create"]
        print("\n[CREATE] 2. Insercion de registros:")
        print(f"   - Mesa creada ID: {creacion['mesa_id']}")
        print(f"   - Platos creados: {creacion['platos_creados']}")
        print(f"   - Pedido creado ID: {creacion['pedido_id']}")
        print(f"   - Detalles creados IDs: {creacion['detalles_creados']}")
        print(f"   - Total calculado del pedido: ${creacion['pedido_total']}")

        lectura = resultados["2_read"]
        print("\n[READ] 3. Consultas y filtros:")
        print(f"   - Mesa por ID (numero): {lectura['mesa_por_id']}")
        print(f"   - Mesa por Numero (ubicacion): {lectura['mesa_por_numero']}")
        print(f"   - Mesas paginadas (limit=1): {lectura['mesas_paginadas_limit_1']}")
        print(f"   - Mesas filtradas (estado + capacidad): {lectura['mesas_filtradas_count']}")
        print(f"   - Platos filtrados (nombre + categoria + precio): {lectura['platos_filtrados']}")
        print(f"   - Pedidos filtrados (id_mesa + estado): {lectura['pedidos_filtrados_count']}")
        print(f"   - Pedido con detalles (selectinload): {lectura['pedido_con_detalles_count']}")
        print(f"   - Detalles del pedido: {lectura['detalles_del_pedido_count']}")
        print(f"   - Detalle en otro pedido (debe ser None): {lectura['detalle_en_otro_pedido']}")

        actualizacion = resultados["3_update"]
        print("\n[UPDATE] 4. Actualizacion parcial:")
        print(f"   - Mesa actualizada -> Estado: {actualizacion['mesa_nuevo_estado']}")
        print(
            f"   - Plato actualizado -> Precio: ${actualizacion['plato_nuevo_precio']} "
            f"| Disponible: {actualizacion['plato_disponible']}"
        )
        print(f"   - Pedido actualizado -> Estado: {actualizacion['pedido_nuevo_estado']}")
        print(
            f"   - Detalle actualizado -> Cantidad: {actualizacion['detalle_nueva_cantidad']} "
            f"| Precio del momento: ${actualizacion['detalle_precio_del_momento']} "
            f"| Subtotal: ${actualizacion['detalle_nuevo_subtotal']}"
        )
        print(f"   - Total recalculado del pedido: ${actualizacion['pedido_nuevo_total']}")

        eliminacion = resultados["4_delete"]
        print("\n[DELETE] 5. Eliminacion fisica:")
        print(f"   - ID Detalle eliminado: {eliminacion['detalle_eliminado_id']}")
        print(
            f"   - Busqueda tras eliminar (debe ser None): "
            f"{eliminacion['get_by_id_detalle_tras_eliminar']}"
        )
        print(f"   - Total tras quitar el detalle: ${eliminacion['pedido_total_tras_quitar_detalle']}")
        print(f"   - ID Pedido eliminado: {eliminacion['pedido_eliminado_id']}")
        print(
            f"   - Busqueda tras eliminar (debe ser None): "
            f"{eliminacion['get_by_id_pedido_tras_eliminar']}"
        )
        print(f"   - Detalles tras el cascade (debe ser 0): {eliminacion['detalles_tras_cascade']}")
        print(f"   - IDs Platos eliminados: {eliminacion['platos_eliminados_ids']}")
        print(f"   - ID Mesa eliminada: {eliminacion['mesa_eliminada_id']}")
        print(
            f"   - Busqueda tras eliminar (debe ser None): "
            f"{eliminacion['get_by_id_mesa_tras_eliminar']}"
        )
    finally:
        await engine.dispose()

    print("\n" + "=" * 65)
    print("[EXITO] TODAS LAS PRUEBAS DE REPOSITORIO PASARON CORRECTAMENTE")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main_cli())