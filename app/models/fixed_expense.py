"""FixedExpense: gastos fixos mensais (aluguel, internet, etc.)."""
from ..extensions import db


class FixedExpense(db.Model):
    __tablename__ = "fixed_expenses"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_day = db.Column(db.Integer, nullable=True)  # dia do vencimento (1-31)
    category = db.Column(db.String(60), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    household = db.relationship("Household", back_populates="fixed_expenses")

    def __repr__(self):
        return f"<FixedExpense {self.name!r} {self.amount}>"
