from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from datetime import date

from ...extensions import db
from ...models import FuturePurchase, Installment
from ...services.budget import compute_month_summary, current_year_month
from ...services.planner import plan_purchases
from . import bp
from .forms import FuturePurchaseForm


def _owned(purchase_id):
    obj = db.get_or_404(FuturePurchase, purchase_id)
    if obj.household_id != current_user.household_id:
        abort(404)
    return obj


@bp.route("/")
@login_required
def index():
    """Tela auto-organizada: calcula a sobra do mês e aloca as compras por prioridade."""
    year, month = current_year_month()
    summary = compute_month_summary(current_user.household_id, year, month)

    pending = db.session.scalars(
        db.select(FuturePurchase).where(
            FuturePurchase.household_id == current_user.household_id,
            FuturePurchase.status == "pendente",
        )
    ).all()
    plan = plan_purchases(pending, summary.leftover)

    bought = db.session.scalars(
        db.select(FuturePurchase)
        .where(
            FuturePurchase.household_id == current_user.household_id,
            FuturePurchase.status == "comprado",
        )
        .order_by(FuturePurchase.created_at.desc())
    ).all()

    return render_template("purchases/index.html", summary=summary, plan=plan, bought=bought)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def create():
    form = FuturePurchaseForm()
    if form.validate_on_submit():
        db.session.add(
            FuturePurchase(
                household_id=current_user.household_id,
                name=form.name.data.strip(),
                estimated_cost=form.estimated_cost.data,
                installments=form.installments.data,
                priority=form.priority.data,
                target_date=form.target_date.data,
            )
        )
        db.session.commit()
        flash("Compra adicionada à lista.", "success")
        return redirect(url_for("purchases.index"))
    return render_template("purchases/form.html", form=form, title="Nova compra futura")


@bp.route("/<int:purchase_id>/editar", methods=["GET", "POST"])
@login_required
def edit(purchase_id):
    item = _owned(purchase_id)
    form = FuturePurchaseForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        item.estimated_cost = form.estimated_cost.data
        item.installments = form.installments.data
        item.priority = form.priority.data
        item.target_date = form.target_date.data
        db.session.commit()
        flash("Compra atualizada.", "success")
        return redirect(url_for("purchases.index"))
    return render_template("purchases/form.html", form=form, title="Editar compra")


@bp.route("/<int:purchase_id>/comprado", methods=["POST"])
@login_required
def mark_bought(purchase_id):
    item = _owned(purchase_id)
    item.status = "comprado"

    # Comprou parcelado? Vira um compromisso mensal de verdade, e a projeção
    # de alívio passa a saber quando ele termina. Marcar duas vezes não duplica.
    ja_existe = db.session.scalar(
        db.select(Installment).where(Installment.purchase_id == item.id))
    if item.is_installment and not ja_existe:
        hoje = date.today()
        db.session.add(Installment(
            household_id=item.household_id,
            purchase_id=item.id,
            name=item.name,
            amount=item.monthly_cost,
            total_installments=item.installments,
            current_installment=1,
            reference_month=date(hoje.year, hoje.month, 1),
        ))
        flash(f'"{item.name}" comprada em {item.installments}x de '
              f'{item.monthly_cost} — já entrou nas suas parcelas.', "success")
    else:
        flash(f'"{item.name}" marcada como comprada. 🎉', "success")

    db.session.commit()
    return redirect(url_for("purchases.index"))


def _remove_parcela_da_compra(purchase_id: int) -> None:
    """Se a compra gerou uma parcela, ela morre junto — não é mais um compromisso."""
    parcela = db.session.scalar(
        db.select(Installment).where(Installment.purchase_id == purchase_id))
    if parcela:
        db.session.delete(parcela)


@bp.route("/<int:purchase_id>/reabrir", methods=["POST"])
@login_required
def reopen(purchase_id):
    item = _owned(purchase_id)
    item.status = "pendente"
    _remove_parcela_da_compra(item.id)
    db.session.commit()
    flash("Compra voltou para a lista.", "info")
    return redirect(url_for("purchases.index"))


@bp.route("/<int:purchase_id>/excluir", methods=["POST"])
@login_required
def delete(purchase_id):
    item = _owned(purchase_id)
    # sem isto a parcela ficaria apontando para uma compra inexistente (FK)
    _remove_parcela_da_compra(item.id)
    db.session.delete(item)
    db.session.commit()
    flash("Compra removida.", "info")
    return redirect(url_for("purchases.index"))
