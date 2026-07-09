"""Cálculo do resumo mensal do orçamento (entradas, reserva, gastos, SOBRA).

Lógica 100% determinística — sem IA. Recebe os totais já somados (ou os calcula a
partir do household), e devolve um dataclass com tudo que o dashboard e o planner usam.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from calendar import monthrange

from sqlalchemy import extract, func

from ..extensions import db
from ..models import DailyExpense, FixedExpense, Income, InvestmentConfig


def _q(value) -> Decimal:
    """Converte para Decimal com 2 casas, tratando None como 0."""
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


@dataclass
class MonthSummary:
    year: int
    month: int
    incomes: Decimal          # total de entradas no mês
    investment_pct: Decimal   # % configurado
    investment_reserve: Decimal  # valor separado para investir
    fixed_total: Decimal      # total de gastos fixos ativos
    daily_total: Decimal      # total de gastos do dia a dia no mês
    leftover: Decimal         # SOBRA = entradas - reserva - fixos - diário

    @property
    def spent_total(self) -> Decimal:
        return _q(self.fixed_total + self.daily_total)


def compute_month_summary(household_id: int, year: int, month: int) -> MonthSummary:
    """Calcula o resumo do mês para um household."""
    incomes = db.session.scalar(
        db.select(func.coalesce(func.sum(Income.amount), 0)).where(
            Income.household_id == household_id,
            extract("year", Income.date) == year,
            extract("month", Income.date) == month,
        )
    )
    daily = db.session.scalar(
        db.select(func.coalesce(func.sum(DailyExpense.amount), 0)).where(
            DailyExpense.household_id == household_id,
            extract("year", DailyExpense.date) == year,
            extract("month", DailyExpense.date) == month,
        )
    )
    fixed = db.session.scalar(
        db.select(func.coalesce(func.sum(FixedExpense.amount), 0)).where(
            FixedExpense.household_id == household_id,
            FixedExpense.active.is_(True),
        )
    )
    config = db.session.scalar(
        db.select(InvestmentConfig).where(InvestmentConfig.household_id == household_id)
    )
    pct = _q(config.percentage if config else 0)

    incomes = _q(incomes)
    fixed = _q(fixed)
    daily = _q(daily)
    reserve = _q(incomes * pct / Decimal(100))
    leftover = _q(incomes - reserve - fixed - daily)

    return MonthSummary(
        year=year,
        month=month,
        incomes=incomes,
        investment_pct=pct,
        investment_reserve=reserve,
        fixed_total=fixed,
        daily_total=daily,
        leftover=leftover,
    )


def current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)
