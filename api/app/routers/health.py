"""Rota de verificação de saúde da API e do banco."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Saúde"])


@router.get("/health")
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        # O detalhe técnico vai para o log do servidor, nunca para o cliente
        logger.exception("Falha ao acessar o banco no health check")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        )
    return {"status": "ok", "banco": "ok"}
