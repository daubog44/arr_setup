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
echo "--- 7. eBPF Passthrough Verification (inside pod) ---"
echo "[eBPF] Launching privileged debug pod on a worker node to validate eBPF filesystem access..."
kubectl run ebpf-verify --image=busybox:1.36 \
  --restart=Never \
  --overrides='{
    "spec": {
      "nodeName": null,
      "hostPID": true,
      "hostNetwork": true,
      "containers": [{
        "name": "ebpf-verify",
        "image": "busybox:1.36",
        "command": ["sh", "-c", "echo === BPF mounts ===; mount | grep bpf; echo === /sys/fs/bpf contents ===; ls /sys/fs/bpf && echo OK || echo MISSING"],
        "securityContext": {"privileged": true},
        "volumeMounts": [{"name": "bpf", "mountPath": "/sys/fs/bpf"}]
      }],
      "volumes": [{"name": "bpf", "hostPath": {"path": "/sys/fs/bpf", "type": "Directory"}}]
    }
  }' \
  --rm -it --timeout=60s 2>/dev/null \
  || echo "[eBPF] ⚠️  Test pod fallito o timeout. Controlla che /sys/fs/bpf sia montato sull'host."

echo ""
echo "--- 8. Authelia Middleware Verification ---"
echo "[MW] Middleware presenti nel cluster:"
MW_NAMESPACES=("mgmt" "monitoring" "media" "security" "chaos")
MW_FAIL=0
for NS in "${MW_NAMESPACES[@]}"; do
  EXISTS=$(kubectl get middleware authelia -n "$NS" --no-headers 2>/dev/null | wc -l)
  if [ "$EXISTS" -gt 0 ]; then
    echo "  ✅ Middleware 'authelia' trovato in namespace: $NS"
  else
    echo "  ❌ Middleware 'authelia' MANCANTE in namespace: $NS"
    MW_FAIL=1
  fi
done

FORCE_EXISTS=$(kubectl get middleware force-https -n mgmt --no-headers 2>/dev/null | wc -l)
if [ "$FORCE_EXISTS" -gt 0 ]; then
  echo "  ✅ Middleware 'force-https' trovato in namespace: mgmt"
else
  echo "  ❌ Middleware 'force-https' MANCANTE in namespace mgmt"
  MW_FAIL=1
fi

echo ""
echo "[MW] IngressRoutes che referenziano 'authelia' middleware:"
kubectl get ingressroute -A -o json 2>/dev/null \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
found = 0
for item in data.get('items', []):
  ns = item['metadata']['namespace']
  name = item['metadata']['name']
  routes = item.get('spec', {}).get('routes', [])
  for route in routes:
    for mw in route.get('middlewares', []):
      if 'authelia' in mw.get('name', ''):
        print(f'  ✅ {ns}/{name} -> middleware: {mw[\"name\"]}')
        found += 1
if found == 0:
  print('  ⚠️  Nessun IngressRoute con middleware authelia trovato!')
" 2>/dev/null || echo "  [skip] python3 non disponibile o kubectl error."

if [ "$MW_FAIL" -eq 0 ]; then
  echo ""
  echo "  ✅ Tutti i Middleware Authelia sono configurati correttamente."
else
  echo ""
  echo "  ❌ Alcuni Middleware mancano — controlla la sincronizzazione ArgoCD (haac-stack)."
fi

echo ""
echo "✅ Validazione Cluster Completata."
