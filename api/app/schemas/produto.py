"""Schemas (formato de entrada/saída) de produtos."""

from pydantic import BaseModel, ConfigDict


class ProdutoLeitura(BaseModel):
    """O que o app recebe ao ler um EAN. O custo NÃO é exposto aqui."""

    model_config = ConfigDict(from_attributes=True)

    ean: str
    nome_medicamento: str
    laboratorio: str | None