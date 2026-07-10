"""Installment: compra parcelada em andamento.

ATENÇÃO — este modelo NÃO entra na soma de gastos. Cada parcela já existe como
um DailyExpense no mês em que cai. Ele serve para projetar o futuro: saber
quanto está comprometido e em que mês cada compra libera fôlego no orçamento.
"""
from decimal import Decimal

from ..extensions import db


class Installment(db.Model):
    __tablename__ = "installments"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)       # valor de UMA parcela
    total_installments = db.Column(db.Integer, nullable=False)   # ex: 12
    current_installment = db.Column(db.Integer, nullable=False)  # ex: 8
    # mês a que 'current_installment' se refere (dia 1)
    reference_month = db.Column(db.Date, nullable=False)

    # Origem, quando veio de uma compra futura marcada como comprada. NULL para
    # as parcelas reconstruídas do extrato. Casar por nome seria frágil.
    purchase_id = db.Column(db.Integer, db.ForeignKey("future_purchases.id"), nullable=True)

    household = db.relationship("Household", back_populates="installments")

    @property
    def remaining(self) -> int:
        """Quantas parcelas ainda faltam depois do mês de referência."""
        return max(self.total_installments - self.current_installment, 0)

    @property
    def total_remaining(self) -> Decimal:
        """Quanto ainda será pago por esta compra."""
        return Decimal(str(self.amount)) * self.remaining

    @property
    def finished(self) -> bool:
        return self.remaining == 0

    def __repr__(self):
        return f"<Installment {self.name!r} {self.current_installment}/{self.total_installments}>"
