resource "upcloud_managed_object_storage" "md-object-storage" {
  name              = "md-object-storage"
  region            = "europe-1"
  configured_status = "started"

  network {
    family = "IPv4"
    name   = "public"
    type   = "public"
  }

  network {
    family = "IPv4"
    name   = "md-network"
    type   = "private"
    uuid   = upcloud_network.md-network.id
  }

  labels = {
    managed-by = "terraform"
  }
}

resource "upcloud_managed_object_storage_bucket" "md-raw-data" {
  service_uuid = upcloud_managed_object_storage.md-object-storage.id
  name         = "md-raw-data"
}

resource "upcloud_managed_object_storage_bucket" "processed-data" {
  service_uuid = upcloud_managed_object_storage.md-object-storage.id
  name         = "processed-data"
}

resource "upcloud_managed_object_storage_user" "md-raw-data" {
  username     = "md-raw-data"
  service_uuid = upcloud_managed_object_storage.md-object-storage.id
}

resource "upcloud_managed_object_storage_user_access_key" "md-raw-data" {
  username     = upcloud_managed_object_storage_user.md-raw-data.username
  service_uuid = upcloud_managed_object_storage.md-object-storage.id
  status       = "Active"
}

resource "upcloud_managed_object_storage_user_policy" "md-raw-data-full-access" {
  username     = upcloud_managed_object_storage_user.md-raw-data.username
  service_uuid = upcloud_managed_object_storage.md-object-storage.id
  name         = "ECSS3FullAccess"
}
