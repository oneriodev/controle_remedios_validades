"""Regras de negócio puras sobre produtos (sem banco, sem HTTP)."""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Textos que começam assim viram fórmula ao abrir no Excel/LibreOffice
PREFIXOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")

_CUSTO_MAXIMO = Decimal("9999999999.99")  # limite da coluna Numeric(12, 2)


def normalizar_ean(valor: object) -> str:
    """Converte o EAN em texto, inclusive quando vem como número do Excel."""
    if valor is None or isinstance(valor, bool):
        raise ValueError("EAN é obrigatório")
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        if not valor.is_integer():
            raise ValueError("EAN inválido")
        return str(int(valor))
    texto = str(valor).strip()
    if not re.fullmatch(r"[0-9]{8,14}", texto):
        raise ValueError("EAN deve ter de 8 a 14 dígitos numéricos")
    return texto


def ean_digito_valido(ean: str) -> bool:
    """Confere o dígito verificador (algoritmo GS1, vale para EAN-8/13 e GTIN-14)."""
    digitos = [int(caractere) for caractere in ean]
    corpo, verificador = digitos[:-1], digitos[-1]
    # Da direita para a esquerda: pesos 3, 1, 3, 1...
    soma = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(corpo)))
    return (10 - soma % 10) % 10 == verificador


def converter_custo(valor: object) -> Decimal:
    """Aceita 8,50 / 8.50 / 1.234,56 / R$ 8,50 e números vindos do Excel."""
    if valor is None or isinstance(valor, bool):
        raise ValueError("Custo é obrigatório")

    if isinstance(valor, (int, float, Decimal)):
        texto = str(valor)
    else:
        texto = str(valor).strip().replace("R$", "").replace(" ", "")
        if not texto:
            raise ValueError("Custo é obrigatório")
        if "," in texto and "." in texto:
            # Formato brasileiro com milhar: 1.234,56
            texto = texto.replace(".", "").replace(",", ".")
        elif "," in texto:
            texto = texto.replace(",", ".")

    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise ValueError("Custo inválido; use números como 8,50") from None

    if not numero.is_finite():
        raise ValueError("Custo inválido; use números como 8,50")
    if numero < 0:
        raise ValueError("Custo não pode ser negativo")
    if numero > _CUSTO_MAXIMO:
        raise ValueError("Custo acima do limite aceito")

    # ERPs costumam exportar 4 casas decimais: arredondamos para centavos
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def limpar_texto(valor: object, campo: str, tamanho_maximo: int) -> str | None:
    """Remove espaços, recusa fórmulas e textos longos demais. Vazio vira None."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if texto.startswith(PREFIXOS_DE_FORMULA):
        raise ValueError(
            f"{campo} não pode começar com =, +, - ou @ (proteção contra fórmulas)"
        )
    if len(texto) > tamanho_maximo:
        raise ValueError(f"{campo} pode ter no máximo {tamanho_maximo} caracteres")
    return texto
