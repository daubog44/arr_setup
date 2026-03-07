# Fetch the latest Debian 13 template URL dynamically using a python script
data "external" "latest_debian13" {
  program = ["python3", "${path.module}/get_latest_template.py"]
}

# Fetch all datastores on the specified Proxmox node to dynamically find local-zfs or local-lvm
data "proxmox_virtual_environment_datastores" "available" {
  node_name = var.master_target_node
}

locals {
  # Find the ID of the datastore meant for VM/CT rootfs (prefer local-zfs, fallback to local-lvm, else fallback to whatever is first)
  datastores_list         = [for ds in data.proxmox_virtual_environment_datastores.available.datastores : ds.id]
  chosen_rootfs_datastore = contains(local.datastores_list, "local-zfs") ? "local-zfs" : (contains(local.datastores_list, "local-lvm") ? "local-lvm" : local.datastores_list[0])
}

resource "proxmox_virtual_environment_download_file" "debian_container_template" {
  content_type = "vztmpl"
  datastore_id = "local"
  node_name    = var.master_target_node

  # The fetched dynamic Proxmox release URL for Debian 13
  url = data.external.latest_debian13.result.url
}

resource "proxmox_virtual_environment_container" "k3s_master" {
  description = "K3s Master Node (Control Plane + Traefik) (HaaC v2)"
  node_name   = var.master_target_node

  initialization {
    hostname = var.lxc_master_hostname
    dns { servers = compact([var.lxc_gateway, "1.1.1.1"]) }
    user_account {
      password = var.lxc_password
      keys     = [trimspace(file("${path.module}/../.ssh/haac_ed25519.pub"))]
    }
    ip_config {
      ipv4 {
        address = var.k3s_master_ip != "" ? var.k3s_master_ip : "dhcp"
        gateway = (var.k3s_master_ip != "" && var.k3s_master_ip != "dhcp") ? (var.lxc_gateway != "" ? var.lxc_gateway : replace(var.k3s_master_ip, "/(.*\\.).*/", "$11")) : null
      }
    }
  }

  network_interface {
    name   = "eth0"
    bridge = "vmbr0"
  }

  disk {
    datastore_id = local.chosen_rootfs_datastore
    size         = 20
  }

  operating_system {
    template_file_id = proxmox_virtual_environment_download_file.debian_container_template.id
    type             = "debian"
  }

  unprivileged = true
  features {
    nesting = true
    keyctl  = false
    fuse    = false
  }

  memory { dedicated = 4096 }
  cpu { cores = 2 }

  mount_point {
    path   = "/data"
    volume = var.host_nas_path
  }

  start_on_boot = true


  started = true
}

resource "proxmox_virtual_environment_container" "k3s_worker" {
  for_each = var.worker_nodes

  description = "K3s Worker Node - ${each.key} (HaaC v2)"
  node_name   = each.value.target_node

  depends_on = [
    proxmox_virtual_environment_container.k3s_master
  ]


  initialization {
    hostname = each.value.hostname
    dns { servers = compact([var.lxc_gateway, "1.1.1.1"]) }
    user_account {
      password = var.lxc_password
      keys     = [trimspace(file("${path.module}/../.ssh/haac_ed25519.pub"))]
    }
    ip_config {
      ipv4 {
        address = each.value.ip != "" ? each.value.ip : "dhcp"
        gateway = (each.value.ip != "" && each.value.ip != "dhcp") ? (var.lxc_gateway != "" ? var.lxc_gateway : replace(each.value.ip, "/(.*\\.).*/", "$11")) : null
      }
    }
  }

  network_interface {
    name   = "eth0"
    bridge = "vmbr0"
  }

  disk {
    datastore_id = local.chosen_rootfs_datastore
    size         = 20
  }

  operating_system {
    template_file_id = proxmox_virtual_environment_download_file.debian_container_template.id
    type             = "debian"
  }

  unprivileged = true
  features {
    nesting = true
    keyctl  = false
    fuse    = false
  }

  memory { dedicated = each.value.memory }
  cpu { cores = each.value.cores }

  mount_point {
    path   = "/data"
    volume = var.host_nas_path
  }

  start_on_boot = true

  started = true

  # Stagger creation to prevent Proxmox ZFS locking timeouts when cloning templates concurrently
  provisioner "local-exec" {
    command = "sleep 15"
  }
}

resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/inventory.tftpl", {
    proxmox_hosts      = distinct(concat([var.master_target_node], [for k, v in var.worker_nodes : v.target_node]))
    proxmox_host_user  = "root"
    master_ip          = var.k3s_master_ip != "" && var.k3s_master_ip != "dhcp" ? element(split("/", var.k3s_master_ip), 0) : try(element(split("/", lookup(proxmox_virtual_environment_container.k3s_master.ipv4, "eth0", "")), 0), "")
    master_vmid        = proxmox_virtual_environment_container.k3s_master.vm_id
    master_target_node = var.master_target_node
    workers            = proxmox_virtual_environment_container.k3s_worker
    worker_configs     = var.worker_nodes
    nas_address        = var.nas_address
    host_nas_path      = var.host_nas_path
    nas_share_name     = var.nas_share_name
    storage_uid        = var.storage_uid
    storage_gid        = var.storage_gid
  })



  filename = "${path.module}/../ansible/inventory.yml"
}

resource "proxmox_virtual_environment_dns" "proxmox_dns" {
  node_name = var.master_target_node
  domain    = var.domain_name
  servers   = compact([var.lxc_gateway, "1.1.1.1", "8.8.8.8"])
}
