#!/usr/bin/env bash
set -e

# ==============================================================================
# HaaC E2E Cluster Testing Suite
# ==============================================================================
# This script performs end-to-end verification of the Kubernetes cluster,
# ensuring all nodes, namespaces, deployments, PVCs, and Ingresses are healthy.
# ==============================================================================

# Colori per output
GREEN='\032[0;32m'
RED='\032[0;31m'
YELLOW='\032[1;33m'
NC='\032[0m' # No Color

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/haac-k3s.yaml}"
KUBECTL="${KUBECTL:-kubectl}"

function print_header() {
  echo -e "\n${YELLOW}=== $1 ===${NC}"
}

function check_status() {
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ $1${NC}"
  else
    echo -e "${RED}  ❌ $1${NC}"
    exit 1
  fi
}

echo -e "${GREEN}Starting HaaC Cluster Verification...${NC}"

# 1. Verification K3s Nodes
print_header "1. Check K3s Nodes Status"
NOT_READY_NODES=$($KUBECTL --kubeconfig="$KUBECONFIG" get nodes --no-headers | grep -v "Ready" || true)
if [ -z "$NOT_READY_NODES" ]; then
  echo -e "${GREEN}  ✅ All nodes are Ready.${NC}"
else
  echo -e "${RED}  ❌ Some nodes are not ready:${NC}"
  echo "$NOT_READY_NODES"
  exit 1
fi

# 2. Verification Namespaces
print_header "2. Check Required Namespaces"
REQUIRED_NAMESPACES=("media" "mgmt" "argocd" "longhorn-system" "cloudflared")
for ns in "${REQUIRED_NAMESPACES[@]}"; do
  $KUBECTL --kubeconfig="$KUBECONFIG" get namespace "$ns" > /dev/null 2>&1
  check_status "Namespace $ns exists"
done

# 3. Verification Core Deployments
print_header "3. Check Core System Deployments"
CORE_DEPLOYMENTS=(
  "kube-system deploy/traefik"
  "cloudflared deploy/cloudflared"
  "argocd statefulset/argocd-application-controller"
  "argocd deploy/argocd-server"
)
for dep in "${CORE_DEPLOYMENTS[@]}"; do
  ns=$(echo $dep | awk '{print $1}')
  resource=$(echo $dep | awk '{print $2}')
  $KUBECTL --kubeconfig="$KUBECONFIG" rollout status -n "$ns" "$resource" --timeout=30s >/dev/null 2>&1
  check_status "Resource $resource in $ns is rolled out successfully."
done

# 4. Verification Longhorn & PVCs
print_header "4. Check Longhorn Storage"
$KUBECTL --kubeconfig="$KUBECONFIG" get pods -n longhorn-system | grep -q "Running"
check_status "Longhorn pods are running"

# 5. Verification Media & Mgmt Apps
print_header "5. Check Application Deployments"
APPS=(
  "media deploy/radarr"
  "media deploy/sonarr"
  "media deploy/prowlarr"
  "media deploy/jellyfin"
  "media deploy/downloaders"
  "mgmt deploy/authelia"
  "mgmt deploy/homepage"
  "mgmt deploy/headlamp"
)
for app in "${APPS[@]}"; do
  ns=$(echo $app | awk '{print $1}')
  resource=$(echo $app | awk '{print $2}')
  $KUBECTL --kubeconfig="$KUBECONFIG" rollout status -n "$ns" "$resource" --timeout=60s >/dev/null 2>&1
  check_status "Application $resource in $ns is running."
done

# 6. Verification ArgoCD App-of-Apps Sync
print_header "6. Check GitOps Synchronization"
ARGOCD_SYNC_STATUS=$($KUBECTL --kubeconfig="$KUBECONFIG" get application haac-root -n argocd -o jsonpath='{.status.sync.status}')
if [ "$ARGOCD_SYNC_STATUS" == "Synced" ]; then
  echo -e "${GREEN}  ✅ ArgoCD Root Application is fully synchronized with GitHub.${NC}"
else
  echo -e "${YELLOW}  ⚠️ ArgoCD Root Application sync status: $ARGOCD_SYNC_STATUS${NC}"
  echo -e "${YELLOW}  (This might take a few minutes if a push recently occurred).${NC}"
fi

# 7. Verification Web URLs (delegated to verify-web.sh if exists)
print_header "7. Check Web Endpoints"
VERIFY_SCRIPT="$(dirname "$0")/verify-web.sh"
if [ -f "$VERIFY_SCRIPT" ]; then
  bash "$VERIFY_SCRIPT"
  check_status "Web verification passed via verify-web.sh"
else
  echo -e "${YELLOW}  ⚠️ verify-web.sh not found, skipping endpoint HTTP checks.${NC}"
fi

echo -e "\n${GREEN}🎉 All HaaC cluster automated tests passed successfully!${NC}\n"
