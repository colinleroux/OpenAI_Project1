from flask import flash, redirect, render_template, request, url_for

from . import provider_bp
from ..extensions import db
from ..models import ProviderConfig, SavedModel, SavedPrompt
from ..providers import get_provider, list_providers
from ..services.llm import LlmRequest, ProviderNotReadyError, send_llm_request


def _get_or_create_config(provider_key: str):
    config = ProviderConfig.query.filter_by(provider_key=provider_key).first()
    if config:
        return config

    config = ProviderConfig(provider_key=provider_key)
    db.session.add(config)
    db.session.commit()
    return config


def _render_provider(provider_key: str, **overrides):
    provider = get_provider(provider_key)
    if provider is None:
        return redirect(url_for("main.home"))

    config = _get_or_create_config(provider_key)
    prompts = SavedPrompt.query.order_by(SavedPrompt.title.asc()).all()
    models = SavedModel.query.filter_by(provider_key=provider_key).order_by(SavedModel.name.asc()).all()
    if config.default_model and config.default_model.provider_key != provider_key:
        config.default_model_id = None
        db.session.commit()

    context = {
        "provider": provider,
        "providers": list_providers(),
        "config": config,
        "prompts": prompts,
        "models": models,
        "active_tab": request.args.get("tab", "playground"),
        "selected_prompt_id": None,
        "selected_model_id": config.default_model_id,
        "user_text": "",
        "response_text": "",
        "response_id": "",
    }
    context.update(overrides)
    return render_template("providers/show.html", **context)


@provider_bp.route("/<provider_key>")
def show(provider_key):
    return _render_provider(provider_key)


@provider_bp.post("/<provider_key>/settings")
def update_settings(provider_key):
    provider = get_provider(provider_key)
    if provider is None:
        return redirect(url_for("main.home"))

    config = _get_or_create_config(provider_key)
    default_model_id = request.form.get("default_model_id", type=int) or None
    if default_model_id:
        model = SavedModel.query.filter_by(id=default_model_id, provider_key=provider_key).first()
        if model is None:
            flash(f"Choose a {provider.name} model for {provider.name} settings.")
            return redirect(url_for("provider.show", provider_key=provider_key, tab="settings"))

    config.default_model_id = default_model_id
    config.temperature = request.form.get("temperature", type=float) or 1.0
    config.max_output_tokens = request.form.get("max_output_tokens", type=int) or None
    db.session.commit()
    flash(f"{provider.name} settings saved.")
    return redirect(url_for("provider.show", provider_key=provider_key, tab="settings"))


@provider_bp.post("/<provider_key>/send")
def send(provider_key):
    provider = get_provider(provider_key)
    if provider is None:
        return redirect(url_for("main.home"))

    config = _get_or_create_config(provider_key)
    prompt = SavedPrompt.query.get(request.form.get("prompt_id", type=int))
    model = SavedModel.query.filter_by(
        id=request.form.get("model_id", type=int),
        provider_key=provider_key,
    ).first()
    user_text = request.form.get("user_text", "").strip()

    if not prompt or not model or not user_text:
        flash("Choose a prompt, choose a model, and enter request text before sending.")
        return redirect(url_for("provider.show", provider_key=provider_key))

    response_text = ""
    response_id = ""
    try:
        response = send_llm_request(
            LlmRequest(
                provider_key=provider_key,
                model_name=model.name,
                prompt_text=prompt.prompt_text,
                user_text=user_text,
                temperature=config.temperature,
                max_output_tokens=config.max_output_tokens,
            )
        )
        response_text = response.text
        response_id = response.raw_id or ""
    except ProviderNotReadyError as exc:
        flash(str(exc))
    except Exception as exc:
        flash(f"Provider request failed: {exc}")

    return _render_provider(
        provider_key,
        selected_prompt_id=prompt.id,
        selected_model_id=model.id,
        user_text=user_text,
        response_text=response_text,
        response_id=response_id,
    )


@provider_bp.post("/<provider_key>/prompts")
def save_prompt(provider_key):
    provider = get_provider(provider_key)
    if provider is None:
        return redirect(url_for("main.home"))

    prompt = SavedPrompt(
        title=request.form["title"].strip(),
        description=request.form.get("description", "").strip(),
        prompt_text=request.form["prompt_text"].strip(),
    )
    db.session.add(prompt)
    db.session.commit()
    flash("Prompt saved.")
    return redirect(url_for("provider.show", provider_key=provider_key, prompt_id=prompt.id))
