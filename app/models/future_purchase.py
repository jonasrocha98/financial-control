"""FuturePurchase: compras futuras ordenadas por prioridade."""
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from ..extensions import db


class FuturePurchase(db.Model):
    __tablename__ = "future_purchases"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    estimated_cost = db.Column(db.Numeric(12, 2), nullable=False)  # valor TOTAL da compra
    priority = db.Column(db.Integer, nullable=False, default=3)  # 1 = mais prioritário
    target_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pendente")  # pendente | comprado
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # 1 = à vista. Acima disso é parcelado no cartão: o que pesa no orçamento
    # de cada mês é a parcela, não o valor total.
    installments = db.Column(db.Integer, nullable=False, default=1)

    household = db.relationship("Household", back_populates="purchases")

    @property
    def is_installment(self) -> bool:
        return (self.installments or 1) > 1

    @property
    def monthly_cost(self) -> Decimal:
        """Quanto esta compra tira da sobra POR MÊS."""
        n = self.installments or 1
        total = Decimal(str(self.estimated_cost))
        return (total / n).quantize(Decimal("0.01"), ROUND_HALF_UP)

    def __repr__(self):
        return f"<FuturePurchase {self.name!r} prio={self.priority} {self.installments}x>"
