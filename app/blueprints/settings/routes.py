from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ...extensions import db
from ...models import Household, InvestmentConfig
from . import bp
from .forms import HouseholdForm, InvestmentForm


def _get_or_create_config() -> InvestmentConfig:
    config = db.session.scalar(
        db.select(InvestmentConfig).where(InvestmentConfig.household_id == current_user.household_id)
    )
    if config is None:
        config = InvestmentConfig(household_id=current_user.household_id, percentage=0)
        db.session.add(config)
        db.session.commit()
    return config


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    config = _get_or_create_config()
    household = db.get_or_404(Household, current_user.household_id)

    inv_form = InvestmentForm(prefix="inv", obj=config)
    house_form = HouseholdForm(prefix="house", obj=household)

    if inv_form.submit.data and inv_form.validate_on_submit():
        config.percentage = inv_form.percentage.data
        db.session.commit()
        flash("Percentual de investimento atualizado.", "success")
        return redirect(url_for("settings.index"))

    if house_form.submit.data and house_form.validate_on_submit():
        household.name = house_form.name.data.strip()
        db.session.commit()
        flash("Nome da casa atualizado.", "success")
        return redirect(url_for("settings.index"))

    members = household.users
    return render_template(
        "settings/index.html",
        inv_form=inv_form,
        house_form=house_form,
        household=household,
        members=members,
    )
