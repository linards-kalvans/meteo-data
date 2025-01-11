terraform {
  required_providers {
    upcloud = {
      source  = "UpCloudLtd/upcloud"
      version = ">= 5.0"
    }
  }
  cloud {
    organization = "meteo-data"

    workspaces {
      name = "md-upcloud"
    }
  }
}

provider "upcloud" {}

