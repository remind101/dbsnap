#!/bin/bash

ENVDIR=/etc/container_environment

function log () {
    echo "[$(date)] $*"
}

for CRONFILE in $(ls ${ENVDIR}/CRON_*)
do
    BASE=$(basename $CRONFILE)
    log "Setting up ${BASE} cron job."
    cat $CRONFILE > /etc/cron.d/${BASE}
    # Need to add a new line or cron won't use it
    echo >> /etc/cron.d/${BASE}
    chmod 0600 /etc/cron.d/${BASE}
done
