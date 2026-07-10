"""Vigência dos gastos fixos: cancelar um fixo não pode reescrever o passado."""
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import FixedExpense
from app.services.budget import compute_month_summary


def _fixo(household, **kw):
    f = FixedExpense(household_id=household.id, name=kw.pop("name", "Aluguel"),
                     amount=Decimal(kw.pop("amount", "600")), active=kw.pop("active", True), **kw)
    db.session.add(f)
    db.session.commit()
    return f


def test_sem_datas_vale_em_todo_mes(app, household):
    _fixo(household)
    for mes in (1, 6, 12):
        assert compute_month_summary(household.id, 2026, mes).fixed_total == Decimal("600.00")


def test_encerrado_nao_conta_depois_do_fim(app, household):
    _fixo(household, end_date=date(2026, 6, 30))
    assert compute_month_summary(household.id, 2026, 6).fixed_total == Decimal("600.00")
    assert compute_month_summary(household.id, 2026, 7).fixed_total == Decimal("0.00")


def test_encerrado_continua_valendo_no_passado(app, household):
    """O bug que a vigência existe para evitar."""
    _fixo(household, end_date=date(2026, 6, 30))
    # junho e antes seguem intactos
    assert compute_month_summary(household.id, 2026, 1).fixed_total == Decimal("600.00")
    assert compute_month_summary(household.id, 2026, 5).fixed_total == Decimal("600.00")


def test_iniciado_no_meio_nao_conta_antes(app, household):
    _fixo(household, start_date=date(2026, 4, 1))
    assert compute_month_summary(household.id, 2026, 3).fixed_total == Decimal("0.00")
    assert compute_month_summary(household.id, 2026, 4).fixed_total == Decimal("600.00")


def test_vigencia_parcial_dentro_do_mes_conta(app, household):
    """Começou dia 20; o mês inteiro conta (é um custo mensal, não diário)."""
    _fixo(household, start_date=date(2026, 4, 20))
    assert compute_month_summary(household.id, 2026, 4).fixed_total == Decimal("600.00")


def test_inativo_nunca_conta(app, household):
    _fixo(household, active=False)
    assert compute_month_summary(household.id, 2026, 4).fixed_total == Decimal("0.00")


def test_dois_fixos_com_vigencias_diferentes(app, household):
    _fixo(household, name="Antigo", amount="100", end_date=date(2026, 3, 31))
    _fixo(household, name="Novo", amount="250", start_date=date(2026, 4, 1))
    assert compute_month_summary(household.id, 2026, 3).fixed_total == Decimal("100.00")
    assert compute_month_summary(household.id, 2026, 4).fixed_total == Decimal("250.00")
