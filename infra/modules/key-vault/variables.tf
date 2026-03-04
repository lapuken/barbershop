variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "sku_name" {
  type    = string
  default = "standard"
}

variable "soft_delete_retention_days" {
  type    = number
  default = 30
}

variable "purge_protection_enabled" {
  type    = bool
  default = true
}

variable "enable_rbac_authorization" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
