from dataclasses import dataclass

from flask import current_app

from .attachments import RequestAttachment


@dataclass(frozen=True)
class LlmRequest:
    provider_key: str
    model_name: str
    prompt_text: str
    user_text: str
    temperature: float = 1.0
    max_output_tokens: int | None = None
    attachments: tuple[RequestAttachment, ...] = ()


@dataclass(frozen=True)
class LlmResponse:
    text: str
    raw_id: str | None = None


class ProviderNotReadyError(RuntimeError):
    pass


def send_llm_request(request: LlmRequest) -> LlmResponse:
    if request.provider_key == "openai":
        return _send_openai_request(request)
    raise ProviderNotReadyError("This provider is stubbed for now.")


def _send_openai_request(request: LlmRequest) -> LlmResponse:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderNotReadyError(
            "The OpenAI Python package is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise ProviderNotReadyError("OPENAI_API_KEY is not set in your .env file.")

    client = OpenAI(api_key=api_key)
    kwargs = {
        "model": request.model_name,
        "instructions": request.prompt_text,
        "input": _build_openai_input(client, request),
        "temperature": request.temperature,
    }
    if request.max_output_tokens:
        kwargs["max_output_tokens"] = request.max_output_tokens

    response = client.responses.create(**kwargs)
    return LlmResponse(
        text=getattr(response, "output_text", "") or _extract_response_text(response),
        raw_id=getattr(response, "id", None),
    )


def _extract_response_text(response) -> str:
    output_parts = []
    for output_item in getattr(response, "output", []) or []:
        for content_item in getattr(output_item, "content", []) or []:
            text = getattr(content_item, "text", None)
            if text:
                output_parts.append(text)
    return "\n".join(output_parts)


def _build_openai_input(client, request: LlmRequest) -> str | list[dict]:
    if not request.attachments:
        return request.user_text

    content = [{"type": "input_text", "text": request.user_text}]
    local_text_parts = []
    unsupported = []

    for attachment in request.attachments:
        if attachment.kind in {"text", "docx"}:
            local_text_parts.append(
                f"Attached file: {attachment.filename}\n\n{attachment.extracted_text}".strip()
            )
        elif attachment.kind == "image":
            content.append(
                {
                    "type": "input_image",
                    "file_id": _upload_openai_file(client, attachment, purpose="vision"),
                }
            )
        elif attachment.kind == "pdf":
            content.append(
                {
                    "type": "input_file",
                    "file_id": _upload_openai_file(client, attachment, purpose="user_data"),
                }
            )
        elif attachment.kind == "audio":
            unsupported.append(
                f"{attachment.filename} is an audio file. Audio upload will be wired in a later transcription/audio step."
            )
        else:
            unsupported.append(f"{attachment.filename} has an unsupported file type.")

    if local_text_parts or unsupported:
        content.append(
            {
                "type": "input_text",
                "text": "\n\n".join(local_text_parts + unsupported),
            }
        )

    return [{"role": "user", "content": content}]


def _upload_openai_file(client, attachment: RequestAttachment, purpose: str) -> str:
    with attachment.path.open("rb") as file_handle:
        uploaded_file = client.files.create(file=file_handle, purpose=purpose)
    return uploaded_file.id
