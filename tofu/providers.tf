terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.99.0" # Latest stable version for bpg/proxmox
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3.0"
    }
  }
}

provider "proxmox" {
  endpoint = "https://${var.master_target_node}:8006/"
  username = "root@pam"
  password = var.lxc_password

  # Allow insecure connections (often required in homelabs with self-signed certs)
  insecure = true

  ssh {
    agent = true
    # Connection to the Proxmox host via SSH for file uploads/passthrough operations
    username = "root"
    password = var.lxc_password
  }
}
