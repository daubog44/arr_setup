output "master_ip" {
  description = "The designated IP address of the K3s Master LXC container"
  value       = try(element(split("/", lookup(proxmox_virtual_environment_container.k3s_master.ipv4, "eth0", "")), 0), "")
}

output "master_vmid" {
  description = "The Proxmox VMID of the K3s Master LXC container"
  value       = proxmox_virtual_environment_container.k3s_master.vm_id
}

output "master_target_node" {
  description = "The Proxmox node where the K3s Master is running"
  value       = proxmox_virtual_environment_container.k3s_master.node_name
}

output "workers" {
  description = "Map of worker nodes with their IP addresses and VMIDs"
  value = {
    for k, v in proxmox_virtual_environment_container.k3s_worker : k => {
      ip   = try(element(split("/", lookup(v.ipv4, "eth0", "")), 0), "")
      vmid = v.vm_id
    }
  }
}


# --- Application Ingress Outputs ---
output "url_homepage" {
  description = "URL for the Homepage Server Dashboard"
  value       = "https://home.${var.domain_name}"
}

output "url_jellyfin" {
  description = "URL for Jellyfin Media Server"
  value       = "https://jellyfin.${var.domain_name}"
}

output "url_sonarr" {
  description = "URL for Sonarr"
  value       = "https://sonarr.${var.domain_name}"
}

output "url_radarr" {
  description = "URL for Radarr"
  value       = "https://radarr.${var.domain_name}"
}

output "url_prowlarr" {
  description = "URL for Prowlarr"
  value       = "https://prowlarr.${var.domain_name}"
}

output "url_qui" {
  description = "URL for Qui (qBittorrent UI)"
  value       = "https://qui.${var.domain_name}"
}

output "url_argocd" {
  description = "URL for ArgoCD"
  value       = "https://argocd.${var.domain_name}"
}

output "url_longhorn" {
  description = "URL for Longhorn UI"
  value       = "https://longhorn.${var.domain_name}"
}

