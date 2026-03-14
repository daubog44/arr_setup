#!/usr/bin/env bash
# wait-for-stack.sh — Attende che ArgoCD abbia sincronizzato haac-stack
# e che le risorse critiche (secrets + pod downloaders) siano pronte.
# Logga ogni step in modo chiaro così è evidente cosa sta succedendo.

set -euo pipefail

K3S_KUBECONFIG="${KUBECONFIG:-$HOME/.kube/haac-k3s.yaml}"
KUBECTL="${KUBECTL:-kubectl}"
TIMEOUT="${WAIT_TIMEOUT:-1800}"   # secondi totali di attesa (default: 30 minuti)
INTERVAL=10

elapsed=0

log() { echo "[$(date '+%H:%M:%S')] $*"; }
fail() { echo "[$(date '+%H:%M:%S')] ❌ TIMEOUT dopo ${TIMEOUT}s: $*" >&2; exit 1; }

# ─── 1. Attendi che ArgoCD sia raggiungibile ───────────────────────────────────
log "⏳ [1/4] Attendo che ArgoCD API server sia pronto..."
until $KUBECTL --kubeconfig="$K3S_KUBECONFIG" get applications -n argocd &>/dev/null; do
  [ $elapsed -ge $TIMEOUT ] && fail "ArgoCD API server non raggiungibile"
  log "   ...ArgoCD non ancora pronto (${elapsed}s/${TIMEOUT}s)"
  sleep $INTERVAL; elapsed=$((elapsed + INTERVAL))
done
log "✅ [1/4] ArgoCD API server raggiungibile."

# ─── 2. Attendi sync di haac-stack ────────────────────────────────────────────
log "⏳ [2/4] Attendo sync ArgoCD application 'haac-stack'..."
until $KUBECTL --kubeconfig="$K3S_KUBECONFIG" get application haac-stack -n argocd \
      -o jsonpath='{.status.sync.status}' 2>/dev/null | grep -q "Synced"; do
  [ $elapsed -ge $TIMEOUT ] && fail "haac-stack non sincronizzata"
  SYNC_STATUS=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get application haac-stack -n argocd \
    -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "N/A")
  HEALTH_STATUS=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get application haac-stack -n argocd \
    -o jsonpath='{.status.health.status}' 2>/dev/null || echo "N/A")
  
  if [ "$HEALTH_STATUS" = "Degraded" ]; then
    fail "haac-stack è in stato Degraded! Controlla ArgoCD per i dettagli sull'errore."
  fi

  log "   ...haac-stack sync=${SYNC_STATUS} health=${HEALTH_STATUS} (${elapsed}s/${TIMEOUT}s)"
  sleep $INTERVAL; elapsed=$((elapsed + INTERVAL))
done
log "✅ [2/4] haac-stack sincronizzata con successo."

# ─── 3. Attendi che il Secret protonvpn-key sia decriptato da sealed-secrets ──
log "⏳ [3/4] Attendo che il Secret 'protonvpn-key' sia disponibile in namespace 'media'..."
until $KUBECTL --kubeconfig="$K3S_KUBECONFIG" get secret protonvpn-key -n media &>/dev/null; do
  [ $elapsed -ge $TIMEOUT ] && fail "Secret protonvpn-key non creato (sealed-secrets-controller ok?)"
  log "   ...Secret protonvpn-key non ancora presente (${elapsed}s/${TIMEOUT}s)"
  log "   (Il controller sealed-secrets deve decriptare il SealedSecret appena synced da ArgoCD)"
  sleep $INTERVAL; elapsed=$((elapsed + INTERVAL))
done
log "✅ [3/4] Secret 'protonvpn-key' disponibile."

# ─── 4. Attendi che il pod downloaders sia Running ────────────────────────────
log "⏳ [4/4] Attendo che il pod 'downloaders' (Gluetun+QUI+qBittorrent) sia Ready..."
until $KUBECTL --kubeconfig="$K3S_KUBECONFIG" get pods -n media -l app=downloaders \
      -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null \
      | grep -q "True"; do
  [ $elapsed -ge $TIMEOUT ] && fail "Pod downloaders non Ready"
  POD_NAME=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get pods -n media -l app=downloaders \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "N/A")
  POD_PHASE=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get pods -n media -l app=downloaders \
    -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "N/A")
  READY_CNT=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get pods -n media "$POD_NAME" \
    -o jsonpath='{.status.containerStatuses[*].ready}' 2>/dev/null | tr ' ' '\n' | { grep -c "true" || true; })
  TOT_CNT=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get pods -n media "$POD_NAME" \
    -o jsonpath='{.spec.containers[*].name}' 2>/dev/null | wc -w || echo "?")
  LAST_EVENT=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get events -n media \
    --field-selector "involvedObject.name=${POD_NAME}" \
    --sort-by='.lastTimestamp' 2>/dev/null | tail -1 | awk '{$1=$2=$3=$4=""; print substr($0,5)}' | cut -c1-60 || true)
  log "   ...pod=${POD_NAME} phase=${POD_PHASE} containers_ready=${READY_CNT}/${TOT_CNT} | ${LAST_EVENT} (${elapsed}s/${TIMEOUT}s)"
  sleep $INTERVAL; elapsed=$((elapsed + INTERVAL))
done

POD_NAME=$($KUBECTL --kubeconfig="$K3S_KUBECONFIG" get pods -n media -l app=downloaders \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
log "✅ [4/4] Pod '${POD_NAME}' pronto. Stack pronto per la configurazione."
echo ""
echo "🚀 haac-stack completamente sincronizzato e operativo. Procedo con configure-apps."
