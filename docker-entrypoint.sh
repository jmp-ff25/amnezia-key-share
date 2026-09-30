#!/bin/sh
set -eu

# Docker mounts named volumes after the image filesystem is created. Make the
# SQLite volume writable before dropping the root privileges used only here.
chown -R keyport:keyport /data

exec gosu keyport sh -c 'alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=* --no-access-log'
