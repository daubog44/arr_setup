#!/usr/bin/env bash
set -e

source ../.env

# Usiamo -json per evitare di catturare box di diagnostica/warning su stdout
JSON_OUTPUT=$(tofu output -json 2>/dev/null || echo "{}")
MASTER_VMID=$(echo "$JSON_OUTPUT" | jq -r '.master_vmid.value // empty')
WORKER_VMIDS=$(echo "$JSON_OUTPUT" | jq -r '.workers.value[]?.vmid // empty')

shutdown_vm() {
  local vmid=$1
  local name=$2
  # Validazione: deve essere un numero intero
  if [[ "$vmid" =~ ^[0-9]+$ ]]; then
    # Controlla se il container è in esecuzione
    local status_output
    status_output=$(ssh -o StrictHostKeyChecking=no root@${MASTER_TARGET_NODE} "pct status $vmid" 2>/dev/null || true)
    if echo "$status_output" | grep -q "status: running"; then
      echo "⏳ Tentativo di shutdown grazioso per $name (VMID $vmid)..."
      # 1. Fermo i servizi K3s internamente (velocizza lo shutdown e pulisce i mount). Uso 2>/dev/null per nascondere errori se il servizio non esiste (es. k3s.service sui worker)
      ssh -o StrictHostKeyChecking=no root@${MASTER_TARGET_NODE} "pct exec $vmid -- bash -c 'systemctl stop k3s 2>/dev/null || true; systemctl stop k3s-agent 2>/dev/null || true'" || true
      # 2. Comando shutdown con timeout di 3 minuti
      if ! ssh -o StrictHostKeyChecking=no root@${MASTER_TARGET_NODE} "pct shutdown $vmid --timeout 180"; then
        echo "⚠️ Shutdown grazioso fallito o timeout per $name. Eseguo stop forzato..."
        ssh -o StrictHostKeyChecking=no root@${MASTER_TARGET_NODE} "pct stop $vmid" || true
      fi
    else
      echo "⏭️ Salto shutdown per $name: Il container (VMID $vmid) è già spento o non esistente."
    fi
  else
    echo "⏭️ Salto $name: VMID '$vmid' non valido o non trovato."
  fi
}

shutdown_vm "$MASTER_VMID" "Master"
for vmid in $WORKER_VMIDS; do
  shutdown_vm "$vmid" "Worker"
done
