from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

PRIORITY_CHOICES = [
    (1, "1 - Urgente"),
    (2, "2 - Alta"),
    (3, "3 - Média"),
    (4, "4 - Baixa"),
    (5, "5 - Algum dia"),
]

PARCELA_CHOICES = [(1, "À vista")] + [(n, f"{n}x no cartão") for n in range(2, 25)]


class FuturePurchaseForm(FlaskForm):
    name = StringField("O que comprar", validators=[DataRequired(), Length(max=120)])
    estimated_cost = DecimalField(
        "Custo total (R$)", places=2, validators=[DataRequired(), NumberRange(min=0.01)]
    )
    installments = SelectField("Como vai pagar", coerce=int, choices=PARCELA_CHOICES, default=1)
    priority = SelectField("Prioridade", coerce=int, choices=PRIORITY_CHOICES, default=3)
    target_date = DateField("Quero comprar até", validators=[Optional()])
    submit = SubmitField("Salvar")
