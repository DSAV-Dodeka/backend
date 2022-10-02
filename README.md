# Backend and database


**Backend framework (Server)**: Python **[FastAPI](https://github.com/tiangolo/fastapi)** server running on **uvicorn** (managed by **[gunicorn](https://github.com/benoitc/gunicorn)** in production), which uses **[uvloop](https://github.com/MagicStack/uvloop)** as its async event loop.

**Frontend framework (authpage)**: **[React](https://reactjs.org/)**, using [Vite](https://vitejs.dev/).

**Persistent database (DB)**: **[PostgreSQL](https://www.postgresql.org/)** relationa

**In-memory key-value store (KV)**: **[Redis](https://redis.io/)**

We use the async engine of **[SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy)** (only Core, no ORM, we write SQL manually) as a frontend for **[asyncpg](https://github.com/MagicStack/asyncpg)** for all DB operations. **[Alembic](https://github.com/sqlalchemy/alembic)** is used as a migration tool.

The async component of the **[redis-py](https://github.com/redis/redis-py)** library is used as our KV client.

This is an authorization server, authentication server and web app backend API in one. This model is not recommended for large-scale setups but works well for our purposes. It has been designed in a way that makes the components easy to separate.

Client authentication uses the [OPAQUE protocol](https://datatracker.ietf.org/doc/draft-irtf-cfrg-opaque/) (password-authentication key exchange), which protects against agains pre-computation attacks upon server compromise. This makes passwords extra safe in a way that they never leave the client.

Authorization is performed using [OAuth 2.1](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/), with much of [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) also implemented to make it appropriate for authenticating users.

In addition to this, we rely heavily on the following libraries:
* [PyJWT](https://github.com/jpadilla/pyjwt) for signing and parsing JSON web tokens.
* [cryptography](https://github.com/pyca/cryptography) for many cryptographic primitives, primarily for encrypting refresh tokens and handling the keys used for signing the JWTs.
* [pydantic](https://github.com/pydantic/pydantic) for modeling and parsing all data throughout the application.



**Deployment**: Everything is designed to run easily inside a **[Docker](https://www.docker.com/)** container. The total package (Server, DB, KV) is recommended to be deployed using separate Docker containers using **[Docker Compose](https://docs.docker.com/compose/)**. We manage deployment from the **[DSAV-Dodeka/dodeka](https://github.com/DSAV-Dodeka/dodeka)** repository.


### Why did we choose \<x\>?

#### FastAPI

FastAPI was selected because of its modern features reliant on Python typing, which greatly simplify development. FastAPI is built on [Starlette](https://github.com/encode/starlette), a lightweight async web server framework. We wanted a lightweight framework that is not too opinionated, as we wanted full control over as many components as possible. Flask would have been another option, but the heavy integration of typing in FastAPI made us choose it instead. Of course, there are also many other options outside the Python ecosystem. We chose to use Python simply because it is very well-known among university students.


#### Redis and PostgreSQL

PostgreSQL and Redis were selected simply by their popularity and open-source status. They have the most libraries built for them, have a large feature set and are widely supported. We chose a relational database because we do not need massive scaling and having relational constraints simplifies keeping all data in sync. For Redis, we use the [RedisJSON](https://github.com/RedisJSON/RedisJSON) extension module to greatly simplify temporarily storing dictionary-like datastructures for storing state across requests. Since there are a great many specific data types that need to be persisted, and they do not have any interdependency, this is much easier to do in an unstructured key-value store like Redis. It is also much faster than having to do this all in a structured, relational database. Note that all DB and KV accesses are heavily abstracted, the underlying queries could easily be re-implemented in other database systems if necessary.

We went all-in on async, expecting database and IO calls to make up the majority of response times. Using async, other waiting requests can be handled in the mean-time.


#### OAuth

Implementing good authentication/authorization for a website is hard. There are many mistakes to be made. However, many available libraries are very opinionated and hard to hook in to. Furthermore, the options become qutie limited when there is approximately no budget. There are some self-hosted solutions, but getting the configuration right can be very tricky and none were found that served our needs. As a result, we went for our own solution, but built using well-regarded web standards to ensure there are no security holes. OAuth is used by every major website nowadays, so the choice was easy. 


#### OPAQUE

OPAQUE is an in-development protocol that seeks to provide a permanent solution to the question of how to best store passwords and authenticate users using them. A simple hash-based solution would have been good enough, but there are many (good and bad) ways to implement this, while OPAQUE makes it much more straightforward to implement it the right way. It also provides tangible security benefits. It has also been used by big companies (for example by WhatsApp for their end-to-end encrypted backups), so it is mature enough for production use.

Our implementation relies on [opaque-ke](https://github.com/novifinancial/opaque-ke), a library written in Rust. As there is no Python library, a simple wrapper for the Rust library, [opquepy](https://github.com/tiptenbrink/opaquebind/tree/main/opaquepy), was written for this project. It exposes the necessary functions for using OPAQUE and consists of very little code, making it easy to maintain.


### Current configuration

(Only tested on Linux)


#### Server

The server can be run directly from your development environment or in a Docker container in production mode.

##### Setup Redis
For persistence between requests, we use the Redis key-value database. 

* First, go to /dodekabackend/server/redis
* Run `./build.sh`. This should build the required Docker image and you only have to do this once.
* Go to /server/dev.
* Run `./deploy.sh`. This will make the Redis server accessible. Be sure to do this *after* setting up the PostgreSQL database.

Use `./down.sh` to turn Redis off. Do this *before* shutting down the PostgreSQL database.

##### Configuration and import structure

* The first loaded module is loaded is `define/define.py`. It should be fully independent of any other modules. It determines the so-called "compiled configuration", i.e. app-specific configuration. Every application should have this same configuration, no matter the deploy environment. However, it might still change easily and there are good reasons to not define it in the code. It could also vary between "local development" and "production". By default, it loads the `envconfig.toml` in the resources file. This file is populated with values meant for local development and environment-less testing (i.e. without the database). However, if no runtime-flag indicating it is an "envless" environment is set during app startup, a failure will occur.
* Variables that are more "runtime" are loaded in by `env.py`. Using `APISERVER_CONFIG` the path of the config file can be set. By default it is the incomplete `env.toml`. For a development environment, this variable should be set, with `APISERVER_ENV="envless"` included.

##### Development
* If you want to run it locally, [install Poetry](https://python-poetry.org/docs/master/). This can be complicated as it is still a somewhat fragile tool, but it is really easy to make good virtual environments with. 
* Then, set up your IDE with a Python 3.9 Poetry virtual environment. This step can also be complicated. The best way is to simply run `poetry update` in the /server directory. It will give you a path towards the virtualenv it created, which will contain a python executable in the /bin folder. If you point your IDE to that executable as the project interpreter, everything should work.
* Next run `poetry install`, which will also install the project. Currently the `apiserver` package is in a /src folder which is nice for test isolation, but it might confuse your IDE. In that case, find something like 'project structure' configuration and set the /src folder as a 'sources folder' or similar.
* Before running, you must have the environment variable APISERVER_CONFIG set to `./dev.config.toml` in order to be able to run it. This can be most easily done by editing the run configuration in an IDE as PyCharm.
* Now you can run the server either by just running the `dev.py` in src/apiserver or by running `poetry run s-dodeka`. The server will automatically reload if you change any files. It will tell you at which address you can access it.

##### Production
* First, build a Python environment with the dependencies installed by running: `docker build --tag dodeka/server-deps -f server-deps.Dockerfile .`
* Next, build the project itself by running `docker build --tag dodeka/server .` in the main directory.
* If you did not yet build the Redis server, first build the Redis server by running `./build.sh` in the /server/redis folder.
* Be sure you have the database running with the `dodeka` network turned on, after which you can run `./deploy.sh` in /server/deployment. It works similar to the database and can be shut down using `./down.sh`. 

### Migrations

We can use Alembic for migrations, which allow you to programatically apply large schema changes to your database.

First you need to have the Poetry environment running as described earlier and ensure the database is on as well. 

* Navigate to the /server/src/apiserver/db/migrations directory.
* From there run `poetry run alembic revision --autogenerate -m "Some message"`
* This will generate a Python file in the migrations/versions directory, which you can view to see if everything looks good. It basically looks at the database, looks at the schema described in db/model.py and generates code to migrate to the described schema.
* Then, you can run `poetry run alembic upgrade head`, which will apply the latest generated revision. If you now use your database viewer, the table will have hopefully appeared.
* If there is a mismatch with the current revision, use `poetry run alembic stamp head` before the above 2 commmands.

To check if everything is working, try out the following:

* Navigate to http://localhost:4242/user_write/126?name=YOURNAME&last_name=YOURLASTNAME (replace YOURNAME and YOURLASTNAME with what you want)
* Check if it is indeed retrievable by going to http://localhost:4242/users/126


### Startup and shutdown flow

* Start the DB


### Dev vs production

If you are in a dev environment, you can start by running `dev.py`

### Import order

Nothing may depend on a package below itself in this list

* resources
* define
* define.*
* utilities
* db/kv
* data
* auth
* routers
* app

### Important to keep in mind

Always add a trailing "/" to endpoints.