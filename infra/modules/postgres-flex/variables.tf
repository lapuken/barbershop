variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "postgres_version" {
  type    = string
  default = "16"
}

variable "administrator_login" {
  type = string
}

variable "administrator_password" {
  type      = string
  sensitive = true
}

variable "database_name" {
  type = string
}

variable "storage_mb" {
  type    = number
  default = 32768
}

variable "sku_name" {
  type = string
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

variable "public_network_access_enabled" {
  type    = bool
  default = true
}

variable "zone" {
  type    = string
  default = "1"
}

variable "firewall_rules" {
  type = map(object({
    start_ip_address = string
    end_ip_address   = string
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
