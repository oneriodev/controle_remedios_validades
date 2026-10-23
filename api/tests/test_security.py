"""Testes de senhas e tokens."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    TipoToken,
    TokenInvalido,
    criar_token,
    decodificar_token,
    gerar_hash_senha,
    verificar_senha,
)
from app.services.auth_service import validar_politica_senha


def test_hash_confere_e_nao_contem_a_senha():
    senha = "balcao-azul-farmacia"
    hash_ = gerar_hash_senha(senha)
    assert senha not in hash_
    assert verificar_senha(senha, hash_)
    assert not verificar_senha("senha-errada-qualquer", hash_)


def test_mesma_senha_gera_hashes_diferentes():
    # O "sal" aleatório faz cada hash ser único
    assert gerar_hash_senha("mesma-senha-123") != gerar_hash_senha("mesma-senha-123")


def test_token_de_ida_e_volta():
    usuario_id = uuid.uuid4()
    token = criar_token(usuario_id, TipoToken.ACCESS)
    assert decodificar_token(token, TipoToken.ACCESS) == usuario_id


def test_refresh_nao_serve_como_access():
    token = criar_token(uuid.uuid4(), TipoToken.REFRESH)
    with pytest.raises(TokenInvalido):
        decodificar_token(token, TipoToken.ACCESS)


def test_token_adulterado_e_recusado():
    token = criar_token(uuid.uuid4(), TipoToken.ACCESS)
    cabecalho, conteudo, assinatura = token.split(".")
    # Troca o conteúdo pelo de outro token (outro usuário), mantendo a assinatura antiga
    outro = criar_token(uuid.uuid4(), TipoToken.ACCESS).split(".")[1]
    with pytest.raises(TokenInvalido):
        decodificar_token(f"{cabecalho}.{outro}.{assinatura}", TipoToken.ACCESS)


def test_token_expirado_e_recusado():
    agora = datetime.now(UTC)
    vencido = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "iat": agora - timedelta(hours=1),
            "exp": agora - timedelta(minutes=1),
        },
        get_settings().jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(TokenInvalido):
        decodificar_token(vencido, TipoToken.ACCESS)


def test_token_sem_assinatura_e_recusado():
    # O truque do algoritmo "none": token sem assinatura nenhuma
    sem_assinatura = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "iat": 1, "exp": 9999999999},
        key=None,
        algorithm="none",
    )
    with pytest.raises(TokenInvalido):
        decodificar_token(sem_assinatura, TipoToken.ACCESS)


@pytest.mark.parametrize(
    "senha", ["curta", "x" * 129, "gerente@exemplo.test", "gerente"]
)
def test_politica_de_senha_recusa_senhas_fracas(senha):
    with pytest.raises(ValueError):
        validar_politica_senha(senha, "gerente@exemplo.test")