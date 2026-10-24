"""Rotas de autenticação."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import obter_usuario_atual
from app.core.security import TipoToken, TokenInvalido, decodificar_token
from app.models import Usuario
from app.repositories import usuario_repository
from app.schemas.auth import RenovacaoRequisicao, TokenResposta, UsuarioLeitura
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])

_CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="E-mail ou senha incorretos",  # mesma mensagem para os dois casos
    headers={"WWW-Authenticate": "Bearer"},
)


def _mascarar_email(email: str) -> str:
    """'onerio@exemplo.test' -> 'on***@exemplo.test' (LGPD nos logs)."""
    usuario, _, dominio = email.strip().lower().partition("@")
    return f"{usuario[:2]}***@{dominio}"


@router.post("/login", response_model=TokenResposta)
async def login(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResposta:
    # Pelo padrão OAuth2 o campo se chama "username"; aqui ele recebe o e-mail
    usuario = await auth_service.autenticar(
        session, formulario.username, formulario.password
    )
    if usuario is None:
        logger.warning("Falha de login: %s", _mascarar_email(formulario.username))
        raise _CREDENCIAIS_INVALIDAS

    logger.info("Login: usuario=%s farmacia=%s", usuario.id, usuario.farmacia_id)
    return auth_service.emitir_tokens(usuario)


@router.post("/refresh", response_model=TokenResposta)
async def renovar(
    dados: RenovacaoRequisicao,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResposta:
    sessao_expirada = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão expirada; faça login novamente",
    )
    try:
        usuario_id = decodificar_token(dados.refresh_token, TipoToken.REFRESH)
    except TokenInvalido:
        raise sessao_expirada

    usuario = await usuario_repository.buscar_ativo_por_id(session, usuario_id)
    if usuario is None:
        raise sessao_expirada
    return auth_service.emitir_tokens(usuario)


@router.get("/me", response_model=UsuarioLeitura)
async def quem_sou_eu(
    usuario: Annotated[Usuario, Depends(obter_usuario_atual)],
) -> UsuarioLeitura:
    return UsuarioLeitura.model_validate(usuario)
