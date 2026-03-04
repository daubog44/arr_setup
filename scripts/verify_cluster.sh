#!/bin/bash
# HaaC v2 Cluster Verification Script

echo "--- 1. Node Status ---"
kubectl get nodes -o wide

echo ""
echo ""
echo "--- 2. Pod Health (All Namespaces) ---"
kubectl get pods -A | awk 'NR==1 || ($4!="Running" && $4!="Completed")'
echo "(If only headers are shown, all pods are healthy in Running or Completed state!)"
echo ""
echo "--- 3. GPU Passthrough Verification ---"
echo "[Node] Checking allocatable NVIDIA GPUs on nodes:"
kubectl get nodes -o custom-columns="NAME:.metadata.name,GPU_ALLOCATABLE:.status.allocatable.nvidia\.com/gpu"

echo "[NVIDIA] Device plugin pods:"
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Test GPU access in Jellyfin
echo "[App] Testing GPU access in Jellyfin:"
JELLYFIN_POD=$(kubectl get pods -n media -l app.kubernetes.io/name=jellyfin -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || kubectl get pods -n media -l app=jellyfin -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$JELLYFIN_POD" ]; then
    echo "Checking NVIDIA GPU in Jellyfin pod: $JELLYFIN_POD"
    kubectl exec -n media "$JELLYFIN_POD" -- nvidia-smi 2>/dev/null \
        || echo "nvidia-smi not available yet or GPU not correctly passed through."
else
    echo "Jellyfin pod not found yet (may still be scheduling)."
fi

echo ""
echo "--- 4. Storage Verification (Longhorn) ---"
kubectl get pvc -A
echo ""
kubectl get pv

echo ""
echo "--- 5. Ingress Verification ---"
kubectl get ingress -A
echo ""
echo "--- 6. Certificate Verification (Cert-Manager/Traefik) ---"
kubectl get certificates -A 2>/dev/null || echo "Cert-Manager non installato o non pronto."

echo ""
echo "✅ Validazione Cluster Completata."
