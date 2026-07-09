"""Income: entradas de dinheiro (salário, freelas, etc.)."""
from datetime import date

from ..extensions import db


class Income(db.Model):
    __tablename__ = "incomes"

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey("households.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    recurring = db.Column(db.Boolean, nullable=False, default=False)

    household = db.relationship("Household", back_populates="incomes")
    user = db.relationship("User")

    def __repr__(self):
        return f"<Income {self.description!r} {self.amount}>"
