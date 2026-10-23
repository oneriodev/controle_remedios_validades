"""Acesso ao banco: farmácias."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Farmacia


async def buscar_ativa(session: AsyncSession, farmacia_id: uuid.UUID) -> Farmacia | None:
    farmacia = await session.get(Farmacia, farmacia_id)
    if farmacia is None or not farmacia.ativa:
        return None
    return farmacia