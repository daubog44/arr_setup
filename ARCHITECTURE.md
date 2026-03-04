# HaaC (Home as a Code) - Project Architecture v3 (True GitOps + Sealed Secrets)

## Architettura del Sistema

Questa repository contiene l'intera infrastruttura del Media Center "State of the Art", gestita integralmente tramite **Infrastructure as Code (IaC)** e principi **GitOps**.

Il sistema gira su un cluster **K3s** distribuito su 3 container LXC per massimizzare l'efficienza e l'automazione.

### Il Cluster K3s

1.  **haacarr-master (Control Plane)**: Gestisce l'orchestrazione del cluster e ArgoCD.
2.  **haacarr-worker1 (GPU/Media Node)**: Nodo con **GPU Passthrough** (NVIDIA GTX 1050) per Jellyfin e transcodifica hardware.
3.  **haacarr-worker2 (General Workload)**: Nodo per carichi di lavoro generali e storage distribuito.

---

## Logica GitOps (ArgoCD & Umbrella Helm Chart)

Questo cluster abbandona i vecchi `kubectl apply` manuali ed abbraccia il pattern **App of Apps** con un **Umbrella Helm Chart**.

### 1. Core Infrastructure (`k8s/core/`)

Viene applicato automaticamente al bootstrap per erigere le fondamenta del GitOps:

- **ArgoCD**: Il motore pulsante che sincronizza GitHub col cluster ogni 3 minuti.
- **Sealed Secrets Controller**: Il gestore delle crittografie asimmetriche (v0.36.0 installato nativamente e automaticamente dal `Taskfile.yml`).
- **Traefik & Cloudflared**: Piattaforma ingress e tunneling per l'esterno senza porte aperte.

### 2. Applications Stack (`k8s/charts/haac-stack/`)

Gestisce le app vere e proprie (Jellyfin, Authelia, \*arr suite, Gluetun) tramite un **Umbrella Helm Chart**. ArgoCD scarica questo chart da GitHub e lo applica.

- **Centralizzazione Totale (`values.yaml`)**: Le impostazioni come nomi dominio e parametri vengono popolate in un unico file `values.yaml`, eliminando file sparsi.

---

## The "Gold Standard" Automation (Chicche della Codebase)

L'infrastruttura è governata da automazioni robuste e sicure:

1. **Il `.env` comanda tutto (Single Source of Truth)**
   Nessuno script remoto contiene dati. Il tuo file `.env` sul PC locale è l'unico file che possiede l'anello del potere.
2. **Sealed Secrets (Crittografia Asimmetrica)**
   Per poter salvare le password nel repository Git senza che siano in chiaro, i file sensibili vengono passati attraverso `kubeseal` usando una chiave pubblica generata dinamicamente dal tuo K3s. Il risultato è un file incomprensibile (`*sealed-secret.yaml`) che ArgoCD scarica, e che solo il controller Sealed Secrets dentro al cluster sa decriptare grazie alla propria chiave privata segregata.
3. **Idratazione Dinamica dei Template (.template)**
   Configurazioni complesse (come `authelia/configuration.yml.template`) e parametriche (`values.yaml.template`) non vengono mai scritte a mano. Script Python e Bash (`generate-sealed-secrets.sh`) iniettano i dati esatti prendendoli dal `.env` curando la formattazione dello YAML.
4. **Git Pre-Commit Hooks**
   Il task `setup-hooks` incastra uno script dentro a Git in modo che **prima di ogni `git commit`**, il sistema generi o aggiorni silenziosamente tutti i file Sealed Secrets e Helm Values. È impossibile committare password vecchie!
5. **Configurazioni VPN Avanzate (Gluetun + ProtonVPN)**
   Lo script di generazione configura autonomamente Gluetun per attivare **NAT-PMP (Port Forwarding)** e **Moderate NAT** iniettando nella password OpenVPN i suffissi `+pmp+nr`, mantenendo qBittorrent verde assieme a uno script di "port-sync" che aggiorna l'interfaccia UI.

---

## Deploy dell'Infrastruttura e Workflow

Tutta la baracca si avvia e si aggiorna tramite **`go-task`**:

### Inizializzazione Completa da Zero

```bash
# Eroga LXC, configura OS, installa K3s, ArgoCD e innesca la sincronizzazione GitOps totale.
task up
```

### Il Workflow per aggiornare configurazioni o password (Deploy in Produzione)

Se cambi una password nel `.env` o vuoi aggiungere un utente ad Authelia, e vuoi mandare la modifica alla produzione:

1. Modifica il tuo `.env` (o il template)
2. Fai `git add .` e `git commit -m "update"` -> **Il pre-commit hook prenderà il volo e originerà tutti i file criptati da solo!**
3. Fai `git push`.
4. ArgoCD vedrà la modifa su GitHub e aggiornerà autonomamente i Pod.

### Il Workflow per i Test Locali (Deploy di Test)

Se vuoi provare una modifica ai file YAML **subito**, senza dover pushare su GitHub né aspettare ArgoCD:

```bash
# By-passa ArgoCD, compila e applica l'Helm Chart usando il tuo terminale direttamente in K3s.
# Utile se non sei sicuro che la configurazione funzioni e non vuoi "sporcare" i commit su Git.
task deploy-test
```
