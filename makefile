# Commands used for control and debug the project

build: 
	docker compose build 

rebuild-web: 
	docker compose up -d --build --renew-anon-volumes web

up: 
	docker compose up -d

stop:
	docker compose stop

bash:
	docker exec -it core_ai_agent bash

logs: 
	docker compose logs --tail 100 -f 

restart:
	make stop
	make up

migrations:
	docker exec -it core_ai_agent python manage.py makemigrations

migrate:
	docker exec -it core_ai_agent python manage.py migrate

superuser:
	docker exec -it core_ai_agent python manage.py createsuperuser

test:
	docker exec -it core_ai_agent python manage.py test

lint:
	docker exec -it core_ai_agent uv run ruff check .

# RAG evaluation (see rag/evaluation/README.md). Retrieval is free; each
# `eval_generate` run costs up to 20 LLM requests and resumes where it stopped.
eval_kb:
	uv run python rag/evaluation/scripts/build_kb.py

eval_retrieval:
	docker exec -it core_ai_agent python manage.py rag_eval retrieval

# usage: make eval_generate EXP=small_chunks
eval_generate:
	docker exec -it core_ai_agent python manage.py rag_eval generate $(EXP)

# usage: make eval_judge EXP=small_chunks
eval_judge:
	docker exec -it core_ai_agent python manage.py rag_eval judge $(EXP)

eval_report:
	docker exec -it core_ai_agent python manage.py rag_eval report

# Wipes all DB data (drops the db-data volume) and brings everything back up
# on a clean, empty database. Migration *files* are untouched — `web`'s own
# entrypoint (/start) already runs `migrate` on boot, so the schema is
# reapplied automatically. Use this whenever you want a clean slate to
# experiment from.
reset_db:
	docker compose down -v
	docker compose up -d

# Rare/one-off: deletes every migration file (keeping __init__.py) in
# rag/chat/prompting and regenerates a single fresh 0001_initial per app from
# the current model state. Only makes sense against an already-empty DB
# (run `make reset_db` right after), since it discards migration history —
# any environment still on the old migrations (e.g. a teammate's DB, or a
# deployed one) will no longer line up with these new ones.
reset_migrations:
	find rag/migrations chat/migrations prompting/migrations -maxdepth 1 -type f -name "*.py" ! -name "__init__.py" -delete
	find rag/migrations chat/migrations prompting/migrations -maxdepth 1 -type d -name "__pycache__" -exec rm -rf {} +
	docker compose run --rm --no-deps web python manage.py makemigrations rag chat prompting
	@echo "Reminder: rag's fresh 0001_initial needs pgvector.django.VectorExtension()"
	@echo "as its first operation (before any CreateModel using VectorField) —"
	@echo "add it by hand, it's not something makemigrations knows to generate."