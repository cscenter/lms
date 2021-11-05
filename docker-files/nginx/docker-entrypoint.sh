#!/bin/sh
# Stops the execution of a script if a command or pipeline has an error
set -e

if [ "x$MAIN_DOMAIN" = 'x' ]; then
    >&2 echo "$0: MAIN_DOMAIN env variable is not provided"; exit 1;
fi

if [ "x$SERVER_NAME" = 'x' ]; then
    export SERVER_NAME=${MAIN_DOMAIN}
    >&2 echo "$0: SERVER_NAME is not provided. Set default to $MAIN_DOMAIN"
fi

./docker-entrypoint.sh "$@"
