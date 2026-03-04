variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "container_app_environment_id" {
  type = string
}

variable "revision_mode" {
  type    = string
  default = "Single"
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

variable "target_port" {
  type    = number
  default = 8000
}

variable "allow_insecure_connections" {
  type    = bool
  default = false
}

variable "external_enabled" {
  type    = bool
  default = true
}

variable "min_replicas" {
  type    = number
  default = 1
}

variable "max_replicas" {
  type    = number
  default = 3
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
