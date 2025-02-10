terraform {
  cloud {
    organization = "openai_inc"

    workspaces {
      name = "preparedness-autonenv"
    }
  }
}

provider "azurerm" {
  features {}
  tenant_id       = var.azure_tenant
  subscription_id = var.azure_subscription_id
}

variable "azure_subscription_id" {
  default = "f77ebf0b-8875-4050-b702-696473d0468f"
}

variable "azure_tenant" {
  type    = string
  default = "a48cca56-e6da-484e-a814-9c849652bcb3"
}

resource "azurerm_resource_group" "rg" {
  name     = "alcatraz-swarm"
  location = "northcentralus"
}


resource "azurerm_virtual_network" "example" {
  name = "preparedness-autonenv-vnet"
  address_space = [
    "10.213.0.0/18",
  ]

  location            = azurerm_resource_group.rg.location
  resource_group_name = "preparedness-autonenv-vnet"
  subnet {
    address_prefix = "10.213.0.0/26"
    name           = "utils"
    security_group = ""
  }
  subnet {
    address_prefix = "10.213.0.64/26"
    name           = "common"
    security_group = ""
  }
  # subnet {
  #   address_prefix = "10.213.0.128/26"
  #   name           = "pls"
  #   id  = azurerm_subnet.pls.id
  #   security_group = ""
  # }
  lifecycle {
    ignore_changes = [
      subnet,  # TODO terraform seems to dislike that some subnets are nested and others are azurerm_subnet
    ]
  }
  subnet {
    address_prefix = "10.213.32.0/19"
    name           = "workers"
  }
}
resource "azurerm_subnet" "pls" {
  name                 = "pls"
  resource_group_name  = azurerm_virtual_network.example.resource_group_name
  virtual_network_name = azurerm_virtual_network.example.name
  address_prefixes     = ["10.213.0.128/26"]
  private_link_service_network_policies_enabled = false
}

# Public DNS zone used for ssl certs
resource "azurerm_dns_zone" "alcatraz" {
  name                = "alcatraz.openai.org"
  resource_group_name = azurerm_virtual_network.example.resource_group_name
}


resource "azurerm_dns_txt_record" "acme_challenge" {
  name                = "_acme-challenge"
  zone_name           = azurerm_dns_zone.alcatraz.name
  resource_group_name = azurerm_dns_zone.alcatraz.resource_group_name
  ttl                 = 300
  record {
    value = "51jdIPZRYvoUCIHGbOtXywvYPGHsqBUYpn8MSZ9HI0Y"
  }
}

resource "azurerm_dns_txt_record" "acme_challenge_portforward" {
  name                = "_acme-challenge.port-forward"
  zone_name           = azurerm_dns_zone.alcatraz.name
  resource_group_name = azurerm_dns_zone.alcatraz.resource_group_name
  ttl                 = 300
  record {
    value = "Hk-AOp6RcLU0ATMn3EpDnAn3YuEA8d6nCTOPB7aRkPI"
  }
}

# DNS zone (useful for Tailscale DNS)
resource "azurerm_private_dns_zone" "alcatraz" {
  name                = "alcatraz.openai.org"
  resource_group_name = azurerm_virtual_network.example.resource_group_name
}

### \# A record for swarm-proxy.alcatraz.openai.org
resource "azurerm_private_dns_a_record" "swarm_proxy" {
  name                = "swarm-proxy"
  zone_name           = azurerm_private_dns_zone.alcatraz.name
  resource_group_name = azurerm_virtual_network.example.resource_group_name
  ttl                 = 300
  records             = ["10.213.0.133"]
}

### \# A record for swarm-api-server.alcatraz.openai.org
resource "azurerm_private_dns_a_record" "swarm_api_server" {
  name                = "swarm-api-server"
  zone_name           = azurerm_private_dns_zone.alcatraz.name
  resource_group_name = azurerm_virtual_network.example.resource_group_name
  ttl                 = 300
  records             = ["10.213.0.80"]
}

### \# A record for port-forward.alcatraz.openai.org
resource "azurerm_private_dns_a_record" "port_forward_server" {
  name                = "port-forward"
  zone_name           = azurerm_private_dns_zone.alcatraz.name
  resource_group_name = azurerm_virtual_network.example.resource_group_name
  ttl                 = 300
  records             = ["10.211.128.69"]
}

### \# A record for *.port-forward.alcatraz.openai.org
resource "azurerm_private_dns_a_record" "port_forward_server_catchall" {
  name                = "*.port-forward"
  zone_name           = azurerm_private_dns_zone.alcatraz.name
  resource_group_name = azurerm_virtual_network.example.resource_group_name
  ttl                 = 300
  records             = ["10.211.128.69"]
}

resource "azurerm_virtual_machine" "swarm_api_server" {
  name                  = "swarm-api-server"
  location              = "northcentralus"
  resource_group_name   = "alcatraz-swarm"
  network_interface_ids = [azurerm_network_interface.swarm_api_server_nic.id]
  vm_size               = "Standard_D48as_v4"
  storage_os_disk {
    name              = "osdisk"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  storage_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
  }

  os_profile {
    computer_name = "swarm-api-server"
    admin_username = "azureuser"
  }

  os_profile_linux_config {
    disable_password_authentication = true
    ssh_keys {
      path     = "/home/azureuser/.ssh/authorized_keys"
      key_data = file("~/.ssh/id_rsa.pub")
    }
  }
  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "vm_contributor_swarm_api_server" {
  scope                = "/subscriptions/${var.azure_subscription_id}"
  role_definition_name = "Virtual Machine Contributor"
  principal_id         = azurerm_virtual_machine.swarm_api_server.identity[0].principal_id
}

resource "azurerm_role_assignment" "rg_reader_swarm_api_server" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Reader"
  principal_id         = azurerm_virtual_machine.swarm_api_server.identity[0].principal_id
}

resource "azurerm_role_assignment" "managed_identity_operator_swarm_api_server" {
  scope                = azurerm_user_assigned_identity.vmss_identity.id
  role_definition_name = "Managed Identity Operator"
  principal_id         = azurerm_virtual_machine.swarm_api_server.identity[0].principal_id
}


#
# API Server
#

resource "azurerm_public_ip" "swarm_api_server_pip" {
  name                = "swarm-pip"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm"
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "swarm_api_server_nic" {
  name                = "swarm-nic"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm"

  ip_configuration {
    name                          = "internal"
    subnet_id                     = "${azurerm_virtual_network.example.id}/subnets/common"
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.213.0.80"
    public_ip_address_id          = "${azurerm_public_ip.swarm_api_server_pip.id}"
  }
}

resource "azurerm_network_security_group" "swarm_nsg" {
  name                = "swarm-api-server-nsg"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm"

  security_rule {
    name                       = "AllowOutboundInternet"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  security_rule {
    name                       = "DenyInboundInternet"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface_security_group_association" "swarm_nic_nsg" {
  network_interface_id      = azurerm_network_interface.swarm_api_server_nic.id
  network_security_group_id = azurerm_network_security_group.swarm_nsg.id
}

resource "azurerm_lb" "swarm-api-server-lb" {
  name                = "swarm-api-server-lb"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Standard"

  frontend_ip_configuration {
    name = "internal"
    subnet_id                     = "${azurerm_virtual_network.example.id}/subnets/common"
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.213.0.81"
  }
}

resource "azurerm_lb_backend_address_pool" "swarm_api_server_pool" {
  loadbalancer_id = azurerm_lb.swarm-api-server-lb.id
  name            = "backend-pool"
  
}

resource "azurerm_lb_rule" "swarm_api_server_http_rule" {
  loadbalancer_id            = azurerm_lb.swarm-api-server-lb.id
  name                       = "http"
  protocol                   = "Tcp"
  frontend_port              = 80
  backend_port               = 80
  frontend_ip_configuration_name = azurerm_lb.swarm-api-server-lb.frontend_ip_configuration[0].name
  backend_address_pool_ids   = [azurerm_lb_backend_address_pool.swarm_api_server_pool.id]
}

resource "azurerm_lb_rule" "swarm_api_server_ssh_rule" {
  loadbalancer_id            = azurerm_lb.swarm-api-server-lb.id
  name                       = "ssh"
  protocol                   = "Tcp"
  frontend_port              = 23 # research cluster blocks 22
  backend_port               = 22
  frontend_ip_configuration_name = azurerm_lb.swarm-api-server-lb.frontend_ip_configuration[0].name
  backend_address_pool_ids   = [azurerm_lb_backend_address_pool.swarm_api_server_pool.id]
}

resource "azurerm_private_link_service" "swarm_api_server_pls" {
  name                = "swarm-api-server-pls"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # auto_approval_subscription_ids = [
  #   var.azure_subscription_id,
  # ]

  # visibility_subscription_ids = [
  #   var.azure_subscription_id,
  # ]

  nat_ip_configuration {
    name                         = "swarm-pls-ipconfig"
    primary                      = true
    subnet_id                    = azurerm_subnet.pls.id
    private_ip_address_version   = "IPv4"
  }

  load_balancer_frontend_ip_configuration_ids = [
    azurerm_lb.swarm-api-server-lb.frontend_ip_configuration[0].id,
  ]
}

resource "azurerm_user_assigned_identity" "vmss_identity" {
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  name                = "alcatraz-swarm-worker-identity"
}

resource "azurerm_container_registry" "acr" {
  name                = "alcatrazswarmcontainers"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Premium"
  admin_enabled       = false
}

resource "azurerm_container_registry" "teammate_acr" {
  name                = "oaiteammatecontainers"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Premium"
  admin_enabled       = true
}


resource "azurerm_role_assignment" "vmss_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.vmss_identity.principal_id
}

resource "azurerm_role_assignment" "harmony_swarmcontainers_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = "462fdb4f-4efe-464c-966b-d97a8f94443e"  # harmony
}

resource "azurerm_role_assignment" "baogang_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = "62207ad4-15ed-4657-a30d-882a324a810e"  # baogang-user
}

resource "azurerm_role_assignment" "dc_evals_containers" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "Contributor"
  principal_id         = "c5bc72dc-fd98-42a5-84f6-f5c704443099"  # dc-evals-slack
}

resource "azurerm_role_assignment" "dc_evals_containers2" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = "c5bc72dc-fd98-42a5-84f6-f5c704443099"  # dc-evals-slack
}


resource "azurerm_role_assignment" "vmss_acr_pull_teammate" {
  scope                = azurerm_container_registry.teammate_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.vmss_identity.principal_id
}

resource "azurerm_role_assignment" "acr_teammate_contributors" {
  scope                = azurerm_container_registry.teammate_acr.id
  role_definition_name = "Contributor"
  principal_id         = "462fdb4f-4efe-464c-966b-d97a8f94443e"  # harmony
}

resource "azurerm_role_assignment" "acr_teammate_preparedness_read" {
  scope                = azurerm_container_registry.teammate_acr.id
  role_definition_name = "AcrPull"
  principal_id         = "91365953-3883-4374-9b5c-0ee1edead660" # preparednessx-contributors
}


resource "azurerm_private_endpoint" "set99" {
  name                = "swarm-pls-northcentralus-set99-privatelink"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = "${azurerm_virtual_network.example.id}/subnets/pls"

  private_service_connection {
    name                           = "connect-swarm-pls-northcentralus-alcatraz-swarm-set99"
    is_manual_connection           = false
    private_connection_resource_id = "/subscriptions/f77ebf0b-8875-4050-b702-696473d0468f/resourceGroups/alcatraz-swarm-northcentralus/providers/Microsoft.Network/privateLinkServices/swarm-pls-northcentralus-alcatraz-swarm-set99"
  }
}

#
# Proxy Section Start
#

resource "azurerm_subnet" "region-proxy" {
  name                 = "proxy-northcentralus"
  resource_group_name  = "alcatraz-swarm-northcentralus"
  virtual_network_name = "alcatraz-swarm-vnet-northcentralus"
  address_prefixes     = ["10.213.0.0/26"]
  private_link_service_network_policies_enabled = false
}

variable "proxy_instances" {
  type        = map(any)
  default     = {
    "proxy0" = "10.213.0.30"
    "proxy1" = "10.213.0.31"
    "proxy2" = "10.213.0.32"
    "proxy3" = "10.213.0.33"
    "proxy4" = "10.213.0.34"
    "proxy5" = "10.213.0.35"
    "proxy6" = "10.213.0.36"
    "proxy7" = "10.213.0.37"
    "proxy8" = "10.213.0.38"
    "proxy9" = "10.213.0.39"
    "proxy10" = "10.213.0.40"
    "proxy11" = "10.213.0.41"
    "proxy12" = "10.213.0.42"
  }
}

resource "azurerm_network_interface" "proxy_vm_nic" {
  for_each            = var.proxy_instances
  name                = "${each.key}-nic-northcentralus"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm-northcentralus"

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.region-proxy.id
    private_ip_address_allocation = "Static"
    private_ip_address            = each.value
  }
}
resource "azurerm_network_interface_backend_address_pool_association" "example" {
  for_each                   = var.proxy_instances
  # use the below so you can add new VMs and deploy code to them before load balancer sees them. but actually the pools are shared with ssh and http so maybe not... Well load balancer surely would check healthprobe BEFORE adding new VM to pool RIGHT??. Well actually you still need the below when you need to expand the ssh port range
  # for_each                   = { for k in ["proxy0", "proxy1", "proxy2", "proxy3", "proxy4", "proxy5", "proxy6"] : k => var.proxy_instances[k] }

  network_interface_id       = azurerm_network_interface.proxy_vm_nic[each.key].id
  ip_configuration_name      = "internal"
  backend_address_pool_id    = azurerm_lb_backend_address_pool.proxy.id
}

resource "azurerm_linux_virtual_machine" "proxy" {
  for_each            = var.proxy_instances
  name                = "${each.key}-northcentralus"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm-northcentralus"
  size                = "Standard_D4s_v3"
  admin_username      = "azureuser"
  network_interface_ids = [azurerm_network_interface.proxy_vm_nic[each.key].id]

  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "22.04.202210180"
  }
}

resource "azurerm_lb_backend_address_pool" "proxy" {
  loadbalancer_id     = azurerm_lb.proxy.id
  name                = "proxy-bep"
}

resource "azurerm_lb_rule" "this" {
  name                           = "proxy-http-rule"
  loadbalancer_id                = azurerm_lb.proxy.id
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = azurerm_lb.proxy.frontend_ip_configuration[0].name
  backend_address_pool_ids        = [azurerm_lb_backend_address_pool.proxy.id]
  probe_id                       = azurerm_lb_probe.this.id
}

resource "azurerm_lb_nat_rule" "proxy-ssh" {
  name                = "proxy-ssh-natrule"
  loadbalancer_id     = azurerm_lb.proxy.id
  resource_group_name = "alcatraz-swarm-northcentralus"
  protocol            = "Tcp"
  frontend_port_start = 24
  frontend_port_end   = 40
  backend_address_pool_id  = azurerm_lb_backend_address_pool.proxy.id
  backend_port        = 22
  frontend_ip_configuration_name = azurerm_lb.proxy.frontend_ip_configuration[0].name
}

resource "azurerm_lb_probe" "this" {
  name                = "appservice-health-probe"
  loadbalancer_id     = azurerm_lb.proxy.id
  protocol            = "Tcp"
  port                = 80
  interval_in_seconds = 5
}

resource "azurerm_lb" "proxy" {
  name                = "swarm-workers-lb-northcentralus-alcatraz-swarm-set99"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm-northcentralus"
  sku                 = "Standard"

  frontend_ip_configuration {
    name = "alcatraz-swarm-set99-internal-frontend"
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.region-proxy.id
  }
}

resource "azurerm_subnet" "region-pls" {
  name                 = "pls-northcentralus"
  resource_group_name  = "alcatraz-swarm-northcentralus"
  virtual_network_name = "alcatraz-swarm-vnet-northcentralus"
  address_prefixes     = ["10.213.0.64/26"]
  private_link_service_network_policies_enabled = false
}

resource "azurerm_private_link_service" "proxy" {
  name                = "swarm-pls-northcentralus-alcatraz-swarm-set99"
  location            = "northcentralus"
  resource_group_name = "alcatraz-swarm-northcentralus"

  nat_ip_configuration {
    name                         = "worker-lb-pls-ip-configuration"
    primary                      = true
    subnet_id                    = azurerm_subnet.region-pls.id
    private_ip_address_version   = "IPv4"
  }

  load_balancer_frontend_ip_configuration_ids = [
    azurerm_lb.proxy.frontend_ip_configuration[0].id,
  ]
}

resource "azurerm_subnet_nat_gateway_association" "pls-assoc" {
  subnet_id      = azurerm_subnet.region-proxy.id
  nat_gateway_id = "/subscriptions/f77ebf0b-8875-4050-b702-696473d0468f/resourceGroups/alcatraz-swarm-northcentralus/providers/Microsoft.Network/natGateways/swarm-natgateway-northcentralus"
}

#
# Proxy Section End
#

resource "azurerm_shared_image_gallery" "this" {
  name                = "alcatrazgallery"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  description         = ""
}

resource "azurerm_shared_image_version" "this" {
  name                = "0.0.0"
  image_name          = azurerm_shared_image.this.name
  gallery_name        = azurerm_shared_image_gallery.this.name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  managed_image_id    = "/subscriptions/f77ebf0b-8875-4050-b702-696473d0468f/resourceGroups/alcatraz-swarm/providers/Microsoft.Compute/images/SwarmUbuntu-v62"
  target_region {
    name                   = "northcentralus"
    regional_replica_count = 3
  }
  target_region {
    name                   = "westus"
    regional_replica_count = 3
  }
  target_region {
    name                   = "westus3"
    regional_replica_count = 3
  }
}

resource "azurerm_shared_image" "this" {
  name                = "swarm-ubuntu-worker"
  gallery_name        = azurerm_shared_image_gallery.this.name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  hyper_v_generation  = "V2"

  identifier {
    publisher = "alcatraz"
    offer     = "worker"
    sku       = "worker"
  }
}


module "region-northcentralus" {
  source = "./terraform-region-module"
  location = "northcentralus"
  subscription_id = var.azure_subscription_id
  vnet_cidr = "10.213.0.0/18"
  workers_cidr = "10.213.32.0/19"
  # pls_cidr = "10.213.0.64/26"
  # proxy_cidr = "10.213.0.0/26"
  scale_sets = [
    {
      name           = "set-red"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-blue"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-green"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-gold"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-silver"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-black"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-white"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "alcatraz-swarm-set99"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-t4-pink"
      sku            = "Standard_NC4as_T4_v3"
    },
  ]
}

module "region-westus3" {
  source = "./terraform-region-module"
  location = "westus3"
  subscription_id = var.azure_subscription_id
  vnet_cidr = "10.213.64.0/18"
  workers_cidr = "10.213.96.0/19"
  scale_sets = [ # named after cities in arizona since westus3 is in Arizona
    {
      name           = "set-phoenix"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-mesa"
      sku            = "Standard_NC4as_T4_v3"
    },
  ]
}

module "region-westus" {
  source = "./terraform-region-module"
  location = "westus"
  subscription_id = var.azure_subscription_id
  vnet_cidr = "10.213.128.0/18"
  workers_cidr = "10.213.160.0/19"
  scale_sets = [ # named after neighborhoods in San Francisco since westus is in San Francisco
    {
      name           = "set-nobhill"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-mission"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-marina"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-southbeach"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-colevalley"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-chinatown"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-japantown"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-soma"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-castro"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-fidi"
      sku            = "Standard_D2as_v4"
    },
    {
      name           = "set-northbeach"
      sku            = "Standard_D2s_v5"
    },
  ]
}