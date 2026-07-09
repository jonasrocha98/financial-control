from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange


class InvestmentForm(FlaskForm):
    percentage = DecimalField(
        "% das entradas para investir",
        places=2,
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    submit = SubmitField("Salvar")


class HouseholdForm(FlaskForm):
    name = StringField("Nome da casa", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Salvar")
