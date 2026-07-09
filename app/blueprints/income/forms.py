from datetime import date

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DecimalField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange


class IncomeForm(FlaskForm):
    description = StringField("Descrição", validators=[DataRequired(), Length(max=120)])
    amount = DecimalField(
        "Valor (R$)", places=2, validators=[DataRequired(), NumberRange(min=0.01)]
    )
    date = DateField("Data", validators=[DataRequired()], default=date.today)
    recurring = BooleanField("Recorrente (todo mês)")
    submit = SubmitField("Salvar")
