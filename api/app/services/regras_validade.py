"""Regras de negócio puras sobre validade (sem banco, sem HTTP)."""

import calendar
import re
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

# [0-9] em vez de \d: \d também aceita dígitos de outros alfabetos (ex.: árabes)
_PADRAO_MM_AAAA = re.compile(r"(0[1-9]|1[0-2])/([0-9]{4})")


class FaixaRisco(StrEnum):
    VENCIDO = "vencido"
    ATE_30_DIAS = "ate_30_dias"
    ATE_60_DIAS = "ate_60_dias"
    ATE_90_DIAS = "ate_90_dias"
    OK = "ok"


def converter_validade_mm_aaaa(valor: object) -> date:
    """Converte 'MM/AAAA' no ÚLTIMO dia daquele mês.

    O medicamento vale até o fim do mês impresso na caixa.
    Ex.: '02/2028' -> 2028-02-29 (ano bissexto).
    """
    if not isinstance(valor, str):
        # TypeError viraria erro 500: o Pydantic só converte ValueError em 422
        raise ValueError("A validade deve ser um texto no formato MM/AAAA")  # noqa: TRY004
    
    encontrado = _PADRAO_MM_AAAA.fullmatch(valor.strip())
    if encontrado is None:
        raise ValueError("Validade deve estar no formato MM/AAAA, ex.: 03/2027")

    mes, ano = int(encontrado.group(1)), int(encontrado.group(2))
    if not 2000 <= ano <= 2100:
        raise ValueError("Ano da validade fora do intervalo aceito (2000 a 2100)")

    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, ultimo_dia)


def hoje_no_fuso(fuso: str) -> date:
    """Data de hoje no fuso da farmácia (e não no fuso do servidor)."""
    return datetime.now(ZoneInfo(fuso)).date()


def dias_para_vencer(data_validade: date, hoje: date) -> int:
    """Negativo = já venceu há N dias."""
    return (data_validade - hoje).days


def calcular_faixa_risco(data_validade: date, hoje: date) -> FaixaRisco:
    """Classifica o lote pela distância até o vencimento.

    No último dia do mês o produto ainda é válido (dias = 0),
    por isso só é 'vencido' quando dias < 0.
    """
    dias = dias_para_vencer(data_validade, hoje)
    if dias < 0:
        return FaixaRisco.VENCIDO
    if dias <= 30:
        return FaixaRisco.ATE_30_DIAS
    if dias <= 60:
        return FaixaRisco.ATE_60_DIAS
    if dias <= 90:
        return FaixaRisco.ATE_90_DIAS
    return FaixaRisco.OK
