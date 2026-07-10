"""Planejador de compras futuras: aloca a SOBRA por prioridade (algoritmo guloso).

Sem IA — ordena por (prioridade, prazo, criação) e distribui o saldo disponível de
cima para baixo, marcando o que cabe no mês, o que não cabe e quanto falta.

O que pesa no orçamento de um mês é a PARCELA, não o valor total. Uma compra de
R$ 3.000 em 10x custa R$ 300 no mês — mas compromete os dez meses seguintes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..models import FuturePurchase

MESES_PT = ["", "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _mes_futuro(base: tuple[int, int], somar: int) -> tuple[int, int]:
    ano, mes = base
    total = mes - 1 + somar
    return ano + total // 12, total % 12 + 1


@dataclass
class PlannedPurchase:
    purchase: FuturePurchase
    fits: bool                 # a parcela cabe na sobra deste mês?
    missing: Decimal           # quanto falta por mês (0 se cabe)
    cumulative_cost: Decimal   # custo mensal acumulado, na ordem de prioridade
    monthly_cost: Decimal      # o que sai por mês
    months: int                # em quantas parcelas
    quita_ano: int             # quando a última parcela cai
    quita_mes: int

    @property
    def total_cost(self) -> Decimal:
        return _q(self.purchase.estimated_cost)

    @property
    def quita_em(self) -> str:
        return f"{MESES_PT[self.quita_mes]}/{str(self.quita_ano)[2:]}"


@dataclass
class PurchasePlan:
    leftover: Decimal              # sobra inicial
    remaining: Decimal             # saldo após alocar o que coube
    items: list[PlannedPurchase]
    total_pending: Decimal         # soma do valor TOTAL das compras pendentes
    monthly_committed: Decimal     # soma das parcelas do que coube
    affordable_count: int

    @property
    def total_missing(self) -> Decimal:
        mensal = sum((i.monthly_cost for i in self.items), start=Decimal(0))
        return _q(max(mensal - self.leftover, Decimal(0)))


def _sort_key(p: FuturePurchase):
    far_future = date.max
    return (p.priority, p.target_date or far_future, p.created_at)


def plan_purchases(pending: list[FuturePurchase], leftover, hoje: date | None = None) -> PurchasePlan:
    """Recebe as compras pendentes e a sobra; devolve o plano alocado.

    Para cada compra, o que disputa a sobra é a PARCELA mensal.
    """
    hoje = hoje or date.today()
    base = (hoje.year, hoje.month)
    leftover = _q(leftover)
    ordered = sorted(pending, key=_sort_key)

    items: list[PlannedPurchase] = []
    saldo = leftover
    cumulative = Decimal("0.00")
    total_pending = Decimal("0.00")
    comprometido = Decimal("0.00")
    affordable = 0

    for p in ordered:
        n = p.installments or 1
        mensal = p.monthly_cost
        total_pending += _q(p.estimated_cost)
        cumulative = _q(cumulative + mensal)

        if mensal <= saldo:
            saldo = _q(saldo - mensal)
            fits = True
            missing = Decimal("0.00")
            comprometido = _q(comprometido + mensal)
            affordable += 1
        else:
            fits = False
            missing = _q(mensal - saldo) if saldo > 0 else mensal

        # a última parcela cai n-1 meses depois desta
        ano, mes = _mes_futuro(base, n - 1)
        items.append(PlannedPurchase(
            purchase=p, fits=fits, missing=missing, cumulative_cost=cumulative,
            monthly_cost=mensal, months=n, quita_ano=ano, quita_mes=mes,
        ))

    return PurchasePlan(
        leftover=leftover,
        remaining=_q(max(saldo, Decimal(0))),
        items=items,
        total_pending=_q(total_pending),
        monthly_committed=comprometido,
        affordable_count=affordable,
    )
