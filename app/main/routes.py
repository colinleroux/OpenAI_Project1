from flask import Blueprint, render_template

from ..models import SavedModel, SavedPrompt
from ..providers import list_providers

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    prompt_count = SavedPrompt.query.count()
    model_count = SavedModel.query.count()
    return render_template(
        "home.html",
        providers=list_providers(),
        prompt_count=prompt_count,
        model_count=model_count,
    )
