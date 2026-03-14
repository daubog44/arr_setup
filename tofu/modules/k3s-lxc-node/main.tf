resource "proxmox_virtual_environment_container" "node" {
  description = var.description
  node_name   = var.target_node
  vm_id       = var.vmid

  initialization {
    hostname = var.hostname
    dns {
      servers = var.dns_servers
    }
    user_account {
      password = var.lxc_password
      keys     = [var.ssh_public_key]
    }
    ip_config {
      ipv4 {
        address = var.ip_address != "" ? var.ip_address : "dhcp"
        gateway = (var.ip_address != "" && var.ip_address != "dhcp") ? var.gateway : null
      }
    }
  }

  network_interface {
    name   = "eth0"
    bridge = "vmbr0"
  }

  disk {
    datastore_id = var.datastore_id
    size         = 20
  }

  operating_system {
    template_file_id = var.template_file_id
    type             = "debian"
  }

  unprivileged = var.unprivileged
  features {
    nesting = var.nesting
  }

  memory { dedicated = var.memory }
  cpu { cores = var.cores }

  mount_point {
    path   = "/data"
    volume = var.nas_path
  }

  start_on_boot = true
  started       = true
}

output "vm_id" {
  value = proxmox_virtual_environment_container.node.vm_id
}

output "ipv4" {
  value = proxmox_virtual_environment_container.node.ipv4
}
