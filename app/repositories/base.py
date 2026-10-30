from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

# ==========================================
# Variables de tipo genéricas
# ==========================================
ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Repositorio genérico con las operaciones CRUD estándar para cualquier modelo SQLModel.

    Reglas de la capa de acceso a datos:
    - Recibe la AsyncSession por el constructor (no crea su propia conexión).
    - No conoce HTTP: nunca lanza HTTPException; si no encuentra algo retorna None o [].
    - Retorna modelos de tabla (Mesa, Plato...), nunca DTOs *Public.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    # ==========================================
    # OPERACIONES DE LECTURA (READ)
    # ==========================================

    async def get_by_id(self, record_id: int) -> ModelType | None:
        """Busca un registro por su clave primaria. Retorna None si no existe."""
        return await self.session.get(self.model, record_id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Obtiene una lista paginada de registros ordenada por ID."""
        statement = (
            select(self.model)
            .order_by(self.model.id)  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    # ==========================================
    # OPERACIÓN DE CREACIÓN (CREATE)
    # ==========================================

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Inserta un nuevo registro a partir del DTO de creación y retorna la entidad creada."""
        db_obj = self.model.model_validate(obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    # ==========================================
    # OPERACIÓN DE ACTUALIZACIÓN (UPDATE)
    # ==========================================

    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Actualiza parcialmente un registro existente.

        exclude_unset=True: solo se modifican los campos que el cliente envió,
        así los campos omitidos no se sobrescriben con None.
        """
        update_data: dict[str, Any] = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Todos los modelos de RestAdmin tienen marca de última modificación.
        if hasattr(db_obj, "updated_at"):
            db_obj.updated_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]

        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    # ==========================================
    # OPERACIÓN DE ELIMINACIÓN (DELETE)
    # ==========================================

    async def delete(self, db_obj: ModelType) -> None:
        """Elimina físicamente el registro de la base de datos."""
        await self.session.delete(db_obj)
        await self.session.commit()
