# We use a Docker image with postgres installed, be sure to use a different entrypoint so it doesn't start a server
FROM postgres:14-bullseye
# We install barman, cron and nano (the latter for convenience)
RUN apt-get update
RUN apt-get install barman cron nano -y
# Add the passfile to the barman home directory
ADD .pgpass /var/lib/barman/.pgpass
# It needs to have this specific permissions and ownership to work
RUN chmod 0600 /var/lib/barman/.pgpass
RUN mkdir /dodeka-barman
RUN chown barman:barman /dodeka-barman
# The barman configuration
ADD d-dodeka-db-1.conf /etc/barman.d/d-dodeka-db-1.conf
RUN chown barman:barman /etc/barman.d/d-dodeka-db-1.conf
# Barman startup
ADD barman_entrypoint.sh /var/lib/barman/barman_entrypoint.sh
RUN chown -R barman:barman /var/lib/barman
ENTRYPOINT ["/bin/bash", "/var/lib/barman/barman_entrypoint.sh"]
CMD [""]
