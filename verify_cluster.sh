#!/bin/bash
# HaaC v2 Cluster Verification Script

echo "--- 1. Node Status ---"
kubectl get nodes -o wide

echo ""
echo "--- 2. Pod Health (All Namespaces) ---"
kubectl get pods -A

echo ""
echo "--- 3. GPU Passthrough Verification ---"
# Check NVIDIA device plugin status
echo "[NVIDIA] Device plugin pods:"
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds

# Check Intel GPU plugin status (only schedules if gpu_intel=true label exists)
echo "[Intel] GPU plugin pods:"
kubectl get pods -n kube-system -l app=intel-gpu-plugin

# Test GPU access in Jellyfin
JELLYFIN_POD=$(kubectl get pods -n media -l app=jellyfin -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$JELLYFIN_POD" ]; then
    echo "Checking NVIDIA GPU in Jellyfin pod: $JELLYFIN_POD"
    kubectl exec -n media "$JELLYFIN_POD" -- nvidia-smi 2>/dev/null \
        || echo "nvidia-smi not available yet (pod may still be initializing)"
else
    echo "Jellyfin pod not found yet (may still be scheduling)."
fi

echo ""
echo "[Labels] GPU-related node labels:"
kubectl get nodes --show-labels | grep -oE "gpu[^,=]*=[^,]+" | sort -u || echo "No GPU labels found yet."

echo ""
echo "--- 4. Storage Verification (Longhorn) ---"
kubectl get pvc -A
kubectl get storageclass

echo ""
echo "--- 5. Ingress Verification ---"
kubectl get ingress -A
