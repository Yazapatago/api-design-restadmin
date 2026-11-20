from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.models.detalle_pedido import DetallePedido, DetallePedidoCreate
from app.models.pedido import EstadoPedido, Pedido, PedidoCreate, PedidoUpdate
from app.repositories.base import BaseRepository


class PedidoRepository(BaseRepository[Pedido, PedidoCreate, PedidoUpdate]):
    """Capa de Acceso a Datos para la entidad Pedido.

    Hereda get_by_id, get_multi, create, update y delete de BaseRepository.
    Al borrar un pedido se borran también sus detalles (cascade definido en el modelo).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Pedido, session)

    async def get_with_detalles(self, pedido_id: int) -> Pedido | None:
        """Busca un pedido junto con sus detalles. Retorna None si no existe.

        Con AsyncSession no se puede usar la carga perezosa (lazy load) de relaciones,
        por eso los detalles se cargan explícitamente con selectinload.
        populate_existing refresca la lista aunque el pedido ya esté en la sesión.
        """
        statement = (
            select(Pedido)
            .where(Pedido.id == pedido_id)
            .options(selectinload(Pedido.detalles))  # type: ignore[arg-type]
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_filtered(
        self,
        *,
        id_mesa: int | None = None,
        estado: EstadoPedido | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Pedido]:
        """Lista pedidos aplicando únicamente los filtros que se envíen.

        Se ordenan del más antiguo al más reciente (orden en que la cocina los atiende).
        """
        statement = select(Pedido)

        # Filtro 1: Pedidos de una mesa específica
        if id_mesa is not None:
            statement = statement.where(Pedido.id_mesa == id_mesa)

        # Filtro 2: Estado (pendiente, en_preparacion, entregado, pagado, cancelado)
        if estado is not None:
            statement = statement.where(Pedido.estado == estado)

        # Ordenamiento y paginación al final
        statement = (
            statement.order_by(Pedido.fecha_hora, Pedido.id).offset(skip).limit(limit)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_with_items(
        self,
        *,
        pedido_in: PedidoCreate,
        items: list[tuple[DetallePedidoCreate, Decimal]],
    ) -> Pedido:
        """Inserta el pedido y sus detalles en UNA sola transacción.

        items: lista de (detalle, precio_unitario). El precio lo decide el servicio
        (copiado del plato). Si algo falla no queda un pedido a medias en la BD.
        """
        db_pedido = Pedido.model_validate(pedido_in.model_dump(exclude={"items"}))

        for detalle_in, precio_unitario in items:
            # id_pedido lo llena el ORM al agregar el detalle a la relación
            db_pedido.detalles.append(
                DetallePedido.model_validate(
                    detalle_in,
                    update={
                        "precio_unitario": precio_unitario,
                        "subtotal": precio_unitario * detalle_in.cantidad,
                    },
                )
            )

        db_pedido.total = sum(
            (d.subtotal for d in db_pedido.detalles), start=Decimal("0.00")
        )
        self.session.add(db_pedido)
        await self.session.commit()
        await self.session.refresh(db_pedido)
        return db_pedido

    async def update_total(self, db_pedido: Pedido) -> Pedido:
        """Recalcula el total del pedido como la suma de los subtotales de sus detalles."""
        statement = select(
            func.coalesce(func.sum(DetallePedido.subtotal), 0)
        ).where(DetallePedido.id_pedido == db_pedido.id)
        result = await self.session.execute(statement)

        db_pedido.total = result.scalar_one()
        # La lista de detalles cargada en memoria puede estar desactualizada
        # (ej: incluir un detalle recién borrado). Se marca como vencida para que
        # el ORM no la use al guardar; get_with_detalles la vuelve a cargar.
        self.session.expire(db_pedido, ["detalles"])
        db_pedido.updated_at = datetime.now(timezone.utc)
        self.session.add(db_pedido)
        await self.session.commit()
        await self.session.refresh(db_pedido)
        return db_pedido