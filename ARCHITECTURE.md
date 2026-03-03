# HaaC (Home as a Code) - Project Architecture v2 (K3s + GitOps)

## Architettura del Sistema

Questa repository contiene l'intera infrastruttura del Media Center "State of the Art", gestita integralmente tramite **Infrastructure as Code (IaC)** e principi **GitOps**.

Il sistema è migrato da Docker Compose a un cluster **K3s** (Kubernetes leggero) distribuito su 3 container LXC per massimizzare l'efficienza e l'automazione.

### Il Cluster K3s

1.  **haacarr-master (Control Plane)**: Gestisce l'orchestrazione del cluster e ArgoCD.
2.  **haacarr-worker1 (GPU/Media Node)**: Nodo con **GPU Passthrough** (NVIDIA GTX 1050) per Jellyfin e transcodifica hardware. I device `/dev/nvidia*` e `/dev/dri/*` sono passati al container LXC tramite cgroup2 rules e idmap.
3.  **haacarr-worker2 (General Workload)**: Nodo per carichi di lavoro generali e storage distribuito.

---

## Logica GitOps (ArgoCD)

Il sistema segue il pattern **App of Apps**. ArgoCD monitora la directory `k8s/` in questa repository e applica automaticamente ogni cambiamento al cluster.

### 1. Core Infrastructure (`k8s/core/`)

- **Traefik**: Ingress Controller integrato. Gestisce il routing HTTPS, SSL e il bilanciamento del carico tra i pod.
- **Cloudflared**: Implementa un **Cloudflare Tunnel**. Tutto il traffico WAN entra nel cluster in modo sicuro senza aprire porte sul router.
- **Longhorn**: Storage distribuito ad alta affidabilità. Gestisce i volumi persistenti (configurazioni dei container) replicandoli tra i nodi.

### 2. Applications Stack (`k8s/apps/`)

Le applicazioni sono gestite tramite **Manifesti Kubernetes Nativi (Raw YAML)** per garantire massima trasparenza, controllo totale e zero dipendenze da chart di terze parti.

- **Management Stack**:
  - **Homepage**: Dashboard unificata con widget dinamici.
- **Media Stack**:
  - **Jellyfin**: Media server con transcodifica hardware NVIDIA (NVENC/NVDEC) via GTX 1050.
  - **Gluetun + qBittorrent**: Stack di download sicuro sotto VPN.
  - **Servarr Suite**: Sonarr, Radarr, Prowlarr, Autobrr.
- **Network**:
  - **Cloudflare Tunnel**: Accesso WAN sicuro con logica Wildcard.
  - **Traefik**: Ingress Controller per il routing intelligente.

---

## The "True GitOps" Philosophy

Nessuna configurazione viene fatta a mano:

1.  **Declarativo**: Ogni pod, servizio e ingress è definito in YAML puro.
2.  **Zero-Touch**: Le rotte Cloudflare sono dinamiche grazie al Wildcard routing.
3.  **Local Development**: Possibilità di testare i manifesti istantaneamente senza push su Git.

---

## Deploy dell'Infrastruttura

Il sistema è pronto all'uso con un unico comando:

```bash
# Eroga LXC, configura OS, installa K3s e deploy delle app
task up
```

Per aggiornamenti veloci del software (senza toccare LXC):

```bash
# Ricarica tutti i manifesti Kubernetes e verifica lo stato del cluster
task deploy
```

Il sistema eseguirà automaticamente lo script `verify_cluster.sh` (o `task verify`) alla fine dei comandi di deploy per validare lo stato dei nodi base e del control plane.
