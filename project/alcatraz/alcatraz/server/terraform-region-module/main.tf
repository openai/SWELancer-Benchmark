resource "azurerm_resource_group" "this" {
  name     = "alcatraz-swarm-${var.location}"
  location = var.location
}

resource "azurerm_virtual_network" "this" {
  name = "alcatraz-swarm-vnet-${var.location}"
  address_space = [
    var.vnet_cidr,
  ]

  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
}
resource "azurerm_subnet" "region-workers" {
  name                 = "workers-${var.location}"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.workers_cidr]
}

resource "azurerm_virtual_network_peering" "vnet1_to_vnet2" {
  count    = var.location != "northcentralus" ? 1 : 0
  name                      =  var.location == "westus3" ? "vnet1-to-vnet2" : "vnet1-to-${var.location}" # TODO remove special case for westus3
  resource_group_name       = "alcatraz-swarm-northcentralus"
  virtual_network_name      = "alcatraz-swarm-vnet-northcentralus"
  remote_virtual_network_id = azurerm_virtual_network.this.id
  allow_virtual_network_access = true
  allow_forwarded_traffic   = true
}

resource "azurerm_virtual_network_peering" "vnet2_to_vnet1" {
  count    = var.location != "northcentralus" ? 1 : 0
  name                      = var.location == "westus3" ? "vnet2-to-vnet1" : "${var.location}-to-vnet1" # TODO remove special case for westus3
  resource_group_name       =  azurerm_resource_group.this.name
  remote_virtual_network_id = "/subscriptions/f77ebf0b-8875-4050-b702-696473d0468f/resourceGroups/alcatraz-swarm-northcentralus/providers/Microsoft.Network/virtualNetworks/alcatraz-swarm-vnet-northcentralus"
  virtual_network_name      = azurerm_virtual_network.this.name
  allow_virtual_network_access = true
  allow_forwarded_traffic   = true
}

# resource "azurerm_virtual_network_peering" "alcatraz2_vnet_to_vnet2" { # did this manually
#   name                      =  "alcatraz2-vnet-to-${var.location}"
#   resource_group_name       = "alcatraz-swarm-northcentralus"
#   virtual_network_name      = "preparedness-cyberenv-vnet"
#   remote_virtual_network_id = azurerm_virtual_network.this.id
#   allow_virtual_network_access = true
#   allow_forwarded_traffic   = true
# }

resource "azurerm_virtual_network_peering" "vnet2_to_alcatraz2_vnet" {
  name                      =  "${var.location}-to-alcatraz2-vnet"
  resource_group_name       = azurerm_resource_group.this.name
  virtual_network_name      = azurerm_virtual_network.this.name
  remote_virtual_network_id = "/subscriptions/9fd6537b-4d0d-4e4e-98a1-91491e7cdfad/resourceGroups/alcatraz2-vnet/providers/Microsoft.Network/virtualNetworks/alcatraz2-vnet"
  allow_virtual_network_access = true
  allow_forwarded_traffic   = true
}


resource "azurerm_public_ip" "nat_gateway_ip" {
  name                = "swarm-nat-gateway-ip-${var.location}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_nat_gateway" "this" {
  name                = "swarm-natgateway-${var.location}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku_name            = "Standard"
}

resource "azurerm_nat_gateway_public_ip_association" "this" {
  nat_gateway_id       = azurerm_nat_gateway.this.id
  public_ip_address_id = azurerm_public_ip.nat_gateway_ip.id
}

resource "azurerm_subnet_nat_gateway_association" "worker-assoc" {
  subnet_id      = azurerm_subnet.region-workers.id
  nat_gateway_id = azurerm_nat_gateway.this.id
}

resource "azurerm_network_security_group" "no-internet" {
  name                = "swarm-vmss-nsg-${var.location}-no-internet"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  security_rule {
    name                       = "Deny-All-Inbound"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Deny-All-Outbound"
    priority                   = 1000
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
resource "azurerm_network_security_group" "this" {
  name                = "swarm-vmss-nsg-${var.location}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name

  security_rule {
    name                       = "SSH"
    description                = ""
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AppPort"
    description                = ""
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "VNCPort"
    description                = ""
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "6080"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "CodeServer"
    description                = ""
    priority                   = 1004
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    count = var.sku == "Standard_D2s_v5"
  }
}

resource "azurerm_linux_virtual_machine_scale_set" "this" {
  for_each = { for ss in var.scale_sets : ss.name => ss }
  name                = "${var.location}-${each.value.name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = each.value.sku
  instances           = 3
  lifecycle {
    ignore_changes = [
      instances, # handled by autoscale.py
      os_disk[0].disk_size_gb,
      zones,
      data_disk,
    ]
  }
  admin_username      = "azureuser"
  computer_name_prefix = "alcatrazs"
  overprovision       = false
  single_placement_group = false
  upgrade_mode        = "Manual"

  source_image_id = "/subscriptions/f77ebf0b-8875-4050-b702-696473d0468f/resourceGroups/alcatraz-swarm/providers/Microsoft.Compute/galleries/alcatrazgallery/images/swarm-ubuntu-worker"

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 30
  }

  network_interface {
    name    = "alcatraz-swarm-vnet-nic01"
    primary = true
    # network_security_group_id = azurerm_network_security_group.this.id
    network_security_group_id = each.value.sku == "Standard_D2s_v5" ? azurerm_network_security_group.no-internet.id : null 
    ip_configuration {
      name      = "IPConfiguration"
      primary   = true
      subnet_id = azurerm_subnet.region-workers.id
    }
  }

  identity {
    type = "UserAssigned"
    identity_ids = [
      "/subscriptions/f77ebf0b-8875-4050-b702-696473d0468f/resourceGroups/alcatraz-swarm/providers/Microsoft.ManagedIdentity/userAssignedIdentities/alcatraz-swarm-worker-identity"
    ]
  }

  admin_ssh_key {
    username   = "azureuser"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDQLQl+akEZrcVPvgpiH9IzOknBfdajbIdQxQzbZZvCr7veMIrkjwUJX5+ojpAo2lC/lNQe1NNluuCILV5bVkCyvIQL8JIuGQtaFnDPMcWJP9Pe+PPFo7M2yOsMiIFjsQxuV3tFJqfjHoplSmLMbG6X1We1QquRGLg4jddTr9DvZOyjeNvDJQ9tbNIj1LePFd3Fw9Dq+XMxZHmWpGmEzaS9vdG1hIAuiWdAyhkG+gQZu4irl4el9vaJFK6dnZ4FStUkexQXAdv6OttG1X/M9NzYM4NiLy2hWvhrXns8j6dgLteQz7Ol2f+8OZTELaNmiBPZp7fiIkZXExPkA3nxtnDz7wGh9mAeGqunwqsila4jjpHdynvKJ0jU8Ddj1c0DeO/JEcQ/EawxIkmnBE+yrlTsy0G7GgrLk7O+mOnlx7War9NS17+0oqEdLlinxSMT2hm83zWjVcmyZtEiNVolJZzmEMe29vjYlM0+xT4QanIEGDh5RWKANph9Gs2HJlEMpjU= evanmays@oai-evanmays"
  }

  # scale_in_policy {
  #   rules = ["Default"]
  # }
}

# resource "azurerm_network_security_group" "proxy_nsg" {
#   name                = "pls-nsg-${var.location}"
#   location            = azurerm_resource_group.this.location
#   resource_group_name = azurerm_resource_group.this.name

#   # security_rule {
#   #   name                       = "Allow-Internal-Subnet"
#   #   priority                   = 100
#   #   direction                  = "Inbound"
#   #   access                     = "Allow"
#   #   protocol                   = "Tcp"
#   #   source_port_range          = "*"
#   #   destination_port_range     = "*"
#   #   source_address_prefix      = azurerm_subnet.region-proxy.address_prefixes[0]
#   #   destination_address_prefix = azurerm_subnet.region-proxy.address_prefixes[0]
#   # }

#   # security_rule {
#   #   name                       = "Allow-PLS-Subnet"
#   #   priority                   = 101
#   #   direction                  = "Inbound"
#   #   access                     = "Allow"
#   #   protocol                   = "Tcp"
#   #   source_port_range          = "*"
#   #   destination_port_range     = "*"
#   #   source_address_prefix      = azurerm_subnet.region-pls.address_prefixes[0]
#   #   destination_address_prefix = "*"
#   # }

#   security_rule {
#     name                       = "Deny-All-Other-Inbound"
#     priority                   = 200
#     direction                  = "Inbound"
#     access                     = "Allow"
#     protocol                   = "Tcp"
#     source_port_range          = "*"
#     destination_port_range     = "*"
#     source_address_prefix      = "*"
#     destination_address_prefix = "*"
#   }
# }

# resource "azurerm_subnet_network_security_group_association" "pls_subnet_nsg" {
#   subnet_id                 = azurerm_subnet.region-proxy.id
#   network_security_group_id = azurerm_network_security_group.proxy_nsg.id
# }
