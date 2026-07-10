"""Testes do planner de compras futuras (alocação gulosa por prioridade).

O que disputa a sobra do mês é a PARCELA, não o valor total da compra.
"""
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.services.planner import plan_purchases

HOJE = date(2026, 7, 15)


class FakePurchase:
    """Stub leve com a mesma interface que o planner usa (sem tocar no banco)."""

    def __init__(self, name, cost, priority, installments=1, target_date=None, created_at=None):
        self.name = name
        self.estimated_cost = Decimal(str(cost))
        self.priority = priority
        self.installments = installments
        self.target_date = target_date
        self.created_at = created_at or datetime(2024, 1, 1)

    @property
    def monthly_cost(self):
        return (self.estimated_cost / self.installments).quantize(
            Decimal("0.01"), ROUND_HALF_UP)


def _plan(compras, sobra):
    return plan_purchases(compras, Decimal(str(sobra)), hoje=HOJE)


# ------------------------------------------------------------------ à vista
def test_lista_vazia():
    plan = _plan([], 1000)
    assert plan.items == []
    assert plan.affordable_count == 0
    assert plan.remaining == Decimal("1000.00")


def test_ordena_por_prioridade():
    compras = [FakePurchase("Baixa", 100, 4), FakePurchase("Urgente", 100, 1),
               FakePurchase("Media", 100, 3)]
    assert [i.purchase.name for i in _plan(compras, 1000).items] == ["Urgente", "Media", "Baixa"]


def test_aloca_o_que_cabe_na_sobra():
    compras = [FakePurchase("A", 300, 1), FakePurchase("B", 300, 2), FakePurchase("C", 300, 3)]
    plan = _plan(compras, 700)
    assert plan.affordable_count == 2
    assert not plan.items[2].fits
    assert plan.items[2].missing == Decimal("200.00")
    assert plan.remaining == Decimal("100.00")


def test_sobra_negativa():
    plan = _plan([FakePurchase("A", 50, 1)], -200)
    assert plan.affordable_count == 0
    assert plan.remaining == Decimal("0.00")


def test_desempate_por_data_alvo():
    compras = [FakePurchase("SemPrazo", 100, 2),
               FakePurchase("ComPrazo", 100, 2, target_date=date(2026, 3, 1))]
    assert _plan(compras, 100).items[0].purchase.name == "ComPrazo"


def test_a_vista_tem_uma_parcela_e_quita_no_mes():
    item = _plan([FakePurchase("TV", 900, 1)], 1000).items[0]
    assert item.months == 1
    assert item.monthly_cost == Decimal("900.00")
    assert (item.quita_ano, item.quita_mes) == (2026, 7)   # o próprio mês


# --------------------------------------------------------------- parcelado
def test_parcelado_disputa_a_parcela_nao_o_total():
    """R$ 3.000 em 10x cabe numa sobra de R$ 500 — pesa R$ 300/mês."""
    plan = _plan([FakePurchase("Notebook", 3000, 1, installments=10)], 500)
    item = plan.items[0]
    assert item.fits
    assert item.monthly_cost == Decimal("300.00")
    assert item.total_cost == Decimal("3000.00")
    assert plan.remaining == Decimal("200.00")


def test_a_vista_o_mesmo_valor_nao_caberia():
    plan = _plan([FakePurchase("Notebook", 3000, 1)], 500)
    assert not plan.items[0].fits
    assert plan.items[0].missing == Decimal("2500.00")


def test_parcelado_projeta_o_mes_de_quitacao():
    # jul/2026 + 9 meses = abr/2027
    item = _plan([FakePurchase("Notebook", 3000, 1, installments=10)], 500).items[0]
    assert (item.quita_ano, item.quita_mes) == (2027, 4)
    assert item.quita_em == "abr/27"


def test_parcela_que_nao_cabe_reporta_o_que_falta_por_mes():
    item = _plan([FakePurchase("Moto", 12000, 1, installments=12)], 300).items[0]
    assert not item.fits
    assert item.monthly_cost == Decimal("1000.00")
    assert item.missing == Decimal("700.00")   # falta por MÊS, não o total


def test_comprometimento_mensal_soma_so_o_que_coube():
    compras = [FakePurchase("A", 1200, 1, installments=12),   # 100/mês, cabe
               FakePurchase("B", 6000, 2, installments=10)]   # 600/mês, não cabe
    plan = _plan(compras, 300)
    assert plan.affordable_count == 1
    assert plan.monthly_committed == Decimal("100.00")
    assert plan.total_pending == Decimal("7200.00")


def test_parcelamento_arredonda_centavos():
    item = _plan([FakePurchase("X", 100, 1, installments=3)], 1000).items[0]
    assert item.monthly_cost == Decimal("33.33")


def test_quitacao_vira_o_ano():
    item = _plan([FakePurchase("X", 600, 1, installments=12)], 1000).items[0]
    assert item.quita_em == "jun/27"
