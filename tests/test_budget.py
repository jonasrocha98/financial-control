"""Testes do budget service (cálculo da sobra mensal)."""
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import DailyExpense, FixedExpense, Income, InvestmentConfig, User
from app.services.budget import compute_month_summary


def _user_id(household):
    return household.users[0].id


def test_sobra_sem_lancamentos(app, household):
    s = compute_month_summary(household.id, 2024, 5)
    assert s.incomes == Decimal("0.00")
    assert s.leftover == Decimal("0.00")


def test_sobra_completa(app, household):
    uid = _user_id(household)
    db.session.add_all([
        Income(household_id=household.id, user_id=uid, description="Salário",
               amount=Decimal("5000"), date=date(2024, 5, 10)),
        FixedExpense(household_id=household.id, name="Aluguel", amount=Decimal("1500"), active=True),
        FixedExpense(household_id=household.id, name="Inativo", amount=Decimal("999"), active=False),
        DailyExpense(household_id=household.id, user_id=uid, description="Mercado",
                     amount=Decimal("800"), date=date(2024, 5, 15)),
        InvestmentConfig(household_id=household.id, percentage=Decimal("10")),
    ])
    db.session.commit()

    s = compute_month_summary(household.id, 2024, 5)
    assert s.incomes == Decimal("5000.00")
    assert s.investment_reserve == Decimal("500.00")   # 10% de 5000
    assert s.fixed_total == Decimal("1500.00")          # ignora o inativo
    assert s.daily_total == Decimal("800.00")
    # 5000 - 500 - 1500 - 800 = 2200
    assert s.leftover == Decimal("2200.00")


def test_filtra_por_mes(app, household):
    uid = _user_id(household)
    db.session.add_all([
        Income(household_id=household.id, user_id=uid, description="Maio",
               amount=Decimal("1000"), date=date(2024, 5, 1)),
        Income(household_id=household.id, user_id=uid, description="Junho",
               amount=Decimal("9999"), date=date(2024, 6, 1)),
    ])
    db.session.commit()
    s = compute_month_summary(household.id, 2024, 5)
    assert s.incomes == Decimal("1000.00")
