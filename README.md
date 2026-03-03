# HaaC (Home as a Code) - Arr Setup

This repository contains the Infrastructure as Code (OpenTofu) and Configuration as Code (Ansible + Kubernetes Manifests) to deploy a full home server stack on Proxmox and K3s.

It automates the provisioning of LXC containers, networking, and the deployment of the \*arr suite (Radarr, Sonarr, Prowlarr), Jellyfin, Authelia, Cloudflare Tunnels, and more.

## Quick Start

1. Copy `.env.example` to `.env` and fill in your secrets.
2. Ensure you have `go-task` installed.
3. Run `task up` to provision the infrastructure, configure the OS via Ansible, and deploy the Kubernetes workloads.

## Architecture

See `ARCHITECTURE.md` for a detailed breakdown of the components.
