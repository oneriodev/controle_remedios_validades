"""Cria um usuário pela linha de comando (usado para o primeiro gerente).

Uso (dentro de api/):
    python -m app.scripts.criar_usuario --farmacia-id <uuid> --nome "Nome" \
        --email nome@exemplo.test --perfil gerente

A senha é pedida de forma oculta: nunca a passe como argumento
(ela ficaria gravada no histórico do terminal).
"""

import argparse
import asyncio
import getpass
import re
import sys
import uuid

from app.core.database import SessionLocal, engine
from app.core.security import gerar_hash_senha
from app.models import Perfil, Usuario
from app.repositories import farmacia_repository, usuario_repository
from app.services.auth_service import validar_politica_senha

_PADRAO_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _ler_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cria um usuário do sistema")
    parser.add_argument("--farmacia-id", required=True, type=uuid.UUID)
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--perfil", required=True, choices=[p.value for p in Perfil])
    return parser.parse_args()


def _falhar(mensagem: str) -> None:
    print(f"Erro: {mensagem}", file=sys.stderr)
    sys.exit(1)


async def _criar(args: argparse.Namespace) -> None:
    email = args.email.strip().lower()
    nome = args.nome.strip()
    if not _PADRAO_EMAIL.fullmatch(email):
        _falhar("e-mail inválido")
    if not 1 <= len(nome) <= 120:
        _falhar("o nome deve ter de 1 a 120 caracteres")

    senha = getpass.getpass("Senha (não aparece na tela): ")
    if senha != getpass.getpass("Repita a senha: "):
        _falhar("as senhas não conferem")
    try:
        validar_politica_senha(senha, email)
    except ValueError as exc:
        _falhar(str(exc))

    try:
        async with SessionLocal() as session:
            if await farmacia_repository.buscar_ativa(session, args.farmacia_id) is None:
                _falhar("farmácia não encontrada ou inativa")
            if await usuario_repository.existe_email(session, email):
                _falhar("já existe um usuário com este e-mail")

            usuario = Usuario(
                farmacia_id=args.farmacia_id,
                nome=nome,
                email=email,
                senha_hash=gerar_hash_senha(senha),
                perfil=args.perfil,
            )
            session.add(usuario)
            await session.commit()
            print(f"Usuário criado: {usuario.id} ({usuario.perfil})")
    finally:
        await engine.dispose()  # fecha as conexões antes de sair


if __name__ == "__main__":
    asyncio.run(_criar(_ler_argumentos()))