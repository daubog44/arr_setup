#!/usr/bin/env bash
set -e

K3S_KUBECONFIG=${KUBECONFIG:-/home/daubog44/.kube/haac-k3s.yaml}
KUBECTL=${KUBECTL:-kubectl}

echo "🔐 Configuring Application Authentications..."

##############################
# 1. ArgoCD Credentials
##############################
if [ -n "$ARGOCD_PASSWORD" ] && [ -n "$ARGOCD_USERNAME" ]; then
  echo "Setting up ArgoCD password..."
  # Wait for ArgoCD server to be ready to exec into it. In ArgoCD 2.x, the argocd CLI is available.
  # We use the argocd-server pod to run the bcrypt hash generation.
  ARGOCD_SERVER_POD=$($KUBECTL --kubeconfig=$K3S_KUBECONFIG get pods -n argocd -l app.kubernetes.io/name=argocd-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
  
  if [ -n "$ARGOCD_SERVER_POD" ]; then
    # Generate bcrypt hash (10 rounds) using argocd CLI
    BCRYPT_HASH=$($KUBECTL --kubeconfig=$K3S_KUBECONFIG exec -n argocd $ARGOCD_SERVER_POD -- argocd account bcrypt --password "$ARGOCD_PASSWORD" 2>/dev/null || true)
    
    if [ -n "$BCRYPT_HASH" ]; then
      if [ "$ARGOCD_USERNAME" = "admin" ]; then
        # Patch the secret with the new password hash for default admin
        $KUBECTL --kubeconfig=$K3S_KUBECONFIG patch secret argocd-secret -n argocd -p "{\"stringData\": {\"admin.password\": \"$BCRYPT_HASH\", \"admin.passwordMtime\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}"
        echo "  ✅ ArgoCD admin password updated successfully."
      else
        # Create a new local user and grant admin role
        echo "  Configuring custom user $ARGOCD_USERNAME..."
        $KUBECTL --kubeconfig=$K3S_KUBECONFIG patch cm argocd-cm -n argocd -p "{\"data\": {\"accounts.${ARGOCD_USERNAME}\": \"login\"}}"
        $KUBECTL --kubeconfig=$K3S_KUBECONFIG patch cm argocd-rbac-cm -n argocd -p "{\"data\": {\"policy.csv\": \"g, ${ARGOCD_USERNAME}, role:admin\"}}"
        $KUBECTL --kubeconfig=$K3S_KUBECONFIG patch secret argocd-secret -n argocd -p "{\"stringData\": {\"accounts.${ARGOCD_USERNAME}.password\": \"$BCRYPT_HASH\", \"accounts.${ARGOCD_USERNAME}.passwordMtime\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}"
        echo "  ✅ Custom ArgoCD username $ARGOCD_USERNAME created and password set."
      fi
    else
      echo "  ⚠️ Failed to generate bcrypt hash using argocd CLI."
    fi
  else
    echo "  ⚠️ ArgoCD server pod not found. Skipping password injection."
  fi
fi

##############################
# 2. Headlamp BasicAuth & Token
##############################
if [ -n "$HEADLAMP_USERNAME" ] && [ -n "$HEADLAMP_PASSWORD" ]; then
  echo "Setting up Headlamp Authentication..."
  
  # Ensure mgmt namespace exists
  $KUBECTL --kubeconfig=$K3S_KUBECONFIG create namespace mgmt 2>/dev/null || true
  
  # a. Generate htpasswd for Basic Auth
  # We use python3 standard library to generate the htpasswd formatted string (crypt/bcrypt not needed for basic auth if we use SHA or standard crypt, but htpasswd is best. We can use openssl passwd -apr1)
  # Actually, htpasswd format with bcrypt is standard, but openssl passwd -apr1 is widely supported.
  HTPASSWD_HASH=$(openssl passwd -apr1 "$HEADLAMP_PASSWORD")
  $KUBECTL --kubeconfig=$K3S_KUBECONFIG create secret generic headlamp-basic-auth -n mgmt \
    --from-literal=users="${HEADLAMP_USERNAME}:${HTPASSWD_HASH}" \
    --dry-run=client -o yaml | $KUBECTL --kubeconfig=$K3S_KUBECONFIG apply -f -
    
  echo "  ✅ Headlamp BasicAuth Secret created."

  # b. Create Headlamp ServiceAccount and ClusterRoleBinding (if not already done by manifest, but doing it here guarantees it)
  $KUBECTL --kubeconfig=$K3S_KUBECONFIG create sa headlamp-admin -n mgmt 2>/dev/null || true
  $KUBECTL --kubeconfig=$K3S_KUBECONFIG create clusterrolebinding headlamp-admin --clusterrole=cluster-admin --serviceaccount=mgmt:headlamp-admin 2>/dev/null || true
  
  # c. Generate a long-lived ServiceAccount Token
  # We create a Secret of type kubernetes.io/service-account-token to get a non-expiring token in newer k8s
  cat <<EOF | $KUBECTL --kubeconfig=$K3S_KUBECONFIG apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: headlamp-admin-token
  namespace: mgmt
  annotations:
    kubernetes.io/service-account.name: headlamp-admin
type: kubernetes.io/service-account-token
EOF

  echo "  Waiting for token to be populated..."
  sleep 3

  # Extract token
  HEADLAMP_TOKEN=$($KUBECTL --kubeconfig=$K3S_KUBECONFIG get secret headlamp-admin-token -n mgmt -o jsonpath='{.data.token}' | base64 -d)
  
  if [ -n "$HEADLAMP_TOKEN" ]; then
    # d. Create Traefik Middleware for Headers (Inject Authorization Bearer)
    cat <<EOF | $KUBECTL --kubeconfig=$K3S_KUBECONFIG apply -f -
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: headlamp-token-header
  namespace: mgmt
spec:
  headers:
    customRequestHeaders:
      Authorization: "Bearer $HEADLAMP_TOKEN"
EOF
    echo "  ✅ Traefik Headers Middleware created with token."
  else
    echo "  ❌ Failed to extract Headlamp token."
  fi
fi

echo "🔐 Authentication Setup Complete."

echo "======================================"
echo "    Configuring QUI via API..."
echo "======================================"

QUI_USER="${HEADLAMP_USERNAME:-admin}"
QUI_PASS="${HEADLAMP_PASSWORD:-MySecretPassword123!}"

# Wait for qui pod to exist and be ready
echo "Waiting for QUI pod to become available..."
while true; do
  POD=$($KUBECTL get pod -l app=downloaders -n media -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || true)
  if [ -n "$POD" ] && $KUBECTL exec -n media $POD -c qui -- wget --spider -S http://localhost:7476/api/auth/validate 2>&1 | grep "HTTP/" >/dev/null; then
    break
  fi
  echo "  ...waiting for QUI API inside pod $POD..."
  sleep 5
done

echo "Setting up QUI initial admin..."
$KUBECTL exec -n media $POD -c qui -- wget -qO- --post-data="{\"username\":\"$QUI_USER\",\"password\":\"$QUI_PASS\"}" --header="Content-Type: application/json" http://localhost:7476/api/auth/setup >/dev/null 2>&1 || true

echo "Automating qBittorrent connection in QUI..."
# Extract the temporary password generated by qBittorrent on its first run
TEMP_QBIT_PASS=$($KUBECTL logs -n media $POD -c qbittorrent 2>/dev/null | grep -i "A temporary password is provided for this session:" | tail -n 1 | awk '{print $NF}')

if [ -n "$TEMP_QBIT_PASS" ]; then
  echo "Found temporary qBittorrent password. Updating to standard password..."
  # Exec into the container to call the qBittorrent local API
  $KUBECTL exec -n media $POD -c qui -- wget -qO- --post-data="username=admin&password=$TEMP_QBIT_PASS" --header="Content-Type: application/x-www-form-urlencoded" --save-cookies /tmp/qbit_cookies.txt --keep-session-cookies http://localhost:8080/api/v2/auth/login >/dev/null 2>&1 || true
  # Change the password to QUI_PASS
  $KUBECTL exec -n media $POD -c qui -- wget -qO- --post-data="new_password=$QUI_PASS" --header="Content-Type: application/x-www-form-urlencoded" --load-cookies /tmp/qbit_cookies.txt http://localhost:8080/api/v2/auth/changePassword >/dev/null 2>&1 || true
else
  echo "No temporary password found for qBittorrent (might already be configured or logs rotated)."
fi

# Authenticate QUI session and define the integration
$KUBECTL exec -n media $POD -c qui -- wget -qO- --post-data="{\"username\":\"$QUI_USER\",\"password\":\"$QUI_PASS\"}" --header="Content-Type: application/json" http://localhost:7476/api/auth/login --save-cookies /tmp/cookies.txt --keep-session-cookies >/dev/null 2>&1 || true
$KUBECTL exec -n media $POD -c qui -- wget -qO- --post-data="{\"name\":\"qBittorrent\",\"type\":\"qbittorrent\",\"enabled\":true,\"host\":\"localhost\",\"port\":8080,\"tls\":false,\"tls_skip_verify\":true,\"username\":\"admin\",\"password\":\"$QUI_PASS\",\"settings\":{\"basic_auth\":false}}" --header="Content-Type: application/json" --load-cookies /tmp/cookies.txt http://localhost:7476/api/download_clients >/dev/null 2>&1 || true
echo "✅ QUI Configuration Complete."

exit 0
