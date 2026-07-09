from flask import Blueprint

bp = Blueprint("purchases", __name__, url_prefix="/compras")

from . import routes  # noqa: E402,F401
