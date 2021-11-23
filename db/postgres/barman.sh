#!/bin/bash
# This is only run when the data directory is empty, i.e. when the database is created for the very first time from scratch
# It creates the users necessary for Barman (backup manager)
# Barman only needs to be superuser for the initialization of the backup process, afterwards it does not have to be
# This connects to the Postgres DB and sets an SQL variable (barmanpwd) and then executes an SQL script
psql -U "${POSTGRES_USER}" --set "barmanpwd=${BARMAN_PASSWORD}" -c '\i /dodeka-init/barman.sql'