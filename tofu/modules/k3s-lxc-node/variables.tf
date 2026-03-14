variable "target_node" { type = string }
variable "hostname" { type = string }
variable "vmid" {
  type    = number
  default = null
}
variable "description" { type = string }
variable "cores" { type = number }
variable "memory" { type = number }
variable "ip_address" { type = string }
variable "gateway" { type = string }
variable "lxc_password" { type = string }
variable "ssh_public_key" { type = string }
variable "template_file_id" { type = string }
variable "datastore_id" { type = string }
variable "nas_path" { type = string }
variable "unprivileged" {
  type    = bool
  default = true
}
variable "nesting" {
  type    = bool
  default = true
}
variable "dns_servers" {
  type    = list(string)
  default = ["1.1.1.1"]
}
