# Backend and database


**Main backend framework**: *[FastAPI](https://github.com/tiangolo/fastapi)* running on *[uvicorn](https://github.com/encode/uvicorn) (uvloop)* inside a *[Docker](https://www.docker.com/)* container.

We use the async *[Databases](https://github.com/encode/databases)* for database connections with *[Alembic](https://github.com/sqlalchemy/alembic)* as a migration tool.

**Database**: *[PostgreSQL](https://www.postgresql.org/)* using a *Docker* volume running inside a *Docker* container.
