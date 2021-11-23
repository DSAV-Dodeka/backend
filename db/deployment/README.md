# PostgreSQL deployment

See the /db/postgres folder for building the Dockerfile, this is for deploying.

Run:
```shell
./deploy.sh
```
to deploy the PostgreSQL server.

Run:
```shell
./down.sh
```

to stop the PostgreSQL server.

### Configuration choices

See the text in the individual files for explanation.

### TODO

* Create SSH tunnel to allow secure remote access
* Manage variables that can't be expanded (like names in Dockerfiles) with a script
* Load secrets in a better way
* Change authentication method (ensure scram-sha-256 is used)