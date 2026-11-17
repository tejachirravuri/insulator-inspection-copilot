#!/bin/sh
# Apply pending database migrations, then start the API.
# Running migrations at start-up is fine for a single instance. With several replicas you
# would run them once as a separate deployment step instead.
set -e
alembic upgrade head
# First start only: load manuals and demo images if the database is empty (never fatal).
python -m inspection_copilot.bootstrap || true
exec uvicorn inspection_copilot.main:app --host 0.0.0.0 --port 8000
