# LLM Prompting API

Django REST API that routes prompts to LLM providers (Gemini, OpenRouter) and returns structured, schema-validated output.

## Setup

1. Copy `.env` with the required variables (see below).
2. `make build && make up` — starts the API (`web`) and Postgres (`db`) via Docker Compose.
3. `make migrate` — apply migrations.
4. API docs: `http://localhost:8000/api/docs/`

## Environment variables

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY`, `GEMINI_AI_MODEL` | Gemini provider |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | OpenRouter provider |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Database |
| `DEBUG` | `1` for Django debug mode |

## Common commands

See `makefile` for all targets: `build`, `up`, `stop`, `logs`, `bash`, `migrations`, `migrate`, `superuser`.

## Adding a provider

1. Implement `Provider` (see `prompting/providers/base.py`) in `prompting/providers/LLMs/`.
2. Register it in `prompting/factory/provider.py`.
