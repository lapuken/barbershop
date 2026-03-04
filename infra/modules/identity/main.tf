resource "azurerm_user_assigned_identity" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "this" {
  count               = var.create_federated_credential ? 1 : 0
  name                = var.federated_credential_name
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.this.id
  audience            = var.federated_audiences
  issuer              = var.federated_issuer
  subject             = var.federated_subject
}
