# Fetch the latest Debian 13 template URL dynamically using a python script
data "external" "latest_debian13" {
  program = [var.python_executable, "${path.module}/get_latest_template.py"]
}

# Fetch all datastores on the specified Proxmox node to dynamically find local-zfs or local-lvm
data "proxmox_datastores" "available" {
  node_name = var.master_target_node
}


locals {
  # Find the ID of the datastore meant for VM/CT rootfs. 
  # If the user provided a var, use it. Otherwise, prefer local-zfs, fallback to local-lvm, else fallback to whatever is first
  datastores_list         = [for ds in data.proxmox_datastores.available.datastores : ds.id]
  chosen_rootfs_datastore = var.lxc_rootfs_datastore != "" ? var.lxc_rootfs_datastore : (contains(local.datastores_list, "local-zfs") ? "local-zfs" : (contains(local.datastores_list, "local-lvm") ? "local-lvm" : local.datastores_list[0]))
}

resource "proxmox_download_file" "debian_container_template" {
  content_type = "vztmpl"
  datastore_id = "local"
  node_name    = var.master_target_node

  # The fetched dynamic Proxmox release URL for Debian 13
  url = data.external.latest_debian13.result.url

  # Keep bootstrap rerunnable even when the template already exists in Proxmox
  # but is not yet tracked in the local state.
  overwrite            = true
  overwrite_unmanaged  = true
}

module "k3s_master" {
  source = "./modules/k3s-lxc-node"

  description      = "K3s Master Node (Control Plane + Traefik) (HaaC v3)"
  target_node      = var.master_target_node
  hostname         = var.lxc_master_hostname
  vmid             = 100
  cores            = 2
  memory           = 4096
  ip_address       = var.k3s_master_ip
  gateway          = var.lxc_gateway != "" ? var.lxc_gateway : cidrhost(var.k3s_master_ip, 1)
  lxc_password     = var.lxc_password
  ssh_public_key   = trimspace(file("${path.module}/../.ssh/haac_ed25519.pub"))
  template_file_id = proxmox_download_file.debian_container_template.id
  datastore_id     = local.chosen_rootfs_datastore
  nas_path         = var.host_nas_path
  dns_servers      = compact([var.lxc_gateway, "1.1.1.1"])
  unprivileged     = var.lxc_unprivileged
  nesting          = var.lxc_nesting
}

module "k3s_workers" {
  source   = "./modules/k3s-lxc-node"
  for_each = var.worker_nodes

  description      = "K3s Worker Node - ${each.key} (HaaC v3)"
  target_node      = each.value.target_node
  hostname         = each.value.hostname
  cores            = each.value.cores
  memory           = each.value.memory
  ip_address       = each.value.ip
  gateway          = var.lxc_gateway != "" ? var.lxc_gateway : cidrhost(each.value.ip, 1)
  lxc_password     = var.lxc_password
  ssh_public_key   = trimspace(file("${path.module}/../.ssh/haac_ed25519.pub"))
  template_file_id = proxmox_download_file.debian_container_template.id
  datastore_id     = local.chosen_rootfs_datastore
  nas_path         = var.host_nas_path
  dns_servers      = compact([var.lxc_gateway, "1.1.1.1"])
  unprivileged     = var.lxc_unprivileged
  nesting          = var.lxc_nesting

  depends_on = [module.k3s_master]
}

resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/inventory.tftpl", {
    proxmox_hosts      = distinct(concat([var.master_target_node], [for k, v in var.worker_nodes : v.target_node]))
    proxmox_host_user  = "root"
    proxmox_access_host = var.proxmox_access_host != "" ? var.proxmox_access_host : var.master_target_node
    master_ip          = var.k3s_master_ip != "" && var.k3s_master_ip != "dhcp" ? element(split("/", var.k3s_master_ip), 0) : try(element(split("/", lookup(module.k3s_master.ipv4, "eth0", "")), 0), "")
    master_vmid        = module.k3s_master.vm_id
    master_target_node = var.master_target_node
    workers            = module.k3s_workers
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
