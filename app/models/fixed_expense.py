"""FixedExpense: gastos fixos mensais (aluguel, internet, etc.)."""
from datetime import date

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

    # Vigência. Sem isto, cancelar um gasto fixo hoje o apagaria retroativamente
    # de todos os meses passados, corrompendo o histórico.
    # NULL = vale desde sempre / para sempre.
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    household = db.relationship("Household", back_populates="fixed_expenses")

    def vigente_em(self, primeiro_dia: date, ultimo_dia: date) -> bool:
        """O gasto vale em algum ponto do mês [primeiro_dia, ultimo_dia]?"""
        if not self.active:
            return False
        if self.start_date and self.start_date > ultimo_dia:
            return False
        if self.end_date and self.end_date < primeiro_dia:
            return False
        return True

    def __repr__(self):
        return f"<FixedExpense {self.name!r} {self.amount}>"
