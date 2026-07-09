from flask import Blueprint

bp = Blueprint("income", __name__, url_prefix="/entradas")

from . import routes  # noqa: E402,F401
