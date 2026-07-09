"""Funções utilitárias compartilhadas."""
from decimal import Decimal


def format_currency(value) -> str:
    """Formata um número como moeda brasileira: 1234.5 -> 'R$ 1.234,50'."""
    if value is None:
        value = 0
    value = Decimal(str(value))
    inteiro, _, centavos = f"{value:,.2f}".partition(".")
    # f-string usa vírgula para milhar e ponto para decimal; troca para pt-BR
    inteiro = inteiro.replace(",", ".")
    return f"R$ {inteiro},{centavos}"
