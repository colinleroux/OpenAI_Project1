from flask import flash, redirect, render_template, request, url_for

from . import settings_bp
from ..extensions import db
from ..models import SavedModel, SavedPrompt
from ..providers import get_provider, list_providers


@settings_bp.route("/")
def index():
    prompts = SavedPrompt.query.order_by(SavedPrompt.title.asc()).all()
    models = SavedModel.query.order_by(SavedModel.provider_key.asc(), SavedModel.name.asc()).all()
    return render_template(
        "settings/index.html",
        prompts=prompts,
        models=models,
        providers=list_providers(),
    )


@settings_bp.post("/prompts")
def add_prompt():
    prompt = SavedPrompt(
        title=request.form["title"].strip(),
        description=request.form.get("description", "").strip(),
        prompt_text=request.form["prompt_text"].strip(),
    )
    db.session.add(prompt)
    db.session.commit()
    return redirect(url_for("settings.index"))


@settings_bp.post("/prompts/<int:prompt_id>")
def update_prompt(prompt_id):
    prompt = SavedPrompt.query.get_or_404(prompt_id)
    prompt.title = request.form["title"].strip()
    prompt.description = request.form.get("description", "").strip()
    prompt.prompt_text = request.form["prompt_text"].strip()
    db.session.commit()
    return redirect(url_for("settings.index"))


@settings_bp.post("/prompts/<int:prompt_id>/delete")
def delete_prompt(prompt_id):
    prompt = SavedPrompt.query.get_or_404(prompt_id)
    db.session.delete(prompt)
    db.session.commit()
    return redirect(url_for("settings.index"))


@settings_bp.post("/models")
def add_model():
    provider_key = request.form["provider_key"].strip()
    provider = get_provider(provider_key)
    if provider is None:
        flash("Choose a valid provider before saving a model.")
        return redirect(url_for("settings.index"))

    name = request.form["name"].strip()
    if SavedModel.query.filter_by(provider_key=provider_key, name=name).first():
        flash(f"{provider.name} model {name} already exists.")
        return redirect(url_for("settings.index"))

    model = SavedModel(
        provider_key=provider_key,
        name=name,
        description=request.form.get("description", "").strip(),
    )
    db.session.add(model)
    db.session.commit()
    return redirect(url_for("settings.index"))


@settings_bp.post("/models/<int:model_id>")
def update_model(model_id):
    model = SavedModel.query.get_or_404(model_id)
    provider_key = request.form["provider_key"].strip()
    provider = get_provider(provider_key)
    if provider is None:
        flash("Choose a valid provider before saving a model.")
        return redirect(url_for("settings.index"))

    name = request.form["name"].strip()
    existing = SavedModel.query.filter(
        SavedModel.provider_key == provider_key,
        SavedModel.name == name,
        SavedModel.id != model.id,
    ).first()
    if existing:
        flash(f"{provider.name} model {name} already exists.")
        return redirect(url_for("settings.index"))

    model.provider_key = provider_key
    model.name = name
    model.description = request.form.get("description", "").strip()
    db.session.commit()
    return redirect(url_for("settings.index"))


@settings_bp.post("/models/<int:model_id>/delete")
def delete_model(model_id):
    from ..models import ProviderConfig

    model = SavedModel.query.get_or_404(model_id)
    ProviderConfig.query.filter_by(default_model_id=model.id).update({"default_model_id": None})
    db.session.delete(model)
    db.session.commit()
    return redirect(url_for("settings.index"))
