#!/bin/bash
# It creates a slot, this might already exist but that isn't a problem
service cron start
barman receive-wal --create-slot d-dodeka-db-1
barman cron
# This requires barman to be a superuser
barman switch-wal d-dodeka-db-1
barman cron
# Sleep to ensure everything is synchronized, etc.
echo "Sleeping for 30 s to ensure synchronization..."
sleep 31s
barman switch-wal --force --archive d-dodeka-db-1
mkdir /var/lib/barman/log
# Create empty crontab
crontab -l 2>/dev/null
# 2 (stderr) to 1 (stdout), which is output to file
croncmd="barman cron > /var/lib/barman/log/barman_cron.log 2>&1"
cronjob="* * * * * $croncmd"
# Add to cron without duplicating it
( crontab -l | grep -v -F "$croncmd" ; echo "$cronjob" ) | crontab -

croncmd="barman backup d-dodeka-db-1 >> /var/lib/barman/log/barman_backup.log 2>&1"
cronjob="0 4 * * * $croncmd"
( crontab -l | grep -v -F "$croncmd" ; echo "$cronjob" ) | crontab -

barman backup d-dodeka-db-1
barman check d-dodeka-db-1

/bin/bash
