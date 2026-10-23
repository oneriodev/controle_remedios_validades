"""Acesso ao banco: produtos (sempre filtrando pela farmácia)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Produto

TAMANHO_BLOCO = 1000


async def buscar_por_ean(
    session: AsyncSession, farmacia_id: uuid.UUID, ean: str
) -> Produto | None:
    # Chave composta: a ordem é a mesma das colunas da PK (farmacia_id, ean)
    return await session.get(Produto, (farmacia_id, ean))


async def contar_existentes(
    session: AsyncSession, farmacia_id: uuid.UUID, eans: Sequence[str]
) -> int:
    """Quantos destes EANs já estão cadastrados nesta farmácia."""
    total = 0
    for inicio in range(0, len(eans), TAMANHO_BLOCO):
        bloco = eans[inicio : inicio + TAMANHO_BLOCO]
        consulta = (
            select(func.count())
            .select_from(Produto)
            .where(Produto.farmacia_id == farmacia_id, Produto.ean.in_(bloco))
        )
        total += (await session.execute(consulta)).scalar_one()
    return total


async def inserir_ou_atualizar(
    session: AsyncSession, registros: Sequence[dict[str, Any]]
) -> None:
    """Upsert: insere produtos novos e atualiza os já existentes."""
    for inicio in range(0, len(registros), TAMANHO_BLOCO):
        bloco = registros[inicio : inicio + TAMANHO_BLOCO]
        comando = insert(Produto).values(list(bloco))
        comando = comando.on_conflict_do_update(
            index_elements=[Produto.farmacia_id, Produto.ean],
            set_={
                "nome_medicamento": comando.excluded.nome_medicamento,
                "laboratorio": comando.excluded.laboratorio,
                "custo_unitario": comando.excluded.custo_unitario,
                "atualizado_em": func.now(),
            },
        )
        await session.execute(comando)