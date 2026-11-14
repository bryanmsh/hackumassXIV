#!/bin/sh
# Starts Caddy with the site password hashed at start-up, so the plain password
# lives only in .env. Refuses to start with no password: the site must never be open.
set -eu
if [ -z "${SITE_USER:-}" ] || [ -z "${SITE_PASSWORD:-}" ]; then
	echo "SITE_USER and SITE_PASSWORD must both be set in .env; refusing to start an open site." >&2
	exit 1
fi
SITE_PASSWORD_HASH="$(caddy hash-password --plaintext "$SITE_PASSWORD")"
export SITE_PASSWORD_HASH
unset SITE_PASSWORD
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
