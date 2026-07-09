"""Planejador de compras futuras: aloca a SOBRA por prioridade (algoritmo guloso).

Sem IA — ordena por (prioridade, prazo, criação) e distribui o saldo disponível de
cima para baixo, marcando o que cabe no mês, o que não cabe e quanto falta.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..models import FuturePurchase


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


@dataclass
class PlannedPurchase:
    purchase: FuturePurchase
    fits: bool                 # cabe na sobra deste mês?
    missing: Decimal           # quanto falta para esta compra (0 se cabe)
    cumulative_cost: Decimal   # custo acumulado até esta compra (na ordem de prioridade)


@dataclass
class PurchasePlan:
    leftover: Decimal              # sobra inicial
    remaining: Decimal             # saldo após alocar as compras que couberam
    items: list[PlannedPurchase]
    total_pending: Decimal         # soma de todas as compras pendentes
    affordable_count: int          # quantas cabem este mês

    @property
    def total_missing(self) -> Decimal:
        return _q(max(self.total_pending - self.leftover, Decimal(0)))


def _sort_key(p: FuturePurchase):
    from datetime import date

    far_future = date.max
    return (p.priority, p.target_date or far_future, p.created_at)


def plan_purchases(pending: list[FuturePurchase], leftover) -> PurchasePlan:
    """Recebe a lista de compras pendentes e a sobra; devolve o plano alocado.

    `pending` deve conter apenas compras com status 'pendente'.
    """
    leftover = _q(leftover)
    ordered = sorted(pending, key=_sort_key)

    items: list[PlannedPurchase] = []
    saldo = leftover
    cumulative = Decimal("0.00")
    total_pending = Decimal("0.00")
    affordable = 0

    for p in ordered:
        cost = _q(p.estimated_cost)
        total_pending += cost
        cumulative = _q(cumulative + cost)

        if cost <= saldo:
            saldo = _q(saldo - cost)
            fits = True
            missing = Decimal("0.00")
            affordable += 1
        else:
            fits = False
            # quanto falta considerando o saldo ainda disponível
            missing = _q(cost - saldo) if saldo > 0 else cost

        items.append(
            PlannedPurchase(
                purchase=p,
                fits=fits,
                missing=missing,
                cumulative_cost=cumulative,
            )
        )

    return PurchasePlan(
        leftover=leftover,
        remaining=_q(max(saldo, Decimal(0))),
        items=items,
        total_pending=_q(total_pending),
        affordable_count=affordable,
    )
