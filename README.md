# Backend and database


**Main backend framework**: *[FastAPI](https://github.com/tiangolo/fastapi)* running on *[uvicorn](https://github.com/encode/uvicorn) (uvloop)* inside a *[Docker](https://www.docker.com/)* container.

We use the async *[Databases](https://github.com/encode/databases)* for database connections with *[Alembic](https://github.com/sqlalchemy/alembic)* as a migration tool.

**Database**: *[PostgreSQL](https://www.postgresql.org/)* using a *Docker* volume running inside a *Docker* container.

### Current configuration

(Only tested on Linux)

* Checkout the DSAV-Dodeka/dodekabackend repository, which contains a /server and /db directory.

#### Database
The database is always run from a container. We use the official [PostgreSQL 14 container](https://hub.docker.com/_/postgres/) for the entire runtime.

Requirements:
* [Docker Engine](https://docs.docker.com/engine/install/)
* [Docker Compose V2](https://docs.docker.com/compose/cli-command/)

It it is recommended to use some kind of IDE to easily view the database, for example [JetBrains](https://www.jetbrains.com/community/education/#students) DataGrip (which you can get for free with TU Delft e-mail account)

* Checkout the DSAV-Dodeka/dodekabackend repository.
* Go into the /db folder.
* Run `./build.sh`. Only do this once.
* Go into the /db/deployment folder.
* Run `./deploy.sh`.

You now have a PostgreSQL server running with the configuration as described in the .env.deploy and .env.db files. You can access it at postgresql://{POSTGRESS_USER}:{POSTGRES_PASSWORD}@{HOST}:{PORT}/{POSTGRES_USER} (based on the environment variable files). If you are in a container on the network defined in the `docker-compose.yml`, {HOST}:{PORT} is {container name}:{PostgreSQL port=5432}. If you are on the host, it is localhost:{HOST_PORT}. Currently: postgresql://dodeka:dodeka@localhost:3141/dodeka

You can turn it off using `./down.sh`.

##### What is going on behind the scenes?

Most files have comments explaining what everything is. 

* `./build.sh` simply (for now, at least) pulls the PostgreSQL container and names it dodeka/postgres.
* `./deploy.sh` loads a bunch of configuration files and then runs `docker compose up`.

Take a look at the `docker-compose.yml`, for the set up. In essence, it just runs the container, uses a host directory for all the database files (so it is persisted across runs) and runs on a network so that other containers can access it.

##### Barman backup

//TODO

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