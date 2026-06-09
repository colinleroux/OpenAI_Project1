# OpenAI Flask Lab

OpenAI Flask Lab is a small Flask application for learning Python, Flask structure, and LLM API workflows. It starts with OpenAI as the first working provider and keeps placeholders for Ollama, Gemini, and Claude so the app can grow into a multi-provider playground.

The app is intentionally built as a learning project rather than a production product. It uses Flask blueprints, SQLAlchemy models, SQLite, Docker Compose, Tailwind, Vite, and Alpine so each part of the stack is visible and easy to inspect.

## What It Does

- Shows a home dashboard with provider tiles.
- Provides a dedicated page for each provider.
- Stores reusable prompts globally.
- Stores models by provider, so OpenAI models only appear in the OpenAI playground.
- Stores reusable request texts for each provider.
- Sends OpenAI requests from a playground UI.
- Can measure estimated input tokens before sending.
- Logs request metadata and actual token usage.
- Supports attaching text, `.docx`, PDF, and image files to OpenAI requests.

## OpenAI Portion

The OpenAI provider is the first fully wired provider in the app. The main user flow lives at:

```text
/providers/openai
```

The OpenAI page has several tabs.

### Playground

The playground is where you build and send an API request. A request is made from:

- a selected OpenAI model
- a selected saved prompt
- request text entered by the user
- optional uploaded files

The selected saved prompt is used as the instruction text for the API call. The request text is the per-call user input. This separation is intentional because it makes it easier to learn how stable instructions and changing user input affect model behavior.

The playground also lets you preview and edit the selected saved prompt before sending. Request text can be saved for reuse from the same screen.

### Models

Models are stored in SQLite as provider-scoped records. This prevents accidentally selecting an Ollama, Gemini, or Claude model while using the OpenAI provider.

OpenAI starts with a seeded model:

```text
gpt-4.1-mini
```

You can add or edit models from Global Settings.

### Prompts

Saved prompts include:

- title
- description
- prompt text

Prompts are global because the same instruction can often be reused across providers. In the OpenAI playground, selecting a prompt shows a preview so you can inspect the exact instruction text before sending.

### Request Texts

The `Request texts` tab stores reusable user inputs for the current provider. This is useful when experimenting with the same question or task across models and providers.

Saved request texts include:

- title
- description
- request text

From the tab, you can use a saved request text in the playground, edit it, or delete it.

### Measuring Load Before Send

The playground includes a `Measure load before send` checkbox. When checked, the app first calls OpenAI's input-token counting endpoint before sending the actual generation request.

The confirmation step shows:

- estimated input tokens
- provider max output token setting, if configured
- potential upper token bound

This is useful for learning how prompt text, request text, and attachments affect request size before spending a full generation call.

### Sending The Request

OpenAI request logic lives in:

```text
app/services/llm.py
```

The app uses a small service layer so the Flask routes do not directly contain provider-specific API logic. Today, OpenAI is implemented and the other providers return a clear "not wired yet" message.

The service builds an OpenAI Responses API request using:

- `model`
- `instructions`
- `input`
- optional `max_output_tokens`
- optional file inputs

The API key is loaded from:

```text
OPENAI_API_KEY
```

### File Attachments

Attachment handling lives in:

```text
app/services/attachments.py
```

Supported OpenAI attachment behavior:

- Text-like files are read locally and added as extra text input.
- `.docx` files are extracted locally and added as extra text input.
- PDFs are uploaded to OpenAI and attached as file input.
- Images are uploaded to OpenAI and attached as image input.
- Audio file support is planned but not fully wired yet.

Uploaded files are saved under:

```text
instance/uploads/
```

That folder is ignored by Git and Docker image builds.

### Request Logs

The `View logs` tab shows recent OpenAI request activity. Logs are stored in SQLite using the `RequestLog` model.

Logs capture useful learning data such as:

- provider
- model
- prompt used
- estimated input tokens
- actual input tokens
- actual output tokens
- actual total tokens
- cached tokens
- reasoning tokens
- response id
- status and errors

This makes the app useful as a small lab for comparing prompts, request text, models, file sizes, and token usage over time.

## Project Structure

```text
app/
  api/              Health/API routes
  main/             Home dashboard
  provider_pages/   Provider playground, settings, logs, request texts
  providers/        Provider registry
  services/         LLM and attachment service logic
  settings/         Global prompt/model settings
  templates/        Jinja templates
  static/           Built Vite assets
  __init__.py       App factory and init-db command
  config.py         Environment-backed app config
  extensions.py     SQLAlchemy extension
  models.py         Database models
instance/           SQLite DB and local uploads
src/                Vite/Tailwind/Alpine frontend entry
compose.yaml        Docker Compose setup
Dockerfile          Multi-stage frontend/backend/nginx build
```

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

## Quick Start With Docker

```bash
docker compose build --no-cache
docker compose up
```

Then open:

```text
http://localhost:8010
```

The Compose setup maps Nginx to host port `8010` so it does not clash with port `80`.

If containers are already running and you want a clean rebuild:

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

## Quick Start Locally

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm run build
flask --app wsgi_app.py init-db
python run.py
```

`init-db` creates database tables and seeds one starter prompt plus one starter OpenAI model.
