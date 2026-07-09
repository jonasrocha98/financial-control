from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class FixedExpenseForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    amount = DecimalField("Valor (R$)", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    due_day = IntegerField("Dia do vencimento", validators=[Optional(), NumberRange(min=1, max=31)])
    category = StringField("Categoria", validators=[Optional(), Length(max=60)])
    active = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar")


class DailyExpenseForm(FlaskForm):
    description = StringField("Descrição", validators=[DataRequired(), Length(max=120)])
    amount = DecimalField("Valor (R$)", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField("Data", validators=[DataRequired()], default=date.today)
    category = StringField("Categoria", validators=[Optional(), Length(max=60)])
    submit = SubmitField("Salvar")
