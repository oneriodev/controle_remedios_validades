"""Schemas de coleta de lote/validade."""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    WithJsonSchema,
    field_validator,
)

from app.services.regras_validade import FaixaRisco, converter_validade_mm_aaaa

# O app envia "MM/AAAA"; a API transforma no último dia do mês.
# O WithJsonSchema faz o Swagger mostrar o formato de texto esperado.
ValidadeMMAAAA = Annotated[
    date,
    BeforeValidator(converter_validade_mm_aaaa),
    WithJsonSchema(
        {"type": "string", "pattern": "^(0[1-9]|1[0-2])/[0-9]{4}$", "examples": ["03/2027"]}
    ),
]


class LoteValidadeCriar(BaseModel):
    """Dados que o app envia ao registrar uma coleta."""

    # Recusa campos desconhecidos (ex.: o app tentando mandar "situacao")
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: uuid.UUID = Field(description="Gerado no aparelho; chave de idempotência")
    ean_produto: str = Field(pattern=r"^[0-9]{8,14}$")
    lote: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9./\- ]+$")
    validade: ValidadeMMAAAA
    quantidade_prateleira: int = Field(gt=0, le=10_000)
    data_coleta: AwareDatetime = Field(description="Data/hora do celular, com fuso")

    @field_validator("lote")
    @classmethod
    def padronizar_lote(cls, valor: str) -> str:
        # "l123" e "L123" devem ser o mesmo lote num recall
        return valor.upper()


class LoteValidadeLeitura(BaseModel):
    """O que a API devolve após registrar (ou reencontrar) uma coleta."""

    id: uuid.UUID
    ean_produto: str
    lote: str
    data_validade: date
    quantidade_prateleira: int
    data_coleta: datetime
    recebido_em: datetime
    situacao: str
    # Calculados no servidor, na hora da consulta
    dias_para_vencer: int
    faixa_risco: FaixaRisco