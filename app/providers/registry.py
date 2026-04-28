from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    key: str
    name: str
    description: str
    status: str
    api_key_env: str


PROVIDERS = {
    "openai": Provider(
        key="openai",
        name="OpenAI",
        description="Use the official OpenAI Python SDK and Responses API.",
        status="Ready",
        api_key_env="OPENAI_API_KEY",
    ),
    "ollama": Provider(
        key="ollama",
        name="Ollama",
        description="Local model provider support will be added after OpenAI is working.",
        status="Stub",
        api_key_env="",
    ),
    "gemini": Provider(
        key="gemini",
        name="Gemini",
        description="Google Gemini support is planned for a later provider adapter.",
        status="Stub",
        api_key_env="GEMINI_API_KEY",
    ),
    "claude": Provider(
        key="claude",
        name="Claude",
        description="Anthropic Claude support is planned for a later provider adapter.",
        status="Stub",
        api_key_env="ANTHROPIC_API_KEY",
    ),
}


def list_providers():
    return list(PROVIDERS.values())


def get_provider(provider_key: str):
    return PROVIDERS.get(provider_key)
