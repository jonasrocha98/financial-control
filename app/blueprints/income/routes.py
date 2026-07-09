from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ...extensions import db
from ...models import Income
from . import bp
from .forms import IncomeForm


def _get_owned_or_404(income_id: int) -> Income:
    income = db.get_or_404(Income, income_id)
    if income.household_id != current_user.household_id:
        from flask import abort

        abort(404)
    return income


@bp.route("/")
@login_required
def index():
    incomes = db.session.scalars(
        db.select(Income)
        .where(Income.household_id == current_user.household_id)
        .order_by(Income.date.desc(), Income.id.desc())
    ).all()
    total = sum((i.amount for i in incomes), start=0)
    return render_template("income/index.html", incomes=incomes, total=total)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def create():
    form = IncomeForm()
    if form.validate_on_submit():
        income = Income(
            household_id=current_user.household_id,
            user_id=current_user.id,
            description=form.description.data.strip(),
            amount=form.amount.data,
            date=form.date.data,
            recurring=form.recurring.data,
        )
        db.session.add(income)
        db.session.commit()
        flash("Entrada adicionada.", "success")
        return redirect(url_for("income.index"))
    return render_template("income/form.html", form=form, title="Nova entrada")


@bp.route("/<int:income_id>/editar", methods=["GET", "POST"])
@login_required
def edit(income_id):
    income = _get_owned_or_404(income_id)
    form = IncomeForm(obj=income)
    if form.validate_on_submit():
        income.description = form.description.data.strip()
        income.amount = form.amount.data
        income.date = form.date.data
        income.recurring = form.recurring.data
        db.session.commit()
        flash("Entrada atualizada.", "success")
        return redirect(url_for("income.index"))
    return render_template("income/form.html", form=form, title="Editar entrada")


@bp.route("/<int:income_id>/excluir", methods=["POST"])
@login_required
def delete(income_id):
    income = _get_owned_or_404(income_id)
    db.session.delete(income)
    db.session.commit()
    flash("Entrada removida.", "info")
    return redirect(url_for("income.index"))
