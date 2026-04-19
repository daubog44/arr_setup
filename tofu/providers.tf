terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.103.0" # Latest stable version for bpg/proxmox
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3.0"
    }
  }
}

locals {
  proxmox_access_host = var.proxmox_access_host != "" ? var.proxmox_access_host : var.master_target_node
}

provider "proxmox" {
  endpoint = "https://${local.proxmox_access_host}:8006/"
  username = "root@pam"
  password = var.lxc_password

  # Allow insecure connections (often required in homelabs with self-signed certs)
  insecure = true

  ssh {
    agent = true
    # Connection to the Proxmox host via SSH for file uploads/passthrough operations
    username = "root"
    password = var.lxc_password
    node {
      name    = var.master_target_node
      address = local.proxmox_access_host
    }
  }
}
