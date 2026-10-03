#!/bin/sh
# ensure the DB volume files are owned by the app user (docker cp seeds as root)
if [ "$(id -u)" = "0" ]; then
  chown -R tolid:tolid /app/outputs/panel/data 2>/dev/null
  exec su-exec tolid "$@" 2>/dev/null || exec setpriv --reuid=tolid --regid=tolid --clear-groups "$@" 2>/dev/null || exec su -s /bin/sh -c "$*" tolid
fi
exec "$@"
