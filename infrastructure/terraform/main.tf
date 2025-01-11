resource "upcloud_router" "md-router" {
  name = "md-router"
}

resource "upcloud_network" "md-network" {
  name = "md-network"
  zone = "fi-hel2"

  ip_network {
    address            = "10.0.0.0/24"
    dhcp               = true
    dhcp_default_route = false
    family             = "IPv4"
    gateway            = "10.0.0.1"
  }

  router = upcloud_router.md-router.id
}

resource "upcloud_server" "md-dagster" {
  hostname = "md-dagster"
  zone     = "fi-hel2"
  plan     = "DEV-1xCPU-2GB"
  metadata = true
  firewall = true

  template {
    storage = "Ubuntu Server 24.04 LTS (Noble Numbat)"
    size    = 30

    # backup_rule {
    #   interval  = "daily"
    #   time      = "0100"
    #   retention = 8
    # }
  }

  network_interface {
    type = "public"
  }

  network_interface {
    type    = "private"
    network = upcloud_network.md-network.id
  }

  labels = {
    env        = "dev"
    production = "false"
  }

  login {
    user = "dagster"

    keys = [
      file("../.ssh/id_ed25519.pub")
    ]
  }
}
