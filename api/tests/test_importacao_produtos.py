"""Testes da leitura e validação da planilha de produtos."""

import io
from decimal import Decimal

import openpyxl
import pytest

from app.services.importacao_produtos import ArquivoInvalido, processar_arquivo
from app.services.regras_produto import converter_custo, ean_digito_valido

CABECALHO = "ean;nome_medicamento;laboratório;custo_unitario\n"


@pytest.mark.parametrize("ean", ["7890000000017", "7890000000024", "7890000000055"])
def test_digito_verificador_valido(ean):
    assert ean_digito_valido(ean)


def test_digito_verificador_invalido():
    assert not ean_digito_valido("7890000000018")


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("8,50", Decimal("8.50")),
        ("8.50", Decimal("8.50")),
        ("1.234,56", Decimal("1234.56")),
        ("R$ 8,50", Decimal("8.50")),
        ("3,2499", Decimal("3.25")),  # 4 casas, como exportam os ERPs
        (8.5, Decimal("8.50")),  # número vindo do Excel
    ],
)
def test_converte_custo(entrada, esperado):
    assert converter_custo(entrada) == esperado


@pytest.mark.parametrize("entrada", ["-5,00", "abc", "", None, "NaN"])
def test_recusa_custo_invalido(entrada):
    with pytest.raises(ValueError):
        converter_custo(entrada)


def test_csv_padrao_brasileiro_em_windows_1252():
    # Acento no cabeçalho + codificação do Excel brasileiro
    conteudo = (CABECALHO + "7890000000017;Losartana;Lab Exemplo;8,50\n").encode("cp1252")
    produtos, erros = processar_arquivo(conteudo, "produtos.csv")
    assert erros == []
    assert produtos[0].custo_unitario == Decimal("8.50")
    assert produtos[0].laboratorio == "Lab Exemplo"


def test_formula_e_ean_repetido_sao_recusados():
    conteudo = (
        CABECALHO
        + "7890000000017;Losartana;;8,50\n"
        + '7890000000024;=HYPERLINK("x");;3,20\n'
        + "7890000000017;Repetida;;8,50\n"
    ).encode()
    _, erros = processar_arquivo(conteudo, "produtos.csv")
    assert [e.linha for e in erros] == [3, 4]


def test_coluna_obrigatoria_ausente():
    conteudo = b"ean;nome_medicamento\n7890000000017;Losartana\n"
    with pytest.raises(ArquivoInvalido, match="custo_unitario"):
        processar_arquivo(conteudo, "produtos.csv")


def test_extensao_falsa_e_recusada():
    # Um zip (ou .xlsx) renomeado para .csv
    with pytest.raises(ArquivoInvalido):
        processar_arquivo(b"PK\x03\x04conteudo", "produtos.csv")


def test_xlsx_com_ean_numerico():
    livro = openpyxl.Workbook()
    planilha = livro.active
    planilha.append(["EAN", "Nome Medicamento", "Laboratorio", "Custo Unitario"])
    planilha.append([7890000000017, "Losartana", "Lab", 8.5])  # EAN como número
    memoria = io.BytesIO()
    livro.save(memoria)

    produtos, erros = processar_arquivo(memoria.getvalue(), "produtos.xlsx")
    assert erros == []
    assert produtos[0].ean == "7890000000017"
    assert produtos[0].custo_unitario == Decimal("8.50")