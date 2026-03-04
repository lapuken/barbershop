variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "container_app_environment_id" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "user_assigned_identity_ids" {
  type = list(string)
}

variable "registry_server" {
  type = string
}

variable "registry_identity_id" {
  type = string
}

variable "image" {
  type = string
}

variable "cpu" {
  type    = number
  default = 0.5
}

variable "memory" {
  type    = string
  default = "1Gi"
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "secret_environment_variables" {
  type    = map(string)
  default = {}
}

variable "key_vault_secrets" {
  type = map(object({
    identity            = string
    key_vault_secret_id = string
  }))
  default = {}
}

variable "command" {
  type    = list(string)
  default = []
}

variable "args" {
  type    = list(string)
  default = []
}
