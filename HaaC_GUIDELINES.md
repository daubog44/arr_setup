# HaaC Project Guidelines

## 1. No Hardcoding Rule

> [!IMPORTANT]
> **ABSUTELY NO HARDCODING.**
> All configuration values (IPs, Hostnames, Passwords, Paths, Domain names) MUST be defined in the central `.env` file or passed as variables.

- **Ansible**: Use `{{ var_name }}` or `lookup('env', 'VAR_NAME')`.
- **OpenTofu**: Use `var.var_name`.
- **Kubernetes**: Use `envsubst` in Taskfile to inject variables into manifests.
- **Scripts**: Use environment variables.

## 2. Centralized Configuration

The root `.env` file is the **Single Source of Truth**.

- Secrets and simple values are stored as plain env vars.
- Complex structures (like worker nodes) are stored as a JSON string (`WORKER_NODES_JSON`).
- **Important**: Although passed as JSON, always maintain strict typing in `variables.tf` (e.g., `map(object({...}))`) to ensure OpenTofu validates the structure during parsing.

## 3. Unified Credentials

- User `root` is assumed for all infrastructure (Proxmox, LXC).
- `LXC_PASSWORD` is the master password for both Proxmox nodes and LXC containers.

## 4. Dynamic Discovery

Whenever possible, let the system discover values (e.g., `MASTER_IP` via Tofu outputs, `DEFAULT_GATEWAY` via `ip route`).
