# Deployment script for Windows PowerShell

# Environment variables
$env:KAFKA_SERVERS = "kafka:9092"
$env:REDIS_HOST = "redis"
$env:CLICKHOUSE_HOST = "clickhouse"

Write-Host "🚀 Starting deployment..." -ForegroundColor Blue

# Check Docker
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not installed. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path data/clickhouse
New-Item -ItemType Directory -Force -Path data/redis

# Build and start services
Write-Host "🏗️ Building and starting services..." -ForegroundColor Blue
docker-compose build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build services" -ForegroundColor Red
    exit 1
}

docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start services" -ForegroundColor Red
    exit 1
}

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Blue
Start-Sleep -Seconds 30

# Initialize ClickHouse schema
Write-Host "🗄️ Initializing ClickHouse schema..." -ForegroundColor Blue
Get-Content backtesting/service/schema.sql | docker exec -i (docker-compose ps -q clickhouse) clickhouse-client

# Check services health
Write-Host "🏥 Checking services health..." -ForegroundColor Blue

function Test-ServicePort {
    param(
        [string]$ServiceName,
        [int]$Port
    )
    
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $tcp.Connect("localhost", $Port)
        Write-Host "✓ $ServiceName is running on port $Port" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ $ServiceName is not responding on port $Port" -ForegroundColor Red
        return $false
    }
    finally {
        $tcp.Dispose()
    }
}

$services_ok = $true

# Check each service
$services_ok = $services_ok -and (Test-ServicePort -ServiceName "Frontend" -Port 3000)
$services_ok = $services_ok -and (Test-ServicePort -ServiceName "Backtest Service" -Port 8000)
$services_ok = $services_ok -and (Test-ServicePort -ServiceName "ClickHouse" -Port 8123)
$services_ok = $services_ok -and (Test-ServicePort -ServiceName "Kafka" -Port 9092)
$services_ok = $services_ok -and (Test-ServicePort -ServiceName "Redis" -Port 6379)

if ($services_ok) {
    Write-Host "✅ All services are running!" -ForegroundColor Green
    Write-Host @"

📊 Access the services:
- Frontend: http://localhost:3000
- Backtest API: http://localhost:8000/docs
- ClickHouse UI: http://localhost:8123/play

📝 Test the system with:
Invoke-RestMethod -Uri 'http://localhost:8000/api/backtest' `
                 -Method Post `
                 -ContentType 'application/json' `
                 -Body '{
                     "strategy": {
                         "symbol": "AAPL",
                         "start_date": "2025-01-01T00:00:00Z",
                         "end_date": "2025-08-24T00:00:00Z",
                         "timeframe": "1d",
                         "fast_ma": 20,
                         "slow_ma": 50
                     }
                 }'
"@
}
else {
    Write-Host "❌ Some services failed to start. Check the logs with:" -ForegroundColor Red
    Write-Host "docker-compose logs"
    exit 1
}
