variable "location" {
  type = string
  description = "Azure region"
}

variable "vnet_cidr" {
  type = string
}

variable "workers_cidr" {
  type = string
}

variable "subscription_id" {
  type = string
}

variable "scale_sets" {
  description = "List of scale set configurations"
  type = list(object({
    name         = string
    sku          = string
  }))
}