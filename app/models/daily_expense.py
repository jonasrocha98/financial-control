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

    # 'conta' ou 'cartao'. Um gasto no cartão sai do bolso só no mês seguinte;
    # sem isto não dá para calcular o caixa disponível hoje.
    source = db.Column(db.String(10), nullable=True)

    # "8/12" quando o gasto é parcela. Parcelas terminam; gasto recorrente não.
    # Separá-las é o que torna o custo de vida honesto.
    installment_info = db.Column(db.String(10), nullable=True)

    @property
    def is_installment(self) -> bool:
        return bool(self.installment_info)

    household = db.relationship("Household", back_populates="daily_expenses")
    user = db.relationship("User")

    def __repr__(self):
        return f"<DailyExpense {self.description!r} {self.amount}>"
