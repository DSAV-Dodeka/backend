# PostgreSQL build

### Configuration

* The DB uses port 3141 instead of the default (to make it explicit)
* The config file, which sets the port and some other settings, is loaded in a separate directory as otherwise the DB cannot initialize from scratch
* Other than the port, no settings were changed
* The pga_hba.conf needs those two lines added so other hosts can connect, e.g. for barman