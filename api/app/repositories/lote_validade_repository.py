"""Acesso ao banco: coletas de lote/validade."""

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LoteValidade


async def inserir_se_novo(session: AsyncSession, valores: dict[str, Any]) -> bool:
    """Insere a coleta; se o id já existir, não faz nada.

    Retorna True se gravou agora, False se o id já existia.
    O ON CONFLICT é atômico: dois reenvios simultâneos não duplicam.
    """
    comando = (
        insert(LoteValidade)
        .values(**valores)
        .on_conflict_do_nothing(index_elements=[LoteValidade.id])
        .returning(LoteValidade.id)
    )
    resultado = await session.execute(comando)
    return resultado.scalar_one_or_none() is not None


async def buscar_por_id(
    session: AsyncSession, lote_id: uuid.UUID
) -> LoteValidade | None:
    return await session.get(LoteValidade, lote_id)
