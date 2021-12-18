FROM python:3.9-slim-bullseye AS poetry
RUN apt-get update
RUN apt-get install curl -y
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | POETRY_HOME=/etc/poetry python3 -
ENV PATH="/etc/poetry/bin:${PATH}"

FROM poetry AS server-deps
WORKDIR dodeka/server
COPY poetry.lock .
COPY pyproject.toml .
RUN poetry install --no-interaction --no-root