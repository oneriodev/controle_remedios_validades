"""Dependências compartilhadas entre as rotas: quem está logado e o que pode fazer."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import TipoToken, TokenInvalido, decodificar_token
from app.models import Perfil, Usuario
from app.repositories import usuario_repository

# Lê o cabeçalho "Authorization: Bearer <token>" e ativa o botão Authorize do Swagger
esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def obter_usuario_atual(
    token: Annotated[str, Depends(esquema_oauth2)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Usuario:
    """Valida o access token e carrega o usuário DO BANCO (perfil sempre atualizado)."""
    nao_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado ou sessão expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        usuario_id = decodificar_token(token, TipoToken.ACCESS)
    except TokenInvalido:
        raise nao_autenticado

    # Usuário desativado (ou farmácia desativada) perde o acesso na hora
    usuario = await usuario_repository.buscar_ativo_por_id(session, usuario_id)
    if usuario is None:
        raise nao_autenticado
    return usuario


async def obter_farmacia_id(
    usuario: Annotated[Usuario, Depends(obter_usuario_atual)],
) -> uuid.UUID:
    """A farmácia vem do usuário logado, nunca de algo que o cliente envia."""
    return usuario.farmacia_id


async def exigir_gerente(
    usuario: Annotated[Usuario, Depends(obter_usuario_atual)],
) -> Usuario:
    if usuario.perfil != Perfil.GERENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida apenas ao gerente",
        )
    return usuario