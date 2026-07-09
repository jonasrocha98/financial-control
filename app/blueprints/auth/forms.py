from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    ValidationError,
)


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    remember = BooleanField("Manter conectado")
    submit = SubmitField("Entrar")


class RegisterForm(FlaskForm):
    name = StringField("Seu nome", validators=[DataRequired(), Length(max=80)])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        "Confirmar senha", validators=[DataRequired(), EqualTo("password", "As senhas não conferem.")]
    )

    # Modo: criar nova casa OU entrar em uma existente
    household_name = StringField("Nome da casa", validators=[Optional(), Length(max=120)])
    invite_code = StringField("Código de convite", validators=[Optional(), Length(max=12)])
    submit = SubmitField("Criar conta")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if not self.household_name.data and not self.invite_code.data:
            msg = "Informe o nome de uma nova casa OU um código de convite."
            self.household_name.errors.append(msg)
            return False
        return True
