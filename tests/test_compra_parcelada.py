"""Comprar parcelado vira um compromisso mensal de verdade."""
from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import FuturePurchase, Installment
from app.services.installments import projetar


@pytest.fixture()
def client(app, household):
    c = app.test_client()
    with c.session_transaction() as s:
        s["_user_id"] = str(household.users[0].id)
        s["_fresh"] = True
    return c


def _compra(household, **kw):
    p = FuturePurchase(household_id=household.id, name=kw.pop("name", "Notebook"),
                       estimated_cost=Decimal(kw.pop("cost", "3000")),
                       priority=1, **kw)
    db.session.add(p)
    db.session.commit()
    return p


def test_comprar_a_vista_nao_cria_parcela(client, household):
    p = _compra(household, installments=1)
    client.post(f"/compras/{p.id}/comprado")
    assert db.session.get(FuturePurchase, p.id).status == "comprado"
    assert projetar(household.id).ativas == []


def test_comprar_parcelado_cria_a_parcela(client, household):
    p = _compra(household, installments=10)
    client.post(f"/compras/{p.id}/comprado")

    parcelas = db.session.scalars(db.select(Installment)).all()
    assert len(parcelas) == 1
    i = parcelas[0]
    assert i.name == "Notebook"
    assert i.amount == Decimal("300.00")       # 3000 / 10
    assert i.total_installments == 10
    assert i.current_installment == 1
    assert i.remaining == 9


def test_parcela_comprada_entra_na_projecao_de_alivio(client, household):
    p = _compra(household, installments=10)
    client.post(f"/compras/{p.id}/comprado")

    proj = projetar(household.id)
    assert proj.comprometido_mensal == Decimal("300.00")
    assert proj.divida_restante == Decimal("2700.00")   # 9 parcelas restantes
    assert len(proj.alivios) == 1
    assert proj.alivios[0].meses_ate_la == 9
    assert proj.alivios[0].valor_liberado == Decimal("300.00")


def test_reabrir_nao_duplica_a_parcela(client, household):
    """Comprou, reabriu, comprou de novo: não pode virar duas parcelas."""
    p = _compra(household, installments=6)
    client.post(f"/compras/{p.id}/comprado")
    client.post(f"/compras/{p.id}/reabrir")
    client.post(f"/compras/{p.id}/comprado")

    assert len(db.session.scalars(db.select(Installment)).all()) == 1


def test_reabrir_cancela_o_compromisso(client, household):
    p = _compra(household, installments=6)
    client.post(f"/compras/{p.id}/comprado")
    assert projetar(household.id).comprometido_mensal == Decimal("500.00")

    client.post(f"/compras/{p.id}/reabrir")
    assert projetar(household.id).ativas == []


def test_excluir_compra_nao_deixa_parcela_orfa(client, household):
    p = _compra(household, installments=6)
    client.post(f"/compras/{p.id}/comprado")
    client.post(f"/compras/{p.id}/excluir")

    assert db.session.scalars(db.select(Installment)).all() == []
    assert db.session.get(FuturePurchase, p.id) is None
