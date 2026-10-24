"""Senhas (argon2) e tokens (JWT). Toda a criptografia do projeto fica aqui."""

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

ALGORITMO_JWT = "HS256"

# Parâmetros padrão do argon2-cffi (perfil recomendado pela RFC 9106)
_hasher = PasswordHasher()

# Hash "de mentira": usado quando o e-mail não existe, para que a resposta
# demore o mesmo tempo e não revele quais e-mails têm conta
_HASH_FICTICIO = _hasher.hash("senha-ficticia-para-igualar-o-tempo")


# ---------- Senhas ----------


def gerar_hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerificationError, InvalidHashError):
        return False


def simular_verificacao(senha: str) -> None:
    """Gasta o mesmo tempo de uma verificação real (contra enumeração de e-mails)."""
    verificar_senha(senha, _HASH_FICTICIO)


def precisa_rehash(senha_hash: str) -> bool:
    """True se o hash foi gerado com parâmetros mais fracos que os atuais."""
    return _hasher.check_needs_rehash(senha_hash)


# ---------- Tokens ----------


class TipoToken(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenInvalido(Exception):
    """Token expirado, adulterado, malformado ou do tipo errado."""


def criar_token(usuario_id: uuid.UUID, tipo: TipoToken) -> str:
    settings = get_settings()
    agora = datetime.now(UTC)
    if tipo is TipoToken.ACCESS:
        duracao = timedelta(minutes=settings.jwt_access_token_minutes)
    else:
        duracao = timedelta(days=settings.jwt_refresh_token_days)

    conteudo = {
        "sub": str(usuario_id),  # o token só diz QUEM; o resto vem do banco
        "type": tipo.value,
        "iat": agora,
        "exp": agora + duracao,
        "jti": uuid.uuid4().hex,  # id único do token (base da revogação na 5b)
    }
    return jwt.encode(
        conteudo, settings.jwt_secret_key.get_secret_value(), algorithm=ALGORITMO_JWT
    )


def decodificar_token(token: str, tipo_esperado: TipoToken) -> uuid.UUID:
    """Valida assinatura, expiração e tipo. Retorna o id do usuário."""
    settings = get_settings()
    try:
        conteudo = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[ALGORITMO_JWT],  # lista fixa: impede o truque do alg "none"
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError:
        raise TokenInvalido from None

    # Impede usar o refresh (7 dias) como se fosse access (15 min)
    if conteudo.get("type") != tipo_esperado.value:
        raise TokenInvalido

    try:
        return uuid.UUID(conteudo["sub"])
    except (ValueError, TypeError):
        raise TokenInvalido from None
