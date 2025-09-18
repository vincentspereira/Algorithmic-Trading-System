param(
    [string]$Environment = "development",
    [switch]$InitializeServices,
    [switch]$SkipHealthChecks,
    [int]$HealthCheckTimeout = 120
)

$COMPOSE_FILE = "docker\docker-compose.infrastructure.yml"
$PROJECT_NAME = "trading-infrastructure"

$HEALTH_CHECK_ENDPOINTS = @{
    "influxdb" = "http://localhost:8086/health"
    "loki" = "http://localhost:3100/ready"
    "jaeger" = "http://localhost:14269/"
    "vault" = "http://localhost:8200/v1/sys/health"
    "minio" = "http://localhost:9000/minio/health/live"
    "spark-master" = "http://localhost:8080/"
    "traefik" = "http://localhost:8080/api/rawdata"
}

function Write-Success { param([string]$Message) Write-Host $Message -ForegroundColor Green }
function Write-Info { param([string]$Message) Write-Host $Message -ForegroundColor Cyan }
function Write-Warning { param([string]$Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host $Message -ForegroundColor Red }

Write-Info "=== Deploying Trading Infrastructure ==="
Write-Info "Environment: $Environment"
Write-Info "Compose File: $COMPOSE_FILE"
Write-Info "Project Name: $PROJECT_NAME"
Write-Info ""

Write-Info "Checking prerequisites..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH"
    exit 1
}

Write-Success "Prerequisites check passed"

Write-Info "Creating necessary directories..."
$directories = @(
    "data\influxdb",
    "data\loki",
    "data\jaeger",
    "data\vault\data",
    "data\vault\logs",
    "data\minio",
    "data\spark\work",
    "data\spark\logs",
    "logs\promtail"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Info "Created directory: $dir"
    }
}

Write-Success "Directory structure created"

$env:COMPOSE_PROJECT_NAME = $PROJECT_NAME
$env:ENVIRONMENT = $Environment

Write-Info "Starting infrastructure services..."
try {
    $result = docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start services: $result"
        exit 1
    }
    Write-Success "Services started successfully"
} catch {
    Write-Error "Failed to start services: $($_.Exception.Message)"
    exit 1
}

if (-not $SkipHealthChecks) {
    Write-Info "Waiting for services to be ready..."
    
    function Test-ServiceHealth {
        param(
            [string]$ServiceName,
            [string]$Endpoint,
            [int]$TimeoutSeconds = 60
        )
        
        $startTime = Get-Date
        $timeout = $startTime.AddSeconds($TimeoutSeconds)
        
        while ((Get-Date) -lt $timeout) {
            try {
                $response = Invoke-WebRequest -Uri $Endpoint -Method GET -TimeoutSec 5 -UseBasicParsing
                if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 204) {
                    return $true
                }
            } catch {
                # Service not ready yet, continue waiting
            }
            
            Start-Sleep -Seconds 2
        }
        
        return $false
    }
    
    $healthyServices = @()
    $unhealthyServices = @()
    
    foreach ($service in $HEALTH_CHECK_ENDPOINTS.Keys) {
        Write-Info "Checking health of $service..."
        
        if (Test-ServiceHealth -ServiceName $service -Endpoint $HEALTH_CHECK_ENDPOINTS[$service] -TimeoutSeconds $HealthCheckTimeout) {
            Write-Success "OK $service is healthy"
            $healthyServices += $service
        } else {
            Write-Error "FAIL $service failed health check"
            $unhealthyServices += $service
        }
    }
    
    Write-Info ""
    Write-Info "Health Check Summary:"
    Write-Success "Healthy services: $($healthyServices.Count)/$($HEALTH_CHECK_ENDPOINTS.Count)"
    
    if ($unhealthyServices.Count -gt 0) {
        Write-Warning "Unhealthy services: $($unhealthyServices -join ', ')"
        Write-Info "You can check service logs with: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs [service-name]"
    }
}

if ($InitializeServices) {
    Write-Info "Initializing services..."
    
    Write-Info "Initializing InfluxDB..."
    try {
        Start-Sleep -Seconds 10
        
        $setupBody = @{
            "username" = "admin"
            "password" = "trading_admin_2024"
            "org" = "trading_org"
            "bucket" = "market_data"
            "retention_period_hrs" = 8760
        } | ConvertTo-Json
        
        $response = Invoke-WebRequest -Uri "http://localhost:8086/api/v2/setup" -Method POST -Body $setupBody -ContentType "application/json" -UseBasicParsing
        Write-Success "InfluxDB initialized successfully"
    } catch {
        Write-Warning "InfluxDB initialization failed or already completed: $($_.Exception.Message)"
    }
    
    Write-Info "Initializing Vault..."
    try {
        $initStatus = Invoke-WebRequest -Uri "http://localhost:8200/v1/sys/init" -Method GET -UseBasicParsing | ConvertFrom-Json
        
        if (-not $initStatus.initialized) {
            $initBody = @{
                "secret_shares" = 5
                "secret_threshold" = 3
            } | ConvertTo-Json
            
            $initResponse = Invoke-WebRequest -Uri "http://localhost:8200/v1/sys/init" -Method POST -Body $initBody -ContentType "application/json" -UseBasicParsing
            $initData = $initResponse.Content | ConvertFrom-Json

            $vaultKeys = @{
                "unseal_keys" = $initData.keys
                "root_token" = $initData.root_token
            }
            $vaultKeys | ConvertTo-Json | Out-File -FilePath "vault-keys.json" -Encoding UTF8
            Write-Success "Vault initialized successfully. Keys saved to vault-keys.json"
            Write-Warning "IMPORTANT: Store vault-keys.json securely and remove it from this location!"
            
            for ($i = 0; $i -lt 3; $i++) {
                $unsealBody = @{ "key" = $initData.keys[$i] } | ConvertTo-Json
                Invoke-WebRequest -Uri "http://localhost:8200/v1/sys/unseal" -Method POST -Body $unsealBody -ContentType "application/json" -UseBasicParsing | Out-Null
            }
            Write-Success "Vault unsealed successfully"
        } else {
            Write-Info "Vault already initialized"
        }
    } catch {
        Write-Warning "Vault initialization failed or already completed: $($_.Exception.Message)"
    }
    
    Write-Info "Initializing MinIO buckets..."
    try {
        Start-Sleep -Seconds 5
        
        docker exec trading-minio mc alias set local http://localhost:9000 trading_admin trading_minio_2024
        docker exec trading-minio mc mb local/warehouse --ignore-existing
        docker exec trading-minio mc mb local/market-data --ignore-existing
        docker exec trading-minio mc mb local/backups --ignore-existing
        
        Write-Success "MinIO buckets created successfully"
    } catch {
        Write-Warning "MinIO bucket creation failed: $($_.Exception.Message)"
    }
}

Write-Info ""
Write-Info "=== Service URLs ==="
Write-Info "InfluxDB UI: http://localhost:8086"
Write-Info "Grafana: http://localhost:3000 (admin/admin)"
Write-Info "Loki: http://localhost:3100"
Write-Info "Jaeger UI: http://localhost:16686"
Write-Info "Vault UI: http://localhost:8200"
Write-Info "MinIO Console: http://localhost:9001 (trading_admin/trading_minio_2024)"
Write-Info "Spark Master UI: http://localhost:8080"
Write-Info "Traefik Dashboard: http://localhost:8080"
Write-Info ""

Write-Info "=== Useful Commands ==="
Write-Info "View all services: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME ps"
Write-Info "View service logs: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME logs [service-name]"
Write-Info "Stop all services: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down"
Write-Info "Restart service: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME restart [service-name]"
Write-Info "Scale service: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --scale [service-name]=[count]"
Write-Info ""

Write-Info "Check the service URLs above to verify everything is working correctly."

if ($unhealthyServices.Count -gt 0) {
    Write-Warning "Some services failed health checks. Please investigate before proceeding."
    exit 1
} else {
    Write-Success "All services are healthy and ready for use!"
    exit 0
}