"""DailyExpense: gastos do dia a dia (mercado, transporte, lazer, etc.)."""
from datetime import date

from ..extensions import db


class DailyExpense(db.Model):
    __tablename__ = "daily_expenses"
    __table_args__ = (
        # Torna a importação de extrato idempotente: reimportar não duplica.
        # NULL para lançamentos manuais (no Postgres NULLs não colidem entre si).
        db.UniqueConstraint("household_id", "external_key", name="uq_daily_expense_external_key"),
    )

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(60), nullable=True)

    # Hash de (conta, fitid, data, memo, valor). O FITID sozinho NÃO serve:
    # o Nubank reaproveita o mesmo FITID entre parcelas de meses diferentes.
    external_key = db.Column(db.String(64), nullable=True)

    household = db.relationship("Household", back_populates="daily_expenses")
    user = db.relationship("User")

    def __repr__(self):
        return f"<DailyExpense {self.description!r} {self.amount}>"
