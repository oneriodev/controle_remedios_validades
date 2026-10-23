"""Acesso ao banco: produtos (sempre filtrando pela farmácia)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Produto


async def buscar_por_ean(
    session: AsyncSession, farmacia_id: uuid.UUID, ean: str
) -> Produto | None:
    # Chave composta: a ordem é a mesma das colunas da PK (farmacia_id, ean)
    return await session.get(Produto, (farmacia_id, ean))