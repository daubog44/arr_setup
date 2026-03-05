#!/bin/sh
set -e

# Carica l'ambiente se eseguito direttamente
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  . "$ENV_FILE"
fi

if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ACCOUNT_ID" ] || [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ] || [ -z "$DOMAIN_NAME" ]; then
  echo "Error: Missing required Cloudflare environment variables."
  exit 1
fi

# Configurable kubectl path and kubeconfig
KUBECTL="${KUBECTL:-kubectl}"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

# Estrai l'ID del tunnel dal token Base64
TUNNEL_ID=$(echo "$CLOUDFLARE_TUNNEL_TOKEN" | base64 -d | jq -r .t)

echo "🔄 Syncing Cloudflare Tunnel configuration for tunnel ID: $TUNNEL_ID"
echo "🌐 Target domain: *.$DOMAIN_NAME -> Traefik Ingress Controller"

# 1. Recupera la configurazione attuale
CURRENT_CONFIG=$(curl -s -X GET "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json")

# Verifica se la richiesta ha avuto successo
if ! echo "$CURRENT_CONFIG" | grep -q '"success":true'; then
  echo "❌ Failed to retrieve tunnel configuration:"
  echo "$CURRENT_CONFIG"
  exit 1
fi

# 2. Prepara la configurazione desiderata tramite API (FQDN Traefik)
# Usiamo il nome DNS interno abbreviato per evitare fastidi IPv6
TRAEFIK_SERVICE="http://traefik.kube-system.svc.cluster.local:80"
echo "📍 Traefik Target: $TRAEFIK_SERVICE"

# Rimuoviamo SOLO le regole esatte "*.dominio" e "dominio", per non cancellare eventuali altre rotte custom dell'utente
NEW_CONFIG_PAYLOAD=$(echo "$CURRENT_CONFIG" | jq -c --arg domain "$DOMAIN_NAME" --arg service "$TRAEFIK_SERVICE" '
  .result.config as $config |
  ($config.ingress | map(select(.service != "http_status:404"))) |
  map(select(.hostname != "*.\($domain)" and .hostname != "\($domain)")) as $filtered_ingress |
  ($filtered_ingress + [
    {"hostname": "*.\($domain)", "service": $service, "originRequest": {"noTLSVerify": true}},
    {"hostname": "\($domain)", "service": $service, "originRequest": {"noTLSVerify": true}},
    {"service": "http_status:404"}
  ]) as $new_ingress |
  {config: ($config | .ingress = $new_ingress)}
')

# 3. Aggiorna la configurazione su Cloudflare
echo "📤 Pushing updated ingress routing rules to Cloudflare API (preserving unrelated routes)..."
UPDATE_RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/configurations" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$NEW_CONFIG_PAYLOAD")

if echo "$UPDATE_RESPONSE" | grep -q '"success":true'; then
  echo "✅ Cloudflare Tunnel Ingress rules successfully updated via API."
else
  echo "❌ Failed to update tunnel ingress rules:"
  echo "$UPDATE_RESPONSE"
  exit 1
fi

# 4. Sincronizzazione Record DNS
echo "🔍 Checking DNS records for $DOMAIN_NAME (preserving unrelated records)..."
# Recupera TUTTI i record A e CNAME
ALL_RECORDS=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records?per_page=100" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json")

EXPECTED_CONTENT="$TUNNEL_ID.cfargotunnel.com"
TARGET_RECORDS="*.$DOMAIN_NAME $DOMAIN_NAME"

for TARGET_NAME in $TARGET_RECORDS; do
  echo "🌐 Verifico record DNS per $TARGET_NAME..."
  
  # Cerca se esiste già e con cosa conflitta
  MATCHING_RECORDS=$(echo "$ALL_RECORDS" | jq -c --arg name "$TARGET_NAME" '.result[] | select(.name == $name)')
  
  NEEDS_CREATION=true
  for record in $MATCHING_RECORDS; do
    TYPE=$(echo "$record" | jq -r .type)
    CONTENT=$(echo "$record" | jq -r .content)
    ID=$(echo "$record" | jq -r .id)
    
    if [ "$TYPE" = "CNAME" ] && [ "$CONTENT" = "$EXPECTED_CONTENT" ]; then
      echo "✅ Record corretto già esistente per $TARGET_NAME."
      NEEDS_CREATION=false
    else
      echo "🗑️  Elimino record errato/conflittuale per $TARGET_NAME: ($TYPE -> $CONTENT)"
      curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records/$ID" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" >/dev/null
    fi
  done
  
  if [ "$NEEDS_CREATION" = true ]; then
    echo "➕ Creo record CNAME per $TARGET_NAME -> $EXPECTED_CONTENT"
    CREATE_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
      -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"type\": \"CNAME\",
        \"name\": \"$TARGET_NAME\",
        \"content\": \"$EXPECTED_CONTENT\",
        \"proxied\": true,
        \"ttl\": 1
      }")
    if echo "$CREATE_RESPONSE" | grep -q '"success":true' || echo "$CREATE_RESPONSE" | grep -q "already exists"; then
      echo "✅ DNS record ensured per $TARGET_NAME."
    else
      echo "❌ DNS setup failed per $TARGET_NAME: $CREATE_RESPONSE"
      exit 1
    fi
  fi
done

echo "🎉 All Cloudflare configurations strictly required for HaaC have been successfully synced without affecting other routes."

