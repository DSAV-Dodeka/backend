FROM postgres:14-bullseye
ADD postgresql.conf /dodeka-conf/postgresql.conf
ADD barman.sh /docker-entrypoint-initdb.d/barman.sh
ADD barman.sql /dodeka-init/barman.sql