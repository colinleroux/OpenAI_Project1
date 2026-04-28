from dataclasses import dataclass

from flask import current_app


@dataclass(frozen=True)
class LlmRequest:
    provider_key: str
    model_name: str
    prompt_text: str
    user_text: str
    temperature: float = 1.0
    max_output_tokens: int | None = None


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
        "input": request.user_text,
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
