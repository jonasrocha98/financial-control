"""DailyExpense: gastos do dia a dia (mercado, transporte, lazer, etc.)."""
from datetime import date

from ..extensions import db


class DailyExpense(db.Model):
    __tablename__ = "daily_expenses"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(60), nullable=True)

    household = db.relationship("Household", back_populates="daily_expenses")
    user = db.relationship("User")

    def __repr__(self):
        return f"<DailyExpense {self.description!r} {self.amount}>"
