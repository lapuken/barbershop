variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "create_federated_credential" {
  type    = bool
  default = false
}

variable "federated_credential_name" {
  type    = string
  default = "github"
}

variable "federated_issuer" {
  type    = string
  default = "https://token.actions.githubusercontent.com"
}

variable "federated_subject" {
  type    = string
  default = ""
}

variable "federated_audiences" {
  type    = list(string)
  default = ["api://AzureADTokenExchange"]
}
