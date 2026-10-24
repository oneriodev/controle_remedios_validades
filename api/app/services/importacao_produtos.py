"""Leitura e validação da planilha de produtos (sem banco, sem HTTP)."""

import csv
import io
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from pydantic import ValidationError

from app.schemas.produto import ErroLinha, ProdutoImportacao

LIMITE_LINHAS = 20_000
LIMITE_DESCOMPACTADO_XLSX = 50 * 1024 * 1024  # 50 MB: proteção contra "bomba zip"
ASSINATURA_ZIP = b"PK\x03\x04"  # todo .xlsx é um zip por dentro

COLUNAS_OBRIGATORIAS = {"ean", "nome_medicamento", "custo_unitario"}
COLUNAS_ACEITAS = COLUNAS_OBRIGATORIAS | {"laboratorio"}


class ArquivoInvalido(Exception):
    """O arquivo inteiro foi recusado (tipo, tamanho, estrutura)."""


@dataclass
class LinhaBruta:
    numero: int  # número da linha como o gerente vê na planilha
    valores: dict[str, object]


def processar_arquivo(
    conteudo: bytes, nome_arquivo: str
) -> tuple[list[ProdutoImportacao], list[ErroLinha]]:
    """Lê o arquivo e valida as linhas. Retorna (produtos válidos, erros)."""
    linhas = _ler_planilha(conteudo, nome_arquivo)
    return _validar_linhas(linhas)


# ---------- Leitura ----------


def _ler_planilha(conteudo: bytes, nome_arquivo: str) -> list[LinhaBruta]:
    if not conteudo:
        raise ArquivoInvalido("O arquivo está vazio")

    extensao = Path(nome_arquivo).suffix.lower()
    if extensao == ".csv":
        tabela = _ler_csv(conteudo)
    elif extensao == ".xlsx":
        tabela = _ler_xlsx(conteudo)
    else:
        raise ArquivoInvalido("Envie um arquivo .csv ou .xlsx")

    return _montar_linhas(tabela)


def _ler_csv(conteudo: bytes) -> list[list[object]]:
    # Não confiamos na extensão: um CSV de verdade é texto
    if conteudo.startswith(ASSINATURA_ZIP) or b"\x00" in conteudo:
        raise ArquivoInvalido("O conteúdo não é um CSV de texto")

    # Excel em português costuma salvar em Windows-1252, não em UTF-8
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ArquivoInvalido(
            "Não foi possível ler o texto do CSV (codificação desconhecida)"
        )

    primeira_linha = texto.split("\n", 1)[0]
    separador = ";" if primeira_linha.count(";") >= primeira_linha.count(",") else ","

    leitor = csv.reader(io.StringIO(texto, newline=""), delimiter=separador)
    tabela: list[list[object]] = []
    for linha in leitor:
        tabela.append(list(linha))
        if len(tabela) > LIMITE_LINHAS + 1:  # +1 pelo cabeçalho
            raise ArquivoInvalido(
                f"O arquivo passa do limite de {LIMITE_LINHAS} linhas"
            )
    return tabela


def _ler_xlsx(conteudo: bytes) -> list[list[object]]:
    if not conteudo.startswith(ASSINATURA_ZIP):
        raise ArquivoInvalido("O conteúdo não é uma planilha .xlsx válida")

    # Proteção contra "bomba zip": soma o tamanho descompactado antes de abrir
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
            tamanho_total = sum(info.file_size for info in pacote.infolist())
    except zipfile.BadZipFile:
        raise ArquivoInvalido("O conteúdo não é uma planilha .xlsx válida") from None
    if tamanho_total > LIMITE_DESCOMPACTADO_XLSX:
        raise ArquivoInvalido("A planilha é grande demais depois de descompactada")

    try:
        # data_only=True: lê os VALORES das células, nunca as fórmulas
        livro = openpyxl.load_workbook(
            io.BytesIO(conteudo), read_only=True, data_only=True
        )
    except Exception:  # noqa: BLE001 - arquivo hostil pode lançar qualquer erro
        raise ArquivoInvalido("Não foi possível abrir a planilha .xlsx") from None
    try:
        tabela: list[list[object]] = []
        for linha in livro.worksheets[0].iter_rows(values_only=True):
            tabela.append(list(linha))
            if len(tabela) > LIMITE_LINHAS + 1:
                raise ArquivoInvalido(
                    f"A planilha passa do limite de {LIMITE_LINHAS} linhas"
                )
        return tabela
    finally:
        livro.close()


def _normalizar_nome_coluna(nome: object) -> str:
    """'Laboratório ' → 'laboratorio'; 'Custo Unitario' → 'custo_unitario'."""
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    sem_acento = "".join(c for c in texto if not unicodedata.combining(c))
    return sem_acento.strip().lower().replace(" ", "_")


def _montar_linhas(tabela: list[list[object]]) -> list[LinhaBruta]:
    if not tabela:
        raise ArquivoInvalido("O arquivo está vazio")

    cabecalho = [_normalizar_nome_coluna(c) for c in tabela[0]]
    faltando = COLUNAS_OBRIGATORIAS - set(cabecalho)
    if faltando:
        raise ArquivoInvalido(
            f"Colunas obrigatórias ausentes: {', '.join(sorted(faltando))}. "
            "O cabeçalho deve conter: ean, nome_medicamento, custo_unitario "
            "(laboratorio é opcional)"
        )

    # Só as colunas que usamos; as demais (comuns em exportações de ERP) são ignoradas
    posicoes = {
        nome: cabecalho.index(nome) for nome in COLUNAS_ACEITAS if nome in cabecalho
    }

    linhas: list[LinhaBruta] = []
    for numero, linha in enumerate(tabela[1:], start=2):  # linha 1 = cabeçalho
        if all(c is None or str(c).strip() == "" for c in linha):
            continue  # pula linhas em branco
        valores = {
            nome: (linha[i] if i < len(linha) else None) for nome, i in posicoes.items()
        }
        linhas.append(LinhaBruta(numero=numero, valores=valores))

    if not linhas:
        raise ArquivoInvalido("O arquivo não tem nenhuma linha de produto")
    return linhas


# ---------- Validação ----------


def _validar_linhas(
    linhas: list[LinhaBruta],
) -> tuple[list[ProdutoImportacao], list[ErroLinha]]:
    validos: list[ProdutoImportacao] = []
    erros: list[ErroLinha] = []
    primeira_ocorrencia: dict[str, int] = {}

    for linha in linhas:
        try:
            produto = ProdutoImportacao.model_validate(linha.valores)
        except ValidationError as exc:
            for erro in exc.errors():
                campo = str(erro["loc"][0]) if erro["loc"] else None
                mensagem = erro["msg"].removeprefix("Value error, ")
                erros.append(ErroLinha(linha=linha.numero, campo=campo, erro=mensagem))
            continue

        # O mesmo EAN duas vezes no arquivo: qual custo vale? Melhor recusar.
        if produto.ean in primeira_ocorrencia:
            erros.append(
                ErroLinha(
                    linha=linha.numero,
                    campo="ean",
                    erro=f"EAN repetido (já aparece na linha {primeira_ocorrencia[produto.ean]})",
                )
            )
            continue

        primeira_ocorrencia[produto.ean] = linha.numero
        validos.append(produto)

    return validos, erros
