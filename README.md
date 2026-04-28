# OpenAI Flask Starter

This is a small no-auth Flask scaffold for learning Python, the OpenAI Python library, and provider-style LLM API integrations. It includes:

- App factory + blueprints (`main` and `api`)
- Provider pages for OpenAI, Ollama, Gemini, and Claude
- A provider service layer, with OpenAI wired first and the others stubbed
- Global prompt and model libraries stored in SQLite
- SQLite by default (`instance/app.db`)
- Docker Compose support (`web` + `nginx`)
- Tailwind + Vite + Alpine frontend pipeline
- `.env` configuration for secrets such as `OPENAI_API_KEY`

## Environment

Create or edit `.env` from `.env-example`:

```bash
SECRET_KEY=dev-secret-change-me
OPENAI_API_KEY=sk-your-openai-api-key-here
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

The real `.env` file is ignored by Git and excluded from Docker image builds.

## Quick start (Docker)

```bash
docker compose build
docker compose up
```

Then open: `http://localhost:8010`

Note: `compose.yaml` currently maps Nginx as `8010:80` so it doesn't clash with existing port 80 usage.
Change that line to `80:80` when you want standard HTTP on host port 80.

## Quick start (local)

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm run build
flask --app wsgi_app.py init-db
python run.py
```

`init-db` creates tables and seeds one starter prompt plus one starter OpenAI model.

## Structure

```text
app/
  api/
  provider_pages/
  providers/
  services/
  settings/
  main/
  templates/
  static/
  __init__.py
  assets.py
  config.py
  extensions.py
  models.py
instance/
src/
compose.yaml
Dockerfile
```
