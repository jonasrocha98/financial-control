"""InvestmentConfig: % das entradas a separar para investimento (um por household)."""
from ..extensions import db


class InvestmentConfig(db.Model):
    __tablename__ = "investment_configs"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(
        db.Integer, db.ForeignKey("households.id"), nullable=False, unique=True, index=True
    )
    percentage = db.Column(db.Numeric(5, 2), nullable=False, default=0)  # 0 a 100

    household = db.relationship("Household", back_populates="investment_config")

    def __repr__(self):
        return f"<InvestmentConfig {self.percentage}%>"
