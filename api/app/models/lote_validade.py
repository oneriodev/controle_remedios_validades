"""Tabela de coletas de lote/validade (alimentada pelo app mobile)."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoteValidade(Base):
    __tablename__ = "lotes_validade"
    __table_args__ = (
        # FK composta: a coleta só pode apontar para um produto DA MESMA farmácia
        ForeignKeyConstraint(
            ["farmacia_id", "ean_produto"],
            ["produtos.farmacia_id", "produtos.ean"],
            ondelete="RESTRICT",  # nunca apagar histórico de coletas em cascata
        ),
        CheckConstraint("quantidade_prateleira > 0", name="quantidade_positiva"),
        # Regra de negócio: a validade é sempre o último dia do mês impresso
        CheckConstraint(
            "data_validade = (date_trunc('month', data_validade)"
            " + interval '1 month - 1 day')::date",
            name="validade_ultimo_dia_mes",
        ),
        # Ciclo de vida do lote. A faixa de risco (vencido, 30/60/90 dias)
        # NÃO é gravada: é calculada na consulta a partir da data de hoje.
        CheckConstraint(
            "situacao IN ('ativo', 'descartado')", name="situacao_valida"
        ),
        # Acelera a consulta do painel: "o que vence nesta farmácia em breve?"
        Index("ix_lotes_validade_farmacia_validade", "farmacia_id", "data_validade"),
    )

    # Gerado no aparelho: é a chave de idempotência (sem valor padrão de propósito)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    farmacia_id: Mapped[uuid.UUID] = mapped_column()
    ean_produto: Mapped[str] = mapped_column(String(14))

    lote: Mapped[str] = mapped_column(String(50))
    data_validade: Mapped[date] = mapped_column(Date)
    quantidade_prateleira: Mapped[int] = mapped_column()

    # Horário informado pelo celular (pode estar com o relógio errado)
    data_coleta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Horário do servidor ao receber: este é o confiável para auditoria
    recebido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    situacao: Mapped[str] = mapped_column(
        String(20), default="ativo", server_default="ativo"
    )