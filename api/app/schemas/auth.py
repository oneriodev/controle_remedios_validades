"""Schemas de autenticação."""

import uuid

from pydantic import BaseModel, ConfigDict


class TokenResposta(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expira_em_segundos: int


class RenovacaoRequisicao(BaseModel):
    refresh_token: str


class UsuarioLeitura(BaseModel):
    """Dados do usuário logado. O hash da senha NUNCA é exposto."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: str
    perfil: str
    farmacia_id: uuid.UUID