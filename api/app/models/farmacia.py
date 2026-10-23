"""Tabela de farmácias (cada cliente do sistema)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Farmacia(Base):
    __tablename__ = "farmacias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150))
    # Desativar em vez de apagar: preserva o histórico de coletas
    ativa: Mapped[bool] = mapped_column(default=True, server_default=true())
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )