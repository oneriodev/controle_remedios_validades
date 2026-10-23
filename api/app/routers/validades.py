"""Rotas de coleta de lote/validade."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import obter_farmacia_id
from app.schemas.lote_validade import LoteValidadeCriar, LoteValidadeLeitura
from app.services import validade_service

router = APIRouter(prefix="/api/validades", tags=["Validades"])


@router.post(
    "",
    response_model=LoteValidadeLeitura,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Reenvio da mesma coleta (nada foi duplicado)"},
        404: {"description": "Produto não cadastrado nesta farmácia"},
        409: {"description": "Este id de coleta já foi usado com dados diferentes"},
    },
)
async def registrar_coleta(
    dados: LoteValidadeCriar,
    response: Response,
    farmacia_id: Annotated[uuid.UUID, Depends(obter_farmacia_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoteValidadeLeitura:
    try:
        coleta, criada = await validade_service.registrar_coleta(session, farmacia_id, dados)
    except validade_service.ProdutoNaoEncontrado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não cadastrado nesta farmácia",
        )
    except validade_service.ConflitoIdempotencia:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este id de coleta já foi usado com dados diferentes",
        )

    if not criada:
        response.status_code = status.HTTP_200_OK  # reenvio idempotente
    return validade_service.para_leitura(coleta)