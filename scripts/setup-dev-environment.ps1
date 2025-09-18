#!/usr/bin/env pwsh
# =============================================================================
# Algorithmic Trading System - Development Environment Setup Script
# =============================================================================
# This script sets up the complete development environment using Docker Compose

param(
    [string]$Profile = "development",
    [switch]$SkipBuild,
    [switch]$Clean,
    [switch]$Monitoring,
    [switch]$AI,
    [switch]$Testing,
    [switch]$Help
)

# Color functions for better output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Info { Write-ColorOutput Cyan $args }
function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }

function Show-Help {
    Write-Info "Algorithmic Trading System - Development Environment Setup"
    Write-Info "================================================================"
    Write-Info ""
    Write-Info "Usage: .\setup-dev-environment.ps1 [OPTIONS]"
    Write-Info ""
    Write-Info "Options:"
    Write-Info "  -Profile <name>     Docker Compose profile to use (default: development)"
    Write-Info "  -SkipBuild         Skip building Docker images"
    Write-Info "  -Clean             Clean up existing containers and volumes"
    Write-Info "  -Monitoring        Include monitoring services (Prometheus, Grafana)"
    Write-Info "  -AI                Include AI services (Qdrant, Jupyter)"
    Write-Info "  -Testing           Include testing services"
    Write-Info "  -Help              Show this help message"
    Write-Info ""
    Write-Info "Examples:"
    Write-Info "  .\setup-dev-environment.ps1                    # Basic development setup"
    Write-Info "  .\setup-dev-environment.ps1 -Monitoring        # With monitoring"
    Write-Info "  .\setup-dev-environment.ps1 -AI -Monitoring    # Full setup"
    Write-Info "  .\setup-dev-environment.ps1 -Clean             # Clean and restart"
    exit 0
}

if ($Help) {
    Show-Help
}

# Check if Docker is installed and running
function Test-Docker {
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker not found"
        }
        Write-Success "✓ Docker is installed: $dockerVersion"
        
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker daemon is not running"
        }
        Write-Success "✓ Docker daemon is running"
        
        $composeVersion = docker compose version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose not found"
        }
        Write-Success "✓ Docker Compose is available: $composeVersion"
        
        return $true
    }
    catch {
        Write-Error "❌ Docker check failed: $_"
        Write-Error "Please install Docker Desktop and ensure it's running."
        Write-Error "Download from: https://www.docker.com/products/docker-desktop"
        return $false
    }
}

# Check if required files exist
function Test-RequiredFiles {
    $requiredFiles = @(
        "docker-compose.yml",
        "Dockerfile",
        ".env.example"
    )
    
    $missing = @()
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            $missing += $file
        }
    }
    
    if ($missing.Count -gt 0) {
        Write-Error "❌ Missing required files:"
        foreach ($file in $missing) {
            Write-Error "  - $file"
        }
        return $false
    }
    
    Write-Success "✓ All required files are present"
    return $true
}

# Setup environment file
function Setup-Environment {
    if (-not (Test-Path ".env")) {
        Write-Info "📝 Creating .env file from .env.example..."
        Copy-Item ".env.example" ".env"
        Write-Success "✓ .env file created"
        Write-Warning "⚠️  Please review and update the .env file with your specific configuration"
    } else {
        Write-Success "✓ .env file already exists"
    }
}

# Build profiles array
function Get-Profiles {
    $profiles = @($Profile)
    
    if ($Monitoring) {
        $profiles += "monitoring"
    }
    
    if ($AI) {
        $profiles += "ai"
    }
    
    if ($Testing) {
        $profiles += "testing"
    }
    
    return $profiles
}

# Clean up existing containers and volumes
function Invoke-Cleanup {
    Write-Info "🧹 Cleaning up existing containers and volumes..."
    
    # Stop all containers
    docker compose down --remove-orphans 2>$null
    
    # Remove volumes (optional - commented out to preserve data)
    # docker compose down --volumes 2>$null
    
    # Prune unused Docker resources
    docker system prune -f 2>$null
    
    Write-Success "✓ Cleanup completed"
}

# Build Docker images
function Invoke-Build {
    if ($SkipBuild) {
        Write-Info "⏭️  Skipping Docker image build"
        return
    }
    
    Write-Info "🔨 Building Docker images..."
    
    $profiles = Get-Profiles
    $profileArgs = $profiles | ForEach-Object { "--profile"; $_ }
    
    $buildCmd = @("docker", "compose") + $profileArgs + @("build", "--parallel")
    
    Write-Info "Running: $($buildCmd -join ' ')"
    & $buildCmd[0] $buildCmd[1..($buildCmd.Length-1)]
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Docker build failed"
        exit 1
    }
    
    Write-Success "✓ Docker images built successfully"
}

# Start services
function Start-Services {
    Write-Info "🚀 Starting services..."
    
    $profiles = Get-Profiles
    $profileArgs = $profiles | ForEach-Object { "--profile"; $_ }
    
    $upCmd = @("docker", "compose") + $profileArgs + @("up", "-d")
    
    Write-Info "Running: $($upCmd -join ' ')"
    & $upCmd[0] $upCmd[1..($upCmd.Length-1)]
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to start services"
        exit 1
    }
    
    Write-Success "✓ Services started successfully"
}

# Wait for services to be healthy
function Wait-ForServices {
    Write-Info "⏳ Waiting for services to be healthy..."
    
    $maxWait = 300  # 5 minutes
    $waited = 0
    $interval = 10
    
    while ($waited -lt $maxWait) {
        $unhealthy = docker compose ps --format json | ConvertFrom-Json | Where-Object { $_.Health -eq "unhealthy" -or $_.State -eq "exited" }
        
        if (-not $unhealthy) {
            Write-Success "✓ All services are healthy"
            return
        }
        
        Write-Info "Waiting for services... ($waited/$maxWait seconds)"
        Start-Sleep $interval
        $waited += $interval
    }
    
    Write-Warning "⚠️  Some services may not be fully ready. Check with 'docker compose ps'"
}

# Show service status and URLs
function Show-ServiceInfo {
    Write-Info "📊 Service Status:"
    docker compose ps --format table
    
    Write-Info ""
    Write-Info "🌐 Available Services:"
    Write-Info "  Frontend Application:    http://localhost:3000"
    Write-Info "  API Gateway:            http://localhost:8001"
    Write-Info "  Market Data Service:    http://localhost:8002"
    Write-Info "  Trading Engine:         http://localhost:8003"
    Write-Info "  Portfolio Manager:      http://localhost:8004"
    Write-Info "  Risk Manager:           http://localhost:8005"
    Write-Info "  AI Assistant:           http://localhost:8006"
    
    if ($Monitoring) {
        Write-Info "  Prometheus:             http://localhost:9090"
        Write-Info "  Grafana:                http://localhost:3001"
        Write-Info "  Jaeger:                 http://localhost:16686"
        Write-Info "  Kafka UI:               http://localhost:8080"
    }
    
    if ($AI) {
        Write-Info "  Jupyter Lab:            http://localhost:8888"
        Write-Info "  Qdrant Dashboard:       http://localhost:6333/dashboard"
    }
    
    Write-Info "  MinIO Console:          http://localhost:9001"
    Write-Info "  Keycloak:               http://localhost:8090"
    Write-Info ""
    Write-Info "📚 Documentation:"
    Write-Info "  API Documentation:      http://localhost:8001/docs"
    Write-Info "  WebSocket API:          ws://localhost:8001/ws"
    Write-Info ""
    Write-Info "🔧 Management Commands:"
    Write-Info "  View logs:              docker compose logs -f [service_name]"
    Write-Info "  Stop services:          docker compose down"
    Write-Info "  Restart service:        docker compose restart [service_name]"
    Write-Info "  Shell access:           docker compose exec [service_name] /bin/bash"
}

# Main execution
function Main {
    Write-Info "🚀 Algorithmic Trading System - Development Environment Setup"
    Write-Info "================================================================"
    
    # Pre-flight checks
    if (-not (Test-Docker)) {
        exit 1
    }
    
    if (-not (Test-RequiredFiles)) {
        exit 1
    }
    
    # Setup environment
    Setup-Environment
    
    # Clean up if requested
    if ($Clean) {
        Invoke-Cleanup
    }
    
    # Build and start services
    Invoke-Build
    Start-Services
    
    # Wait for services to be ready
    Wait-ForServices
    
    # Show service information
    Show-ServiceInfo
    
    Write-Success "🎉 Development environment is ready!"
    Write-Info "💡 Tip: Use 'docker compose logs -f' to monitor service logs"
}

# Run main function
Main