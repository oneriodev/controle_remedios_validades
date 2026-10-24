"""Regras de negócio do registro de coletas."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import LoteValidade
from app.repositories import lote_validade_repository, produto_repository
from app.schemas.lote_validade import LoteValidadeCriar, LoteValidadeLeitura
from app.services.regras_validade import (
    calcular_faixa_risco,
    dias_para_vencer,
    hoje_no_fuso,
)


class ProdutoNaoEncontrado(Exception):
    """O EAN não está no cadastro desta farmácia."""


class ConflitoIdempotencia(Exception):
    """O id da coleta já existe com dados diferentes."""


_CAMPOS_COMPARADOS = (
    "farmacia_id",
    "ean_produto",
    "lote",
    "data_validade",
    "quantidade_prateleira",
)


async def registrar_coleta(
    session: AsyncSession,
    farmacia_id: uuid.UUID,
    usuario_id: uuid.UUID,
    dados: LoteValidadeCriar,
) -> tuple[LoteValidade, bool]:
    """Grava a coleta de forma idempotente. Retorna (coleta, foi_criada_agora)."""
    produto = await produto_repository.buscar_por_ean(
        session, farmacia_id, dados.ean_produto
    )
    if produto is None:
        raise ProdutoNaoEncontrado

    valores = {
        "id": dados.id,
        "farmacia_id": farmacia_id,
        "ean_produto": dados.ean_produto,
        "lote": dados.lote,
        "data_validade": dados.validade,
        "quantidade_prateleira": dados.quantidade_prateleira,
        "data_coleta": dados.data_coleta,
        "coletado_por_id": usuario_id,
    }

    criada = await lote_validade_repository.inserir_se_novo(session, valores)
    await session.commit()

    coleta = await lote_validade_repository.buscar_por_id(session, dados.id)
    if coleta is None:  # não deveria acontecer; protege contra inconsistência
        raise ConflitoIdempotencia

    if not criada:
        # Reenvio: só é aceito se for exatamente a mesma coleta
        mesma = all(
            getattr(coleta, campo) == valores[campo] for campo in _CAMPOS_COMPARADOS
        )
        if not mesma:
            raise ConflitoIdempotencia

    return coleta, criada


def para_leitura(coleta: LoteValidade) -> LoteValidadeLeitura:
    """Monta a resposta, calculando a faixa de risco para HOJE."""
    hoje = hoje_no_fuso(get_settings().fuso_horario)
    return LoteValidadeLeitura(
        id=coleta.id,
        ean_produto=coleta.ean_produto,
        lote=coleta.lote,
        data_validade=coleta.data_validade,
        quantidade_prateleira=coleta.quantidade_prateleira,
        data_coleta=coleta.data_coleta,
        recebido_em=coleta.recebido_em,
        situacao=coleta.situacao,
        dias_para_vencer=dias_para_vencer(coleta.data_validade, hoje),
        faixa_risco=calcular_faixa_risco(coleta.data_validade, hoje),
    )
