variable "master_target_node" {
  description = "The Proxmox node where the K3s Master will be deployed"
  type        = string
  default     = "pve"
}


# Removed proxmox_host variable as it's now derived dynamically from target_node

variable "lxc_password" {
  description = "Root password for the LXC containers"
  type        = string
}

variable "lxc_master_hostname" {
  description = "Hostname for the K3s Master"
  type        = string
}

variable "worker_nodes" {
  description = "Map of worker nodes with their configurations"
  type = map(object({
    hostname    = string
    target_node = string
    ip          = string
    memory      = number
    cores       = number
    labels      = optional(map(string), {})
  }))
  default = {}
}






# proxmox_password removed as it's now unified with lxc_password

# Static IP variables for master only
variable "k3s_master_ip" {
  description = "Static IP Address for the K3s Master container (in CIDR format, e.g. 192.168.0.211/24), use 'dhcp' for DHCP"
  type        = string
  default     = ""
}


variable "lxc_gateway" {
  description = "Default Gateway for the static IP (e.g. 192.168.0.1)"
  type        = string
  default     = ""
}

variable "cloudflare_tunnel_token" {
  description = "Cloudflare Tunnel Token for cloudflared"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Base domain name for routing (e.g. tuodominio.com)"
  type        = string
}


# variable "protonvpn_private_key" removed as it is no longer used

variable "host_nas_path" {
  description = "Path on the Proxmox host where the Samba NAS is mounted"
  type        = string
}

variable "smb_user" {
  description = "Username for the Samba share"
  type        = string
  sensitive   = true
}

variable "smb_password" {
  description = "Password for the Samba share"
  type        = string
  sensitive   = true
}

variable "nas_address" {
  description = "IP or Hostname of the NAS"
  type        = string
}



variable "nas_share_name" {
  description = "The share name on the NAS (e.g. proxmox)"
  type        = string
  default     = "proxmox"
}

variable "storage_uid" {
  description = "UID for storage permissions"
  type        = string
  default     = "13000"
}

variable "storage_gid" {
  description = "GID for storage permissions"
  type        = string
  default     = "13000"
}
