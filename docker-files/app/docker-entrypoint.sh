#!/bin/sh
set -e

exec gosu ${APP_USER} "$@"
