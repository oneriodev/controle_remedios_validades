"""Dependências compartilhadas entre as rotas."""

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.repositories import farmacia_repository


async def obter_farmacia_id(
    x_farmacia_id: Annotated[uuid.UUID, Header(description="PROVISÓRIO: só desenvolvimento")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> uuid.UUID:
    """Identifica a farmácia da requisição.

    ⚠️ PROVISÓRIO (Etapa 4): lê um cabeçalho que qualquer um pode forjar.
    Na Etapa 5 o id passa a vir do token JWT, e as rotas não mudam.
    """
    farmacia = await farmacia_repository.buscar_ativa(session, x_farmacia_id)
    if farmacia is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmácia inválida ou inativa",
        )
    return farmacia.id