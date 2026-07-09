"""Modelos de dados. Importa tudo para o Alembic detectar."""
from .household import Household
from .user import User
from .income import Income
from .fixed_expense import FixedExpense
from .daily_expense import DailyExpense
from .investment_config import InvestmentConfig
from .future_purchase import FuturePurchase

__all__ = [
    "Household",
    "User",
    "Income",
    "FixedExpense",
    "DailyExpense",
    "InvestmentConfig",
    "FuturePurchase",
]
