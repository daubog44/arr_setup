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
KUBESEAL_VERSION="0.36.0"

if ! command -v "$KUBESEAL" >/dev/null 2>&1 || ! "$KUBESEAL" --version 2>&1 | grep -q "$KUBESEAL_VERSION"; then
  echo "Scaricamento kubeseal v$KUBESEAL_VERSION..."
  wget -qO /tmp/kubeseal.tar.gz "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
  tar -xzf /tmp/kubeseal.tar.gz -C /tmp kubeseal
  mkdir -p ~/.local/bin
  mv /tmp/kubeseal "$KUBESEAL"
  chmod +x "$KUBESEAL"
  rm -f /tmp/kubeseal.tar.gz
fi

PUB_CERT="$(dirname "$0")/pub-sealed-secrets.pem"
CHART_DIR="$(dirname "$0")/../k8s/charts/haac-stack/templates"

mkdir -p "$CHART_DIR/secrets"

echo "Generazione/Verifica certificato pubblico Sealed Secrets..."

# Provo a prelevare il certificato aggiornato dal cluster
echo "Tento la connessione al cluster per aggiornare il certificato pubblico..."

if $KUBESEAL --kubeconfig="$KUBECONFIG" --fetch-cert --controller-name=sealed-secrets-controller --controller-namespace=kube-system > "/tmp/new-pub-cert.pem" 2>/dev/null; then
  echo "✅ Certificato pubblico aggiornato con successo dal cluster."
  mv "/tmp/new-pub-cert.pem" "$PUB_CERT"
else
  echo "⚠️ Impossibile contattare il cluster (timeout o errore)."
  if [ -f "$PUB_CERT" ]; then
    echo "✅ Utilizzo il certificato locale salvato in precedenza in $PUB_CERT"
  else
    echo "❌ ERRORE CRITICO: Nessun certificato locale trovato e cluster non raggiungibile."
    echo "Impossibile cifrare i segreti. Assicurati che K3s sia up almeno una volta per scaricare la chiave pubblica."
    rm -f "/tmp/new-pub-cert.pem"
    exit 1
  fi
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

echo "5. Creazione SealedSecret per ArgoCD Notifications (Ntfy)..."
$KUBECTL create secret generic argocd-notifications-secret -n argocd \
  --from-literal=ntfy-webhook-url="http://ntfy.mgmt.svc.cluster.local:80/${NTFY_TOPIC}" \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/argocd-notifications-sealed-secret.yaml"

echo "5.5 Creazione SealedSecret per ArgoCD OIDC..."
$KUBECTL create secret generic argocd-sso-secret -n argocd \
  --from-literal=clientSecret="${ARGOCD_OIDC_SECRET}" \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/argocd-sso-sealed-secret.yaml"

echo "5.6 Creazione SealedSecret per Grafana OIDC..."
$KUBECTL create secret generic grafana-oidc-secret -n monitoring \
  --from-literal=clientSecret="${GRAFANA_OIDC_SECRET}" \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/grafana-oidc-sealed-secret.yaml"

echo "✅ Sealed Secrets generati con successo in $CHART_DIR/secrets"

SSH_KEY="$(dirname "$0")/../.ssh/haac_ed25519"
if [ -f "$SSH_KEY" ]; then
  echo "6. Creazione SealedSecret per chiave SSH Ansible CronJob..."
  $KUBECTL create secret generic haac-ssh-key -n mgmt \
    --from-file=id_ed25519="$SSH_KEY" \
    --dry-run=client -o yaml | \
    $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/haac-ssh-sealed-secret.yaml"
else
  echo "⚠️  Chiave SSH $SSH_KEY non trovata, salto la generazione del SealedSecret SSH."
fi

echo "7. Creazione SealedSecret per Semaphore UI..."
$KUBECTL create secret generic semaphore-db-secret -n mgmt \
  --from-literal=POSTGRES_PASSWORD="${SEMAPHORE_DB_PASSWORD}" \
  --from-literal=APP_SECRET="${SEMAPHORE_APP_SECRET}" \
  --from-literal=OIDC_SECRET="${SEMAPHORE_OIDC_SECRET}" \
  --from-literal=ADMIN_PASSWORD="${SEMAPHORE_ADMIN_PASSWORD}" \
  --dry-run=client -o yaml | \
  $KUBESEAL --format=yaml --cert="$PUB_CERT" > "$CHART_DIR/secrets/semaphore-sealed-secret.yaml"

echo "8. Idratazione del file values.yaml centrale..."
envsubst < "$(dirname "$0")/../k8s/charts/haac-stack/config-templates/values.yaml.template" > "$(dirname "$0")/../k8s/charts/haac-stack/values.yaml"
echo "✅ values.yaml idratato con successo."
