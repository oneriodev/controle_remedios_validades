"""Rotas de produtos."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import obter_farmacia_id
from app.repositories import produto_repository
from app.schemas.produto import ProdutoLeitura

router = APIRouter(prefix="/api/produtos", tags=["Produtos"])


@router.get(
    "/{ean}",
    response_model=ProdutoLeitura,
    responses={404: {"description": "Produto não cadastrado nesta farmácia"}},
)
async def consultar_por_ean(
    ean: Annotated[str, Path(pattern=r"^[0-9]{8,14}$")],
    farmacia_id: Annotated[uuid.UUID, Depends(obter_farmacia_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProdutoLeitura:
    produto = await produto_repository.buscar_por_ean(session, farmacia_id, ean)
    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não cadastrado nesta farmácia",
        )
    return ProdutoLeitura.model_validate(produto)