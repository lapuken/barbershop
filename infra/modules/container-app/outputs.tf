output "id" {
  value = azurerm_container_app.this.id
}

output "name" {
  value = azurerm_container_app.this.name
}

output "latest_revision_name" {
  value = azurerm_container_app.this.latest_revision_name
}

output "latest_revision_fqdn" {
  value = "https://${azurerm_container_app.this.latest_revision_fqdn}"
}
