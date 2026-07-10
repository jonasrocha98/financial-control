"""Servidor de demonstração: SQLite temporário com dados sintéticos.

Serve para inspecionar o visual sem tocar no banco real nem expor dados
pessoais. Login: demo@demo.com / demo123

  python scripts/preview_demo.py
"""
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

# ANTES de importar config: força SQLite e desliga o .env de produção.
RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / "demo.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["SECRET_KEY"] = "demo-nao-use-em-producao"
os.environ["FLASK_ENV"] = "development"

import sys  # noqa: E402

sys.path.insert(0, str(RAIZ))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    DailyExpense,
    FixedExpense,
    Household,
    Income,
    Installment,
    User,
)


def seed():
    casa = Household(name="Casa Demo", invite_code="DEMO01")
    u = User(name="Ana Demo", email="demo@demo.com", household=casa)
    u.set_password("demo123")
    db.session.add_all([casa, u])
    db.session.commit()

    db.session.add_all([
        FixedExpense(household_id=casa.id, name="Aluguel", amount=Decimal("604")),
        FixedExpense(household_id=casa.id, name="Aula de música", amount=Decimal("140")),
        FixedExpense(household_id=casa.id, name="Internet", amount=Decimal("90")),
        FixedExpense(household_id=casa.id, name="Energia", amount=Decimal("50")),
        FixedExpense(household_id=casa.id, name="Gás", amount=Decimal("50")),
        FixedExpense(household_id=casa.id, name="Streaming", amount=Decimal("35")),
        FixedExpense(household_id=casa.id, name="Telefone", amount=Decimal("39")),
    ])

    hoje = date.today()
    # 6 meses fechados + o mês corrente pela metade
    for i in range(6, 0, -1):
        m = hoje.month - i
        ano = hoje.year + (m - 1) // 12
        mes = (m - 1) % 12 + 1
        db.session.add(Income(household_id=casa.id, user_id=u.id, description="Salário",
                              amount=Decimal("3077.59"), date=date(ano, mes, 7), recurring=True))
        if i in (4, 3, 1):
            db.session.add(Income(household_id=casa.id, user_id=u.id, description="Venda de eletrônicos",
                                  amount=Decimal(["500.00", "150.00", "120.00"][i % 3]),
                                  date=date(ano, mes, 15), recurring=False))
        for dia, val, cat, src in [(5, "820.40", "Mercado", "cartao"),
                                   (11, "310.15", "Compras online", "cartao"),
                                   (16, "180.00", "Farmácia", "cartao"),
                                   (21, "240.75", "Alimentação fora", "cartao"),
                                   (24, "1065.00", "Mercado", "cartao"),
                                   (26, "120.00", "Transporte", "conta")]:
            db.session.add(DailyExpense(household_id=casa.id, user_id=u.id, description=cat,
                                        amount=Decimal(val), date=date(ano, mes, dia),
                                        category=cat, source=src))
        for nome, val in [("Óticas", "100.50"), ("Notebook", "47.93")]:
            db.session.add(DailyExpense(household_id=casa.id, user_id=u.id, description=nome,
                                        amount=Decimal(val), date=date(ano, mes, 5),
                                        category="Compras", source="cartao",
                                        installment_info=f"{7 - i}/12"))

    # mês corrente: só o começo
    db.session.add(Income(household_id=casa.id, user_id=u.id, description="Salário",
                          amount=Decimal("3048.47"), date=date(hoje.year, hoje.month, 7),
                          recurring=True))
    db.session.add(DailyExpense(household_id=casa.id, user_id=u.id, description="Mercado",
                                amount=Decimal("793.60"), date=date(hoje.year, hoje.month, min(hoje.day, 9)),
                                category="Mercado", source="cartao"))

    ref = date(hoje.year, hoje.month, 1)
    db.session.add_all([
        Installment(household_id=casa.id, name="Óticas", amount=Decimal("100.50"),
                    total_installments=10, current_installment=7, reference_month=ref),
        Installment(household_id=casa.id, name="Notebook", amount=Decimal("47.93"),
                    total_installments=12, current_installment=8, reference_month=ref),
        Installment(household_id=casa.id, name="Fone", amount=Decimal("58.15"),
                    total_installments=6, current_installment=5, reference_month=ref),
        Installment(household_id=casa.id, name="Cadeira", amount=Decimal("37.50"),
                    total_installments=6, current_installment=5, reference_month=ref),
    ])
    db.session.commit()


if __name__ == "__main__":
    if DB.exists():
        DB.unlink()
    app = create_app()
    with app.app_context():
        db.create_all()
        seed()
    print("demo pronto -> demo@demo.com / demo123", flush=True)
    app.run(port=5002, debug=False)
