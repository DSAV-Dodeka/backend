#!/bin/bash
set -a
export APISERVER_CONFIG=./localenv.toml
export GUNICORN_CMD_ARGS="--bind=0.0.0.0:4241 --workers=20"
poetry run gunicorn apiserver.app:app -w 20 -k uvicorn.workers.UvicornWorker