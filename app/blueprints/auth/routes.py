from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models import Household, User
from . import bp
from .forms import LoginForm, RegisterForm


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.email == form.email.data.lower().strip()))
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))
        flash("E-mail ou senha inválidos.", "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if db.session.scalar(db.select(User).where(User.email == email)):
            flash("Já existe uma conta com esse e-mail.", "warning")
            return render_template("auth/register.html", form=form)

        # Define o household: entrar em existente (código) ou criar nova casa
        if form.invite_code.data:
            code = form.invite_code.data.strip().upper()
            household = db.session.scalar(
                db.select(Household).where(Household.invite_code == code)
            )
            if not household:
                flash("Código de convite inválido.", "danger")
                return render_template("auth/register.html", form=form)
        else:
            household = Household(name=form.household_name.data.strip())
            db.session.add(household)

        user = User(name=form.name.data.strip(), email=email, household=household)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Não foi possível criar a conta. Tente novamente.", "danger")
            return render_template("auth/register.html", form=form)

        login_user(user)
        flash(f"Bem-vindo(a), {user.name}! Sua casa é \"{household.name}\".", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))
