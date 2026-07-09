from datetime import date

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import extract

from ...extensions import db
from ...models import DailyExpense, FixedExpense
from ...services.budget import current_year_month
from . import bp
from .forms import DailyExpenseForm, FixedExpenseForm


def _owned(model, obj_id):
    obj = db.get_or_404(model, obj_id)
    if obj.household_id != current_user.household_id:
        abort(404)
    return obj


# ---------------------------------------------------------------- Gastos fixos
@bp.route("/fixos")
@login_required
def fixed_index():
    items = db.session.scalars(
        db.select(FixedExpense)
        .where(FixedExpense.household_id == current_user.household_id)
        .order_by(FixedExpense.active.desc(), FixedExpense.name)
    ).all()
    total = sum((e.amount for e in items if e.active), start=0)
    return render_template("expenses/fixed_index.html", items=items, total=total)


@bp.route("/fixos/novo", methods=["GET", "POST"])
@login_required
def fixed_create():
    form = FixedExpenseForm()
    if form.validate_on_submit():
        db.session.add(
            FixedExpense(
                household_id=current_user.household_id,
                name=form.name.data.strip(),
                amount=form.amount.data,
                due_day=form.due_day.data,
                category=(form.category.data or "").strip() or None,
                active=form.active.data,
            )
        )
        db.session.commit()
        flash("Gasto fixo adicionado.", "success")
        return redirect(url_for("expenses.fixed_index"))
    return render_template("expenses/fixed_form.html", form=form, title="Novo gasto fixo")


@bp.route("/fixos/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def fixed_edit(item_id):
    item = _owned(FixedExpense, item_id)
    form = FixedExpenseForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        item.amount = form.amount.data
        item.due_day = form.due_day.data
        item.category = (form.category.data or "").strip() or None
        item.active = form.active.data
        db.session.commit()
        flash("Gasto fixo atualizado.", "success")
        return redirect(url_for("expenses.fixed_index"))
    return render_template("expenses/fixed_form.html", form=form, title="Editar gasto fixo")


@bp.route("/fixos/<int:item_id>/excluir", methods=["POST"])
@login_required
def fixed_delete(item_id):
    item = _owned(FixedExpense, item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Gasto fixo removido.", "info")
    return redirect(url_for("expenses.fixed_index"))


# ------------------------------------------------------------ Gastos do dia a dia
@bp.route("/diario")
@login_required
def daily_index():
    year, month = current_year_month()
    items = db.session.scalars(
        db.select(DailyExpense)
        .where(
            DailyExpense.household_id == current_user.household_id,
            extract("year", DailyExpense.date) == year,
            extract("month", DailyExpense.date) == month,
        )
        .order_by(DailyExpense.date.desc(), DailyExpense.id.desc())
    ).all()
    total = sum((e.amount for e in items), start=0)
    return render_template("expenses/daily_index.html", items=items, total=total, year=year, month=month)


@bp.route("/diario/novo", methods=["GET", "POST"])
@login_required
def daily_create():
    form = DailyExpenseForm()
    if form.validate_on_submit():
        db.session.add(
            DailyExpense(
                household_id=current_user.household_id,
                user_id=current_user.id,
                description=form.description.data.strip(),
                amount=form.amount.data,
                date=form.date.data,
                category=(form.category.data or "").strip() or None,
            )
        )
        db.session.commit()
        flash("Gasto registrado.", "success")
        return redirect(url_for("expenses.daily_index"))
    return render_template("expenses/daily_form.html", form=form, title="Novo gasto")


@bp.route("/diario/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def daily_edit(item_id):
    item = _owned(DailyExpense, item_id)
    form = DailyExpenseForm(obj=item)
    if form.validate_on_submit():
        item.description = form.description.data.strip()
        item.amount = form.amount.data
        item.date = form.date.data
        item.category = (form.category.data or "").strip() or None
        db.session.commit()
        flash("Gasto atualizado.", "success")
        return redirect(url_for("expenses.daily_index"))
    return render_template("expenses/daily_form.html", form=form, title="Editar gasto")


@bp.route("/diario/<int:item_id>/excluir", methods=["POST"])
@login_required
def daily_delete(item_id):
    item = _owned(DailyExpense, item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Gasto removido.", "info")
    return redirect(url_for("expenses.daily_index"))
