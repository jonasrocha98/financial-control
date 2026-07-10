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
    # Só os fixos vigentes NESTE mês. Um fixo cancelado em agosto continua
    # valendo para julho — do contrário o histórico mudaria sozinho.
    primeiro, ultimo = month_bounds(year, month)
    fixed = db.session.scalar(
        db.select(func.coalesce(func.sum(FixedExpense.amount), 0)).where(
            FixedExpense.household_id == household_id,
            FixedExpense.active.is_(True),
            db.or_(FixedExpense.start_date.is_(None), FixedExpense.start_date <= ultimo),
            db.or_(FixedExpense.end_date.is_(None), FixedExpense.end_date >= primeiro),
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


@dataclass
class CashPosition:
    """Visão de CAIXA: quando o dinheiro sai da conta, não quando foi gasto.

    A compra no cartão em junho só drena a conta em julho, quando a fatura é
    paga. É por isso que a 'sobra do mês' pode ser positiva enquanto a conta
    está vazia.
    """
    incomes: Decimal
    fixed: Decimal
    paid_from_account: Decimal   # gastos do mês pagos direto na conta
    last_month_card_bill: Decimal  # fatura do mês passado, paga neste mês
    this_month_card: Decimal     # compras no cartão deste mês (a pagar no próximo)

    @property
    def available(self) -> Decimal:
        """Quanto do dinheiro que entrou ainda não saiu (nem vai sair este mês)."""
        return _q(self.incomes - self.fixed - self.paid_from_account
                  - self.last_month_card_bill)


def _sum_daily(household_id: int, year: int, month: int, source: str | None) -> Decimal:
    q = db.select(func.coalesce(func.sum(DailyExpense.amount), 0)).where(
        DailyExpense.household_id == household_id,
        extract("year", DailyExpense.date) == year,
        extract("month", DailyExpense.date) == month,
    )
    if source:
        q = q.where(DailyExpense.source == source)
    return _q(db.session.scalar(q))


def compute_cash_position(household_id: int, year: int, month: int) -> CashPosition:
    anterior_ano, anterior_mes = (year, month - 1) if month > 1 else (year - 1, 12)
    resumo = compute_month_summary(household_id, year, month)
    return CashPosition(
        incomes=resumo.incomes,
        fixed=resumo.fixed_total,
        paid_from_account=_sum_daily(household_id, year, month, "conta"),
        last_month_card_bill=_sum_daily(household_id, anterior_ano, anterior_mes, "cartao"),
        this_month_card=_sum_daily(household_id, year, month, "cartao"),
    )


def month_progress(year: int, month: int) -> tuple[int, int]:
    """(dias decorridos, dias do mês). Serve para avisar que o mês não acabou."""
    total = monthrange(year, month)[1]
    hoje = date.today()
    if (hoje.year, hoje.month) != (year, month):
        return total, total          # mês passado: completo
    return hoje.day, total


def current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)
