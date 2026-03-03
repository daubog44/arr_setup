#!/usr/bin/env bash
set -e

# Carica l'ambiente
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
else
  echo ".env non trovato"
  exit 1
fi

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/haac-k3s.yaml}"
KUBECTL="${KUBECTL:-kubectl}"
KUBESEAL="${KUBESEAL:-$HOME/.local/bin/kubeseal}"
PUB_CERT="$(dirname "$0")/pub-sealed-secrets.pem"
CHART_DIR="$(dirname "$0")/../k8s/charts/haac-stack/templates"

mkdir -p "$CHART_DIR/secrets"

echo "Generazione certificato pubblico Sealed Secrets se non esiste..."
if [ ! -f "$PUB_CERT" ]; then
  KUBECONFIG="$KUBECONFIG" $KUBESEAL --fetch-cert --controller-name=sealed-secrets-controller --controller-namespace=kube-system > "$PUB_CERT"
fi

echo "1. Creazione SealedSecret per ProtonVPN..."
$KUBECTL create secret generic protonvpn-key -n media \
  --from-literal=OPENVPN_USER="${PROTONVPN_OPENVPN_USERNAME}+pmp+nr" \
  --from-literal=OPENVPN_PASSWORD="${PROTONVPN_OPENVPN_PASSWORD}" \
  --from-literal=SERVER_COUNTRIES="${PROTONVPN_SERVER_COUNTRIES}" \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/protonvpn-sealed-secret.yaml"

echo "2. Creazione SealedSecret per Cloudflare Tunnel..."
$KUBECTL create secret generic cloudflare-tunnel-token -n cloudflared \
  --from-literal=token="${CLOUDFLARE_TUNNEL_TOKEN}" \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/cloudflared-sealed-secret.yaml"

echo "3. Generazione configurazione Authelia temporanea..."
export DOMAIN_NAME="${DOMAIN_NAME}"
python3 "$(dirname "$0")/hydrate-authelia.py"

echo "4. Creazione SealedSecret per Authelia config..."
$KUBECTL create secret generic authelia-config-files -n mgmt \
  --from-file=configuration.yml=/tmp/authelia_configuration.yml \
  --from-file=users.yml=/tmp/authelia_users.yml \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/authelia-sealed-secret.yaml"

echo "✅ Sealed Secrets generati con successo in $CHART_DIR/secrets"

echo "5. Idratazione del file values.yaml centrale..."
envsubst < "$(dirname "$0")/../k8s/charts/haac-stack/config-templates/values.yaml.template" > "$(dirname "$0")/../k8s/charts/haac-stack/values.yaml"
echo "✅ values.yaml idratato con successo."
