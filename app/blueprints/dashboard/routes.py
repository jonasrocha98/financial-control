from decimal import Decimal

from flask import render_template
from flask_login import current_user, login_required
from sqlalchemy import extract, func

from ...extensions import db
from ...models import DailyExpense, FuturePurchase
from ...services.budget import compute_month_summary, current_year_month
from ...services.planner import plan_purchases
from . import bp

MONTH_NAMES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


@bp.route("/")
@login_required
def index():
    year, month = current_year_month()
    summary = compute_month_summary(current_user.household_id, year, month)

    # Gastos do dia a dia por categoria (para gráfico de rosca)
    rows = db.session.execute(
        db.select(
            func.coalesce(DailyExpense.category, "Sem categoria"),
            func.sum(DailyExpense.amount),
        )
        .where(
            DailyExpense.household_id == current_user.household_id,
            extract("year", DailyExpense.date) == year,
            extract("month", DailyExpense.date) == month,
        )
        .group_by(DailyExpense.category)
    ).all()
    category_labels = [r[0] for r in rows]
    category_values = [float(r[1]) for r in rows]

    # Próxima compra recomendada pelo planner
    pending = db.session.scalars(
        db.select(FuturePurchase).where(
            FuturePurchase.household_id == current_user.household_id,
            FuturePurchase.status == "pendente",
        )
    ).all()
    plan = plan_purchases(pending, summary.leftover)
    next_purchase = plan.items[0] if plan.items else None

    # Dados para o gráfico de barras (composição do mês)
    composition = {
        "labels": ["Investir", "Gastos fixos", "Dia a dia", "Sobra"],
        "values": [
            float(summary.investment_reserve),
            float(summary.fixed_total),
            float(summary.daily_total),
            float(max(summary.leftover, Decimal(0))),
        ],
    }

    return render_template(
        "dashboard/index.html",
        summary=summary,
        month_name=MONTH_NAMES_PT[month],
        year=year,
        category_labels=category_labels,
        category_values=category_values,
        composition=composition,
        plan=plan,
        next_purchase=next_purchase,
    )
