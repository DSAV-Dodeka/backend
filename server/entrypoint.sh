#!/bin/bash
export GUNICORN_CMD_ARGS="--bind=0.0.0.0:4241 --workers=1"
export DODEKA_DB_HOST="d-dodeka-db-1"
export DODEKA_DB_PORT="5432"
poetry run gunicorn dodekaserver.app:app -w 1 -k uvicorn.workers.UvicornWorker