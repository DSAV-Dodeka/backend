# Barman

[Barman](https://docs.pgbarman.org/release/2.13) is the Backup and Recovery Manager for PostgreSQL. It is very powerful and can provide very safe backups, but it is also difficult to set up.

It was mostly done using the documentation and by looking at [this Docker image](https://github.com/ubc/barman-docker), which is unfortunately outdated and not as flexible to configure.

A number of things must go right before Barman can work:

1. There needs to be a connection between the DB container and the Barman container, assumed here to be on a Docker bridge-type network, where the DB container is d-dodeka-db-1 running on port 3141.
2. PostgreSQL must accept connections coming from other hosts, so the pg_hba.conf needs to be modified.
3. There needs to be a password file set-up for Barman to use. For this, there needs to be a .pgpass in the /var/lib/barman (the barman user home).
4. The DB needs two users with specific priviledges (barman, streaming_barman) 
5. Cron jobs need to be set up

Important notes:

* Files outside of the data directory or not backed up. Currently the PostgreSQL conf file is outside the data directory.

### TODO

* Set up proper cron jobs
* Test recovery
* Persist data in a good way
* Set up proper deployment using docker compose

### Misc useful commands

Test connection (it should not prompt for a password):
```shell
psql -U barman -p 3141 -d dodeka
```

Update conf on the PostgreSQL server
```postgresql
SELECT pg_reload_conf();
```

### Main init commands

```shell
barman receive-wal --create-slot d-dodeka-db-1
barman cron
barman switch-wal d-dodeka-db-1
barman cron
barman backup d-dodeka-db-1
```