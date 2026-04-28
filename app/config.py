import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DB = BASE_DIR / "instance" / "app.db"

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite:///{INSTANCE_DB.as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
