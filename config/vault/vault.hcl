# HashiCorp Vault Configuration for Algorithmic Trading System
# Production-ready configuration with security best practices

# Storage backend - using file storage for development/testing
# In production, consider using Consul, etcd, or cloud storage
storage "file" {
  path = "/vault/data"
}

# Listener configuration
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = true  # Set to false in production with proper certificates
  # tls_cert_file = "/vault/config/vault.crt"
  # tls_key_file  = "/vault/config/vault.key"
  # tls_min_version = "tls12"
}

# API address
api_addr = "http://127.0.0.1:8200"

# Cluster address (for HA setups)
cluster_addr = "http://127.0.0.1:8201"

# UI configuration
ui = true

# Logging
log_level = "INFO"
log_format = "json"
log_file = "/vault/logs/vault.log"
log_rotate_duration = "24h"
log_rotate_max_files = 30

# Disable mlock for development (enable in production)
disable_mlock = true

# Default lease TTL and max lease TTL
default_lease_ttl = "768h"  # 32 days
max_lease_ttl = "8760h"     # 365 days

# Plugin directory
plugin_directory = "/vault/plugins"

# Telemetry configuration
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = true
  enable_hostname_label = false
  
  # StatsD configuration (optional)
  # statsd_address = "localhost:8125"
  
  # Circonus configuration (optional)
  # circonus_api_token = "your-circonus-api-token"
  # circonus_api_app = "vault"
  # circonus_api_url = "https://api.circonus.com/v2"
  # circonus_submission_interval = "10s"
  # circonus_submission_url = "https://trap.noit.circonus.net/module/httptrap/check-id/secret"
  # circonus_check_id = "your-check-id"
  # circonus_check_force_metric_activation = "true"
  # circonus_check_instance_id = "vault:production"
  # circonus_check_search_tag = "service:vault"
  # circonus_check_display_name = "Vault Production"
  # circonus_check_tags = "environment:production,service:vault"
  # circonus_broker_id = "your-broker-id"
  # circonus_broker_select_tag = "datacenter:primary"
}

# Entropy configuration for better randomness
entropy "seal" {
  mode = "augmentation"
}

# Seal configuration (for auto-unseal in production)
# seal "awskms" {
#   region     = "us-west-2"
#   kms_key_id = "your-kms-key-id"
# }

# seal "azurekeyvault" {
#   tenant_id      = "your-tenant-id"
#   client_id      = "your-client-id"
#   client_secret  = "your-client-secret"
#   vault_name     = "your-key-vault-name"
#   key_name       = "your-key-name"
# }

# seal "gcpckms" {
#   project     = "your-gcp-project"
#   region      = "global"
#   key_ring    = "your-key-ring"
#   crypto_key  = "your-crypto-key"
# }

# Performance and caching
cache_size = "32000"

# Disable clustering for single-node setup
disable_clustering = false

# Raw storage endpoint (disable in production)
raw_storage_endpoint = false

# Introspection endpoint (disable in production)
introspection_endpoint = false

# Disable sentry error reporting
disable_sentry = true

# Disable performance standby
disable_performance_standby = false

# License path (for Vault Enterprise)
# license_path = "/vault/config/vault.hclic"

# Service registration (for service discovery)
# service_registration "consul" {
#   address = "127.0.0.1:8500"
#   service = "vault"
#   service_tags = "trading,secrets"
#   service_address = "127.0.0.1"
# }

# High availability configuration
# ha_storage "consul" {
#   address = "127.0.0.1:8500"
#   path    = "vault/"
#   service = "vault"
#   service_tags = "trading,secrets,ha"
# }

# Replication configuration (Vault Enterprise)
# replication {
#   performance {
#     token = "your-performance-replication-token"
#   }
#   dr {
#     token = "your-dr-replication-token"
#   }
# }

# Sentinel policies (Vault Enterprise)
# sentinel {
#   additional_enabled_modules = []
# }

# Transform secrets engine configuration (Vault Enterprise)
# transform {
#   role "trading-data" {
#     transformations = ["ssn-transform", "credit-card-transform"]
#   }
# }

# KMIP secrets engine configuration (Vault Enterprise)
# kmip {
#   listen_addrs = ["0.0.0.0:5696"]
#   tls_ca_key_type = "rsa"
#   tls_ca_key_bits = 2048
#   default_tls_client_key_type = "rsa"
#   default_tls_client_key_bits = 2048
#   default_tls_client_ttl = "24h"
# }

# Administrative namespace (Vault Enterprise)
# administrative_namespace_path = "admin/"

# Custom response headers
# custom_response_headers {
#   "X-Custom-Header" = "Trading-System"
#   "X-Vault-Cluster" = "production"
# }

# User lockout configuration
user_lockout {
  threshold = 5
  duration = "10m"
  counter_reset_duration = "10m"
  disable_lockout = false
}

# Request limiter
api_rate_limit {
  rate = 1000
  burst = 1000
  # path_rate_limits {
  #   "/v1/auth/userpass/login" {
  #     rate = 100
  #     burst = 100
  #   }
  # }
}

# Experiments (for testing new features)
# experiments = ["events.alpha1"]

# Imprecise request counting
detect_deadlocks = "statelock"

# Activity log configuration
activity_log {
  enabled = true
  default_report_months = 12
}

# Audit device configuration will be set via API after initialization
# audit {
#   file {
#     file_path = "/vault/logs/audit.log"
#     log_raw = false
#     hmac_accessor = true
#     mode = "0600"
#     format = "json"
#   }
# }

# Secrets engines will be mounted via API after initialization
# mount {
#   path = "trading/"
#   type = "kv-v2"
#   description = "Trading system secrets"
#   config {
#     max_versions = 10
#     cas_required = false
#     delete_version_after = "0s"
#   }
# }

# Auth methods will be enabled via API after initialization
# auth {
#   path = "userpass/"
#   type = "userpass"
#   description = "Username and password authentication"
# }

# Policies will be created via API after initialization
# policy {
#   name = "trading-admin"
#   policy = file("/vault/config/policies/trading-admin.hcl")
# }

# Database secrets engine configuration
# database {
#   postgresql {
#     plugin_name = "postgresql-database-plugin"
#     connection_url = "postgresql://{{username}}:{{password}}@postgres:5432/trading?sslmode=disable"
#     allowed_roles = "trading-readonly,trading-readwrite"
#     username = "vault"
#     password = "vault-password"
#   }
# }

# PKI secrets engine configuration
# pki {
#   root_ca {
#     common_name = "Trading System Root CA"
#     ttl = "87600h"  # 10 years
#     key_type = "rsa"
#     key_bits = 4096
#   }
#   intermediate_ca {
#     common_name = "Trading System Intermediate CA"
#     ttl = "43800h"  # 5 years
#     key_type = "rsa"
#     key_bits = 2048
#   }
# }

# Transit secrets engine for encryption as a service
# transit {
#   keys {
#     "trading-data" {
#       type = "aes256-gcm96"
#       deletion_allowed = false
#       exportable = false
#     }
#     "pii-data" {
#       type = "rsa-4096"
#       deletion_allowed = false
#       exportable = false
#     }
#   }
# }