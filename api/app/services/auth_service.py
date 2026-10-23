"""Regras de negócio de autenticação."""

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    TipoToken,
    criar_token,
    gerar_hash_senha,
    precisa_rehash,
    simular_verificacao,
    verificar_senha,
)
from app.models import Usuario
from app.repositories import usuario_repository
from app.schemas.auth import TokenResposta

TAMANHO_MINIMO_SENHA = 10
TAMANHO_MAXIMO_SENHA = 128  # sem limite, uma "senha" de MBs vira ataque ao argon2


def validar_politica_senha(senha: str, email: str) -> None:
    """Lança ValueError com uma mensagem clara se a senha for fraca."""
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise ValueError(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres")
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        raise ValueError(f"A senha pode ter no máximo {TAMANHO_MAXIMO_SENHA} caracteres")
    if senha.lower() == email.lower() or senha.lower() == email.split("@")[0].lower():
        raise ValueError("A senha não pode ser igual ao e-mail")


async def autenticar(session: AsyncSession, email: str, senha: str) -> Usuario | None:
    """Retorna o usuário se e-mail e senha conferem; senão, None (sem dizer o motivo)."""
    email = email.strip().lower()
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        return None

    usuario = await usuario_repository.buscar_ativo_por_email(session, email)
    if usuario is None:
        # Gasta o mesmo tempo: a resposta não revela se o e-mail existe
        await to_thread.run_sync(simular_verificacao, senha)
        return None

    if not await to_thread.run_sync(verificar_senha, senha, usuario.senha_hash):
        return None

    # Se os parâmetros do argon2 ficaram mais fortes, atualiza o hash agora
    if precisa_rehash(usuario.senha_hash):
        usuario.senha_hash = await to_thread.run_sync(gerar_hash_senha, senha)
        await session.commit()

    return usuario


def emitir_tokens(usuario: Usuario) -> TokenResposta:
    return TokenResposta(
        access_token=criar_token(usuario.id, TipoToken.ACCESS),
        refresh_token=criar_token(usuario.id, TipoToken.REFRESH),
        expira_em_segundos=get_settings().jwt_access_token_minutes * 60,
    )