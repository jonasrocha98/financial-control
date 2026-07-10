from flask import Blueprint

bp = Blueprint("target", __name__, url_prefix="/faturar")

from . import routes  # noqa: E402,F401
