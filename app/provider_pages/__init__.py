from flask import Blueprint

provider_bp = Blueprint("provider", __name__, url_prefix="/providers")

from . import routes  # noqa: E402,F401
