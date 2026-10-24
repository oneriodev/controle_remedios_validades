"""Tabela de produtos (cadastro base importado por CSV/XLSX)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Produto(Base):
    __tablename__ = "produtos"
    __table_args__ = (
        # EAN-8, EAN-13 ou GTIN-14: somente dígitos
        CheckConstraint("ean ~ '^[0-9]{8,14}$'", name="ean_somente_digitos"),
        CheckConstraint("custo_unitario >= 0", name="custo_nao_negativo"),
    )

    # Chave composta: o mesmo EAN pode existir uma vez em cada farmácia
    farmacia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farmacias.id"), primary_key=True
    )
    ean: Mapped[str] = mapped_column(String(14), primary_key=True)

    nome_medicamento: Mapped[str] = mapped_column(String(200))
    laboratorio: Mapped[str | None] = mapped_column(String(120))
    # Numeric (exato) em vez de float: é dinheiro
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
