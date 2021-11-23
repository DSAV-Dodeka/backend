#!/bin/bash
# It creates a slot, this might already exist but that isn't a problem
barman receive-wal --create-slot d-dodeka-db-1
barman cron
# This requires barman to be a superuser
barman switch-wal d-dodeka-db-1
barman cron

/bin/bash