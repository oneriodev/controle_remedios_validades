"""Regras de negócio da importação do cadastro de produtos."""

import uuid

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import produto_repository
from app.schemas.produto import ErroLinha, ResultadoImportacao
from app.services.importacao_produtos import processar_arquivo


class ErrosNaImportacao(Exception):
    """Uma ou mais linhas são inválidas; nada foi importado."""

    def __init__(self, erros: list[ErroLinha]) -> None:
        super().__init__(f"{len(erros)} erro(s) na planilha")
        self.erros = erros


async def importar_produtos(
    session: AsyncSession, farmacia_id: uuid.UUID, conteudo: bytes, nome_arquivo: str
) -> ResultadoImportacao:
    # Ler planilha é trabalho de CPU: roda numa thread para não travar a API
    produtos, erros = await to_thread.run_sync(processar_arquivo, conteudo, nome_arquivo)
    if erros:
        raise ErrosNaImportacao(erros)  # tudo ou nada

    eans = [p.ean for p in produtos]
    ja_existentes = await produto_repository.contar_existentes(session, farmacia_id, eans)

    registros = [{"farmacia_id": farmacia_id, **p.model_dump()} for p in produtos]
    await produto_repository.inserir_ou_atualizar(session, registros)
    # Commit único no final: se algum bloco falhar, nada fica gravado
    await session.commit()

    return ResultadoImportacao(
        total_linhas=len(produtos),
        inseridos=len(produtos) - ja_existentes,
        atualizados=ja_existentes,
    )