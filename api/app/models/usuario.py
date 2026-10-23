"""Tabela de usuários (funcionários das farmácias)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Perfil(StrEnum):
    OPERADOR = "operador"
    GERENTE = "gerente"


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("perfil IN ('operador', 'gerente')", name="perfil_valido"),
        CheckConstraint("email = lower(email)", name="email_minusculo"),
        # Permite que lotes_validade aponte para (farmacia_id, id):
        # garante que o coletor é da MESMA farmácia da coleta
        UniqueConstraint("farmacia_id", "id", name="uq_usuarios_farmacia_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    farmacia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farmacias.id"))

    # LGPD: só o necessário para identificar quem coletou e para o login
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))  # argon2; nunca a senha

    perfil: Mapped[str] = mapped_column(String(20))
    # Desativar em vez de apagar: as coletas continuam rastreáveis
    ativo: Mapped[bool] = mapped_column(default=True, server_default=true())
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )