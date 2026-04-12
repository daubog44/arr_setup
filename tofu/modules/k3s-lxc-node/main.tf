resource "terraform_data" "declared_container_spec" {
  triggers_replace = {
    description        = var.description
    target_node        = var.target_node
    hostname           = var.hostname
    vmid               = tostring(coalesce(var.vmid, 0))
    cores              = tostring(var.cores)
    memory             = tostring(var.memory)
    ip_address         = var.ip_address
    gateway            = var.gateway
    template_file_id   = var.template_file_id
    datastore_id       = var.datastore_id
    nas_path           = var.nas_path
    unprivileged       = tostring(var.unprivileged)
    nesting            = tostring(var.nesting)
    dns_servers        = jsonencode(var.dns_servers)
    ssh_public_key_sha = sha256(var.ssh_public_key)
    lxc_password_sha   = sha256(var.lxc_password)
  }
}

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

  lifecycle {
    # The Proxmox provider cannot model the extra LXC config we reconcile later
    # (for example idmaps, TUN/eBPF mounts, and GPU passthrough lines). Those
    # lines are still part of the desired HaaC state, but they live in the
    # Proxmox config file and would otherwise be removed by any in-place update.
    #
    # Treat the container declaration as create-or-replace only:
    # - no-op on runtime drift introduced by later reconciliation steps
    # - replace intentionally when the declared bootstrap spec changes
    ignore_changes       = all
    replace_triggered_by = [terraform_data.declared_container_spec]
  }
}

output "vm_id" {
  value = proxmox_virtual_environment_container.node.vm_id
}

output "ipv4" {
  value = proxmox_virtual_environment_container.node.ipv4
}
