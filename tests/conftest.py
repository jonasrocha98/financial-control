"""Fixtures de teste: app Flask com banco SQLite em memória."""
import pytest

from app import create_app
from app.extensions import db as _db
from app.models import (
    DailyExpense,
    FixedExpense,
    Household,
    Income,
    InvestmentConfig,
    User,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def household(app):
    h = Household(name="Casa Teste", invite_code="TEST01")
    u = User(name="Jonas", email="j@test.com", household=h)
    u.set_password("123456")
    _db.session.add_all([h, u])
    _db.session.commit()
    return h
