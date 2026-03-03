#!/usr/bin/env bash

# This script verifies that all expected external web endpoints are reachable.
# It polls up to 30 times (every 10 seconds, total 5 minutes) before failing.

set -e

# Default domain name
DOMAIN_NAME=${1:-$DOMAIN_NAME}

if [ -z "$DOMAIN_NAME" ]; then
  echo "Error: DOMAIN_NAME environment variable is required."
  exit 1
fi

URLS=(
  "https://home.${DOMAIN_NAME}"
  "https://jellyfin.${DOMAIN_NAME}"
  "https://argocd.${DOMAIN_NAME}"
  "https://longhorn.${DOMAIN_NAME}"
  "https://sonarr.${DOMAIN_NAME}"
  "https://radarr.${DOMAIN_NAME}"
  "https://prowlarr.${DOMAIN_NAME}"
  "https://qui.${DOMAIN_NAME}"
  "https://autobrr.${DOMAIN_NAME}"
  "https://headlamp.${DOMAIN_NAME}"
)

MAX_RETRIES=30
SLEEP_SECONDS=10

echo "🔍 Starting robust web verification for *.$DOMAIN_NAME..."

for URL in "${URLS[@]}"; do
  echo "Checking $URL..."
  SUCCESS=false
  for i in $(seq 1 $MAX_RETRIES); do
    # NOTE: Since some services return 302 or 401 (e.g. BasicAuth), we accept 2xx, 3xx, and 401 as "reachable".
    HTTP_CODE=$(curl -4 -sL -D - -o /dev/null --max-time 10 "$URL" | grep -m1 "HTTP" | awk '{print $2}')
    
    if [[ "$HTTP_CODE" =~ ^(2[0-9]{2}|3[0-9]{2}|401)$ ]]; then
      echo "  ✅ Reachable (HTTP $HTTP_CODE)"
      SUCCESS=true
      break
    else
      echo "  ⏳ Attempt $i/$MAX_RETRIES: HTTP Code $HTTP_CODE (Bad Gateway/Timeout/Not Ready) - Waiting ${SLEEP_SECONDS}s..."
      sleep $SLEEP_SECONDS
    fi
  done
  
  if [ "$SUCCESS" = false ]; then
    echo "  ❌ Failed to reach $URL after $((MAX_RETRIES * SLEEP_SECONDS)) seconds!"
    exit 1
  fi
done

echo "🎉 All web endpoints are reachable!"
exit 0
