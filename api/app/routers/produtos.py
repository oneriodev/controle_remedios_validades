"""Rotas de produtos."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import obter_farmacia_id
from app.repositories import produto_repository
from app.schemas.produto import ProdutoLeitura, ResultadoImportacao
from app.services import produto_service
from app.services.importacao_produtos import ArquivoInvalido

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/produtos", tags=["Produtos"])

TAMANHO_MAXIMO_UPLOAD = 2 * 1024 * 1024  # 2 MB
MAXIMO_ERROS_NA_RESPOSTA = 100


async def _ler_com_limite(arquivo: UploadFile) -> bytes:
    """Lê o arquivo em blocos e para assim que passar do limite."""
    partes: list[bytes] = []
    total = 0
    while bloco := await arquivo.read(64 * 1024):
        total += len(bloco)
        if total > TAMANHO_MAXIMO_UPLOAD:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="O arquivo passa do limite de 2 MB",
            )
        partes.append(bloco)
    return b"".join(partes)


@router.post(
    "/upload-csv",
    response_model=ResultadoImportacao,
    responses={
        400: {"description": "Arquivo recusado (tipo, estrutura ou colunas)"},
        413: {"description": "Arquivo maior que 2 MB"},
        422: {"description": "Linhas com erro; nada foi importado"},
    },
)
async def importar_cadastro(
    arquivo: Annotated[UploadFile, File(description="Planilha .csv ou .xlsx (máx. 2 MB)")],
    farmacia_id: Annotated[uuid.UUID, Depends(obter_farmacia_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResultadoImportacao:
    # TODO Etapa 5: permitir somente ao perfil gerente
    conteudo = await _ler_com_limite(arquivo)

    try:
        resultado = await produto_service.importar_produtos(
            session, farmacia_id, conteudo, arquivo.filename or ""
        )
    except ArquivoInvalido as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except produto_service.ErrosNaImportacao as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "mensagem": "Nenhum produto foi importado. Corrija os erros e envie novamente.",
                "total_erros": len(exc.erros),
                "erros": [e.model_dump() for e in exc.erros[:MAXIMO_ERROS_NA_RESPOSTA]],
            },
        )

    # Auditoria: quem e quanto, nunca o conteúdo (custos são confidenciais)
    logger.info(
        "Importação de produtos: farmacia=%s linhas=%d inseridos=%d atualizados=%d",
        farmacia_id,
        resultado.total_linhas,
        resultado.inseridos,
        resultado.atualizados,
    )
    return resultado


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