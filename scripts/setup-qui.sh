#!/bin/bash
set -e

# Load env variables
if [ -f .env ]; then
  source .env
fi

QUI_URL="https://qui.${DOMAIN_NAME:-nucleoautogenerativo.it}"
# Default credentials or from env
QUI_USER="${QUI_USERNAME:-admin}"
QUI_PASS="${QUI_PASSWORD:-MySecretPassword123!}"

echo "🔄 Automating QUI Setup at ${QUI_URL}..."

# Wait for QUI to be reachable
echo "⏳ Waiting for QUI API to become available..."
until curl -skL -f "${QUI_URL}/api/auth/validate" > /dev/null 2>&1; do
    echo "   ...still waiting"
    sleep 5
done

# We use a temporary cookie file
COOKIE_JAR=$(mktemp)
trap 'rm -f $COOKIE_JAR' EXIT

echo "🔐 Attempting initial setup (if not already done)..."
# Setup will return 403 or 400 if already setup, so we ignore errors here
curl -skL -X POST "${QUI_URL}/api/auth/setup" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${QUI_USER}\",\"password\":\"${QUI_PASS}\"}" >/dev/null 2>&1 || true

echo "🔑 Logging in to obtain session cookie..."
# Login and save cookie
LOGIN_RESP=$(curl -skL -c "${COOKIE_JAR}" -w "%{http_code}" -X POST "${QUI_URL}/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${QUI_USER}\",\"password\":\"${QUI_PASS}\"}")

if [[ "$LOGIN_RESP" != *"200"* ]] && [[ "$LOGIN_RESP" != *"201"* ]] && [[ "$LOGIN_RESP" != *"20"* ]]; then
    echo "❌ Failed to login to QUI. HTTP Code: $LOGIN_RESP"
    exit 1
fi
echo "✅ Login successful."

echo "🌐 Adding qBittorrent download client to QUI..."
# Note: we use internal kubernetes DNS or localhost?
# Since QUI is in the exact same pod as qbittorrent, we use localhost!
CLIENT_PAYLOAD=$(cat <<EOF
{
  "name": "Local qBittorrent",
  "type": "qbittorrent",
  "enabled": true,
  "host": "localhost",
  "port": 8080,
  "tls": false,
  "tls_skip_verify": true,
  "username": "${QBIT_USER:-admin}",
  "password": "${QBIT_PASS:-adminadmin}",
  "settings": {
    "basic_auth": false
  }
}
EOF
)

ADD_RESP=$(curl -skL -b "${COOKIE_JAR}" -w "%{http_code}" -X POST "${QUI_URL}/api/download_clients" \
    -H 'Content-Type: application/json' \
    -d "${CLIENT_PAYLOAD}")

if [[ "$ADD_RESP" == *"20"* ]] || [[ "$ADD_RESP" == *"409"* ]]; then
    echo "✅ qBittorrent client configured in QUI successfully (or already exists)."
else
    echo "❌ Failed to add qBittorrent client. HTTP Code: $ADD_RESP"
    exit 1
fi

echo "🎉 QUI automation complete!"
