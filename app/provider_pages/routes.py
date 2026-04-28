from flask import current_app, flash, redirect, render_template, request, url_for

from . import provider_bp
from ..extensions import db
from ..models import ProviderConfig, RequestLog, SavedModel, SavedPrompt
from ..providers import get_provider, list_providers
from ..services.attachments import load_saved_attachments, save_request_attachments
from ..services.llm import LlmRequest, ProviderNotReadyError, count_input_tokens, send_llm_request


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
    logs = RequestLog.query.filter_by(provider_key=provider_key).order_by(RequestLog.created_at.desc()).limit(50).all()
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
        "selected_prompt_id": request.args.get("prompt_id", type=int),
        "selected_model_id": request.args.get("model_id", type=int) or config.default_model_id,
        "user_text": "",
        "response_text": "",
        "response_id": "",
        "actual_usage": None,
        "estimated_input_tokens": None,
        "pending_log_id": None,
        "pending_attachment_paths": [],
        "logs": logs,
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
    include_files = request.form.get("include_files") == "on"
    attachment_paths = request.form.getlist("attachment_paths")
    if attachment_paths:
        attachments = tuple(load_saved_attachments(attachment_paths, current_app.config["UPLOAD_FOLDER"]))
    elif include_files:
        attachments = tuple(
            save_request_attachments(request.files.getlist("attachments"), current_app.config["UPLOAD_FOLDER"])
        )
    else:
        attachments = ()

    if not prompt or not model or not user_text:
        flash("Choose a prompt, choose a model, and enter request text before sending.")
        return redirect(url_for("provider.show", provider_key=provider_key))

    llm_request = LlmRequest(
        provider_key=provider_key,
        model_name=model.name,
        prompt_text=prompt.prompt_text,
        user_text=user_text,
        temperature=config.temperature,
        max_output_tokens=config.max_output_tokens,
        attachments=attachments,
    )
    action = request.form.get("action", "send")
    measure_before_send = request.form.get("measure_load") == "on"

    if measure_before_send and action != "confirm_send":
        try:
            estimated_input_tokens = count_input_tokens(llm_request)
            log = _create_request_log(
                provider_key=provider_key,
                model=model,
                prompt=prompt,
                user_text=user_text,
                attachments=attachments,
                estimated_input_tokens=estimated_input_tokens,
                status="measured",
            )
            db.session.add(log)
            db.session.commit()
            return _render_provider(
                provider_key,
                selected_prompt_id=prompt.id,
                selected_model_id=model.id,
                user_text=user_text,
                estimated_input_tokens=estimated_input_tokens,
                pending_log_id=log.id,
                pending_attachment_paths=[str(attachment.path) for attachment in attachments],
            )
        except ProviderNotReadyError as exc:
            flash(str(exc))
            return _render_provider(
                provider_key,
                selected_prompt_id=prompt.id,
                selected_model_id=model.id,
                user_text=user_text,
            )

    response_text = ""
    response_id = ""
    log = None
    pending_log_id = request.form.get("pending_log_id", type=int)
    if pending_log_id:
        log = RequestLog.query.filter_by(id=pending_log_id, provider_key=provider_key).first()
    if log is None:
        log = _create_request_log(
            provider_key=provider_key,
            model=model,
            prompt=prompt,
            user_text=user_text,
            attachments=attachments,
            estimated_input_tokens=None,
            status="sending",
        )
        db.session.add(log)
        db.session.commit()

    try:
        response = send_llm_request(llm_request)
        response_text = response.text
        response_id = response.raw_id or ""
        _update_log_from_response(log, response)
        actual_usage = response.usage or {}
    except ProviderNotReadyError as exc:
        log.status = "failed"
        log.error_message = str(exc)
        db.session.commit()
        flash(str(exc))
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        db.session.commit()
        flash(f"Provider request failed: {exc}")

    return _render_provider(
        provider_key,
        selected_prompt_id=prompt.id,
        selected_model_id=model.id,
        user_text=user_text,
        response_text=response_text,
        response_id=response_id,
        actual_usage=actual_usage if "actual_usage" in locals() else None,
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


@provider_bp.post("/<provider_key>/prompts/<int:prompt_id>")
def update_prompt(provider_key, prompt_id):
    provider = get_provider(provider_key)
    if provider is None:
        return redirect(url_for("main.home"))

    prompt = SavedPrompt.query.get_or_404(prompt_id)
    prompt.title = request.form["title"].strip()
    prompt.description = request.form.get("description", "").strip()
    prompt.prompt_text = request.form["prompt_text"].strip()
    db.session.commit()
    flash("Prompt updated.")
    return redirect(url_for("provider.show", provider_key=provider_key, prompt_id=prompt.id))


def _create_request_log(
    provider_key: str,
    model: SavedModel,
    prompt: SavedPrompt,
    user_text: str,
    attachments: tuple,
    estimated_input_tokens: int | None,
    status: str,
) -> RequestLog:
    return RequestLog(
        provider_key=provider_key,
        model_name=model.name,
        prompt_id=prompt.id,
        prompt_title=prompt.title,
        request_text=user_text,
        included_files=bool(attachments),
        attachment_names=", ".join(attachment.filename for attachment in attachments) or None,
        estimated_input_tokens=estimated_input_tokens,
        status=status,
    )


def _update_log_from_response(log: RequestLog, response):
    usage = response.usage or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}

    log.status = "completed"
    log.response_id = response.raw_id
    log.actual_input_tokens = usage.get("input_tokens")
    log.actual_output_tokens = usage.get("output_tokens")
    log.actual_total_tokens = usage.get("total_tokens")
    log.cached_tokens = input_details.get("cached_tokens")
    log.reasoning_tokens = output_details.get("reasoning_tokens")
    db.session.commit()
