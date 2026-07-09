"""Testes do planner de compras futuras (alocação gulosa por prioridade)."""
from datetime import date, datetime
from decimal import Decimal

from app.services.planner import plan_purchases


class FakePurchase:
    """Stub leve com a mesma interface que o planner usa (sem tocar no banco)."""

    def __init__(self, name, cost, priority, target_date=None, created_at=None):
        self.name = name
        self.estimated_cost = Decimal(str(cost))
        self.priority = priority
        self.target_date = target_date
        self.created_at = created_at or datetime(2024, 1, 1)


def test_lista_vazia():
    plan = plan_purchases([], Decimal("1000"))
    assert plan.items == []
    assert plan.affordable_count == 0
    assert plan.remaining == Decimal("1000.00")


def test_ordena_por_prioridade():
    compras = [
        FakePurchase("Baixa", 100, priority=4),
        FakePurchase("Urgente", 100, priority=1),
        FakePurchase("Media", 100, priority=3),
    ]
    plan = plan_purchases(compras, Decimal("1000"))
    nomes = [i.purchase.name for i in plan.items]
    assert nomes == ["Urgente", "Media", "Baixa"]


def test_aloca_o_que_cabe_na_sobra():
    compras = [
        FakePurchase("A", 300, priority=1),
        FakePurchase("B", 300, priority=2),
        FakePurchase("C", 300, priority=3),
    ]
    plan = plan_purchases(compras, Decimal("700"))
    # A e B cabem (600), C não (faltam 200)
    assert plan.affordable_count == 2
    assert plan.items[0].fits and plan.items[1].fits
    assert not plan.items[2].fits
    assert plan.items[2].missing == Decimal("200.00")
    assert plan.remaining == Decimal("100.00")


def test_sobra_zero_nada_cabe():
    compras = [FakePurchase("A", 50, priority=1)]
    plan = plan_purchases(compras, Decimal("0"))
    assert plan.affordable_count == 0
    assert plan.items[0].missing == Decimal("50.00")


def test_sobra_negativa():
    compras = [FakePurchase("A", 50, priority=1)]
    plan = plan_purchases(compras, Decimal("-200"))
    assert plan.affordable_count == 0
    assert plan.items[0].fits is False
    assert plan.remaining == Decimal("0.00")


def test_total_pending_e_missing():
    compras = [
        FakePurchase("A", 400, priority=1),
        FakePurchase("B", 400, priority=2),
    ]
    plan = plan_purchases(compras, Decimal("500"))
    assert plan.total_pending == Decimal("800.00")
    assert plan.total_missing == Decimal("300.00")


def test_desempate_por_data_alvo():
    compras = [
        FakePurchase("SemPrazo", 100, priority=2, target_date=None),
        FakePurchase("ComPrazo", 100, priority=2, target_date=date(2024, 3, 1)),
    ]
    plan = plan_purchases(compras, Decimal("100"))
    # mesma prioridade: quem tem prazo mais próximo vem primeiro
    assert plan.items[0].purchase.name == "ComPrazo"
