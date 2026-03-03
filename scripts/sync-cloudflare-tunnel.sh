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
# Recuperiamo l'IP del servizio traefik in modo dinamico per evitare hardcoding
TRAEFIK_SERVICE_IP=$(KUBECONFIG="$KUBECONFIG_PATH" $KUBECTL get svc -n kube-system traefik -o jsonpath='{.spec.clusterIP}')
if [ -z "$TRAEFIK_SERVICE_IP" ]; then
  echo "❌ Error: Could not determine Traefik Service IP."
  exit 1
fi
echo "📍 Traefik Service IP detected: $TRAEFIK_SERVICE_IP"

# Rimuoviamo tutte le regole che contengono il dominio (sia specifiche che wildcard)
NEW_CONFIG_PAYLOAD=$(echo "$CURRENT_CONFIG" | jq -c --arg domain "$DOMAIN_NAME" --arg service "http://$TRAEFIK_SERVICE_IP:80" '
  .result.config as $config |
  ($config.ingress | map(select(.service != "http_status:404"))) |
  map(select(if .hostname != null then (.hostname | endswith($domain) | not) else true end)) as $filtered_ingress |
  ($filtered_ingress + [{"hostname": "*.\($domain)", "service": $service, "originRequest": {"noTLSVerify": true}}, {"service": "http_status:404"}]) as $new_ingress |
  {config: ($config | .ingress = $new_ingress)}
')

# 3. Aggiorna la configurazione su Cloudflare
echo "📤 Pushing updated ingress routing rules to Cloudflare API..."
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
echo "🔍 Checking and purging conflicting DNS records for $DOMAIN_NAME..."
# Recupera TUTTI i record A e CNAME
ALL_RECORDS=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records?per_page=100" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json")

EXPECTED_CONTENT="$TUNNEL_ID.cfargotunnel.com"
WILDCARD_NAME="*.$DOMAIN_NAME"

# Rimuovi record specifici che bloccano il wildcard o puntano a vecchi tunnel
echo "$ALL_RECORDS" | jq -c '.result[] | select(.type=="A" or .type=="CNAME")' | while read -r record; do
  NAME=$(echo "$record" | jq -r .name)
  TYPE=$(echo "$record" | jq -r .type)
  CONTENT=$(echo "$record" | jq -r .content)
  ID=$(echo "$record" | jq -r .id)

  # Salta se è esattamente il nostro record wildcard corretto (per evitare cicli di delete/create)
  if [ "$NAME" = "$WILDCARD_NAME" ] && [ "$CONTENT" = "$EXPECTED_CONTENT" ]; then
    continue
  fi

  # Se il nome finisce con il nostro dominio (o è il dominio stesso)
  if echo "$NAME" | grep -qE "(^|\.)$DOMAIN_NAME$"; then
    # Eliminiamo se:
    # 1. È un record A (vogliamo solo tunnel CNAME)
    # 2. È un CNAME ma punta a un tunnel diverso (.cfargotunnel.com ma non il nostro)
    # 3. È un CNAME specifico (es. jellyfin...) e non vogliamo record specifici per far vincere il wildcard
    if [ "$TYPE" = "A" ] || ( [ "$TYPE" = "CNAME" ] && echo "$CONTENT" | grep -q "\.cfargotunnel\.com$" ); then
       echo "🗑️  Elimino record conflittuale: $NAME ($TYPE -> $CONTENT)"
       curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records/$ID" \
         -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" >/dev/null
    fi
  fi
done

# Ora creiamo il wildcard se non esiste
echo "🌐 Verifico/Creo wildcard record..."
CREATE_RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"CNAME\",
    \"name\": \"$WILDCARD_NAME\",
    \"content\": \"$EXPECTED_CONTENT\",
    \"proxied\": true,
    \"ttl\": 1
  }")

if echo "$CREATE_RESPONSE" | grep -q '"success":true' || echo "$CREATE_RESPONSE" | grep -q "already exists"; then
  echo "✅ DNS Wildcard record ensured ($WILDCARD_NAME -> $EXPECTED_CONTENT)."
else
  echo "❌ DNS setup failed: $CREATE_RESPONSE"
  exit 1
fi

