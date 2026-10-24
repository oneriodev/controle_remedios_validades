"""Acesso ao banco: usuários."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Farmacia, Usuario


def _ativos():
    """Usuário ativo E farmácia ativa."""
    return (
        select(Usuario)
        .join(Farmacia, Farmacia.id == Usuario.farmacia_id)
        .where(Usuario.ativo.is_(True), Farmacia.ativa.is_(True))
    )


async def buscar_ativo_por_email(session: AsyncSession, email: str) -> Usuario | None:
    resultado = await session.execute(_ativos().where(Usuario.email == email))
    return resultado.scalar_one_or_none()


async def buscar_ativo_por_id(
    session: AsyncSession, usuario_id: uuid.UUID
) -> Usuario | None:
    resultado = await session.execute(_ativos().where(Usuario.id == usuario_id))
    return resultado.scalar_one_or_none()


async def existe_email(session: AsyncSession, email: str) -> bool:
    """Inclui inativos: um e-mail desativado continua ocupado."""
    resultado = await session.execute(select(Usuario.id).where(Usuario.email == email))
    return resultado.first() is not None
