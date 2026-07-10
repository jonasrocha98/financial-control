"""Household: container compartilhado do orçamento da casa."""
import secrets

from ..extensions import db


def generate_invite_code() -> str:
    """Código de convite curto e legível (ex: 'A3F9K2')."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem caracteres ambíguos
    return "".join(secrets.choice(alphabet) for _ in range(6))


class Household(db.Model):
    __tablename__ = "households"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    invite_code = db.Column(db.String(12), unique=True, nullable=False, default=generate_invite_code)

    # Relacionamentos (cascade: apagar a casa apaga tudo dela)
    users = db.relationship("User", back_populates="household", cascade="all, delete-orphan")
    incomes = db.relationship("Income", back_populates="household", cascade="all, delete-orphan")
    fixed_expenses = db.relationship("FixedExpense", back_populates="household", cascade="all, delete-orphan")
    daily_expenses = db.relationship("DailyExpense", back_populates="household", cascade="all, delete-orphan")
    purchases = db.relationship("FuturePurchase", back_populates="household", cascade="all, delete-orphan")
    installments = db.relationship("Installment", back_populates="household", cascade="all, delete-orphan")
    investment_config = db.relationship(
        "InvestmentConfig", back_populates="household", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Household {self.name!r}>"
