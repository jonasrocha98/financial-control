"""FuturePurchase: compras futuras ordenadas por prioridade."""
from datetime import datetime

from ..extensions import db


class FuturePurchase(db.Model):
    __tablename__ = "future_purchases"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    estimated_cost = db.Column(db.Numeric(12, 2), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=3)  # 1 = mais prioritário
    target_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pendente")  # pendente | comprado
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    household = db.relationship("Household", back_populates="purchases")

    def __repr__(self):
        return f"<FuturePurchase {self.name!r} prio={self.priority}>"
