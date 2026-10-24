"""Schemas (formato de entrada/saída) de produtos."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.regras_produto import (
    converter_custo,
    ean_digito_valido,
    limpar_texto,
    normalizar_ean,
)


class ProdutoLeitura(BaseModel):
    """O que o app recebe ao ler um EAN. O custo NÃO é exposto aqui."""

    model_config = ConfigDict(from_attributes=True)

    ean: str
    nome_medicamento: str
    laboratorio: str | None


class ProdutoImportacao(BaseModel):
    """Uma linha da planilha de cadastro, já validada e convertida."""

    ean: str
    nome_medicamento: str
    laboratorio: str | None = None
    custo_unitario: Decimal

    @field_validator("ean", mode="before")
    @classmethod
    def validar_ean(cls, valor: object) -> str:
        ean = normalizar_ean(valor)
        if not ean_digito_valido(ean):
            raise ValueError("Dígito verificador do EAN inválido; confira o código")
        return ean

    @field_validator("nome_medicamento", mode="before")
    @classmethod
    def validar_nome(cls, valor: object) -> str:
        nome = limpar_texto(valor, "Nome do medicamento", 200)
        if nome is None:
            raise ValueError("Nome do medicamento é obrigatório")
        return nome

    @field_validator("laboratorio", mode="before")
    @classmethod
    def validar_laboratorio(cls, valor: object) -> str | None:
        return limpar_texto(valor, "Laboratório", 120)

    @field_validator("custo_unitario", mode="before")
    @classmethod
    def validar_custo(cls, valor: object) -> Decimal:
        return converter_custo(valor)


class ErroLinha(BaseModel):
    """Um problema encontrado numa linha da planilha."""

    linha: int
    campo: str | None
    erro: str


class ResultadoImportacao(BaseModel):
    """Resumo devolvido após uma importação bem-sucedida."""

    total_linhas: int
    inseridos: int
    atualizados: int
