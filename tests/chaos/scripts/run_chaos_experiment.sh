#!/bin/bash

# Script to run individual chaos experiments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [EXPERIMENT_TYPE] [OPTIONS]"
    echo ""
    echo "Experiment Types:"
    echo "  network-latency    - Test network latency resilience"
    echo "  service-crash      - Test service crash recovery"
    echo "  memory-pressure    - Test memory pressure handling"
    echo "  network-partition  - Test network partition recovery"
    echo "  game-day          - Run full chaos game day"
    echo ""
    echo "Options:"
    echo "  --duration SECONDS - Experiment duration (default: varies by type)"
    echo "  --intensity FLOAT  - Experiment intensity 0.0-1.0 (default: 0.5)"
    echo "  --target SERVICE   - Target service name (default: varies by type)"
    echo "  --report          - Generate detailed report"
    echo "  --monitor         - Keep monitoring services running"
    echo ""
    echo "Examples:"
    echo "  $0 network-latency --duration 60 --intensity 0.8"
    echo "  $0 service-crash --target order_service --report"
    echo "  $0 game-day --monitor"
}

# Default values
EXPERIMENT_TYPE=""
DURATION=""
INTENSITY=""
TARGET=""
GENERATE_REPORT=false
KEEP_MONITORING=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        network-latency|service-crash|memory-pressure|network-partition|game-day)
            EXPERIMENT_TYPE="$1"
            shift
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --intensity)
            INTENSITY="$2"
            shift 2
            ;;
        --target)
            TARGET="$2"
            shift 2
            ;;
        --report)
            GENERATE_REPORT=true
            shift
            ;;
        --monitor)
            KEEP_MONITORING=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if experiment type is provided
if [[ -z "$EXPERIMENT_TYPE" ]]; then
    print_error "Experiment type is required"
    show_usage
    exit 1
fi

print_header "🔥 Chaos Engineering Experiment Runner"
print_header "======================================"

# Check Docker
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running"
    exit 1
fi

# Start monitoring services if requested
if [[ "$KEEP_MONITORING" == true ]]; then
    print_status "Starting monitoring services..."
    docker-compose up -d prometheus grafana
    sleep 5
fi

# Create experiment configuration
create_experiment_config() {
    local exp_type=$1
    local config_file="/tmp/chaos_experiment_config.json"
    
    case $exp_type in
        network-latency)
            cat > $config_file << EOF
{
    "experiment_id": "cli_network_latency_$(date +%s)",
    "name": "CLI Network Latency Test",
    "description": "Network latency chaos experiment via CLI",
    "failure_type": "network_latency",
    "target_component": "${TARGET:-market_data_feed}",
    "duration": ${DURATION:-60},
    "intensity": ${INTENSITY:-0.5},
    "parameters": {
        "latency_ms": $(echo "${INTENSITY:-0.5} * 1000" | bc -l | cut -d. -f1)
    },
    "hypothesis": "System should handle network latency gracefully",
    "success_criteria": [
        "Response time increases but stays under 5 seconds",
        "Error rate remains below 5%",
        "System recovers within 30 seconds"
    ],
    "rollback_strategy": "Restore normal network conditions immediately"
}
EOF
            ;;
        service-crash)
            cat > $config_file << EOF
{
    "experiment_id": "cli_service_crash_$(date +%s)",
    "name": "CLI Service Crash Test",
    "description": "Service crash chaos experiment via CLI",
    "failure_type": "service_crash",
    "target_component": "${TARGET:-order_service}",
    "duration": ${DURATION:-30},
    "intensity": ${INTENSITY:-1.0},
    "parameters": {},
    "hypothesis": "System should handle service crashes with automatic recovery",
    "success_criteria": [
        "Service restarts automatically",
        "Requests are queued during downtime",
        "No data loss occurs"
    ],
    "rollback_strategy": "Manually restart service if needed"
}
EOF
            ;;
        memory-pressure)
            cat > $config_file << EOF
{
    "experiment_id": "cli_memory_pressure_$(date +%s)",
    "name": "CLI Memory Pressure Test",
    "description": "Memory pressure chaos experiment via CLI",
    "failure_type": "memory_pressure",
    "target_component": "${TARGET:-trading_engine}",
    "duration": ${DURATION:-45},
    "intensity": ${INTENSITY:-0.8},
    "parameters": {
        "target_usage": ${INTENSITY:-0.8}
    },
    "hypothesis": "System should handle high memory usage without crashing",
    "success_criteria": [
        "System remains responsive",
        "No out-of-memory errors",
        "Graceful performance degradation"
    ],
    "rollback_strategy": "Release memory pressure immediately"
}
EOF
            ;;
        network-partition)
            cat > $config_file << EOF
{
    "experiment_id": "cli_network_partition_$(date +%s)",
    "name": "CLI Network Partition Test",
    "description": "Network partition chaos experiment via CLI",
    "failure_type": "network_partition",
    "target_component": "${TARGET:-database}",
    "duration": ${DURATION:-20},
    "intensity": ${INTENSITY:-1.0},
    "parameters": {},
    "hypothesis": "System should handle network partitions gracefully",
    "success_criteria": [
        "System switches to degraded mode",
        "Critical operations continue",
        "Automatic recovery when partition heals"
    ],
    "rollback_strategy": "Restore network connectivity immediately"
}
EOF
            ;;
        game-day)
            cat > $config_file << EOF
{
    "game_day_id": "cli_game_day_$(date +%s)",
    "name": "CLI Chaos Game Day",
    "description": "Comprehensive chaos game day via CLI",
    "duration": ${DURATION:-240},
    "experiments": [
        "network_latency",
        "service_crash",
        "memory_pressure"
    ],
    "participants": ["CLI User"],
    "objectives": [
        "Test system resilience",
        "Validate recovery procedures"
    ],
    "success_criteria": [
        "All experiments complete successfully",
        "System recovers within expected timeframes"
    ]
}
EOF
            ;;
    esac
    
    echo $config_file
}

# Run the experiment
run_experiment() {
    local exp_type=$1
    local config_file=$2
    
    print_status "Running $exp_type experiment..."
    
    if [[ "$exp_type" == "game-day" ]]; then
        # Run game day
        docker-compose run --rm chaos-engineering python -c "
import json
import asyncio
from chaos_automation import ChaosAutomation, ChaosGameDay
from chaos_engineering_framework import ChaosExperimentLibrary
from datetime import datetime

# Load config
with open('$config_file', 'r') as f:
    config = json.load(f)

# Create game day
game_day = ChaosGameDay(
    game_day_id=config['game_day_id'],
    name=config['name'],
    description=config['description'],
    start_time=datetime.now(),
    duration=config['duration'],
    experiments=[
        ChaosExperimentLibrary.network_latency_experiment(),
        ChaosExperimentLibrary.service_crash_experiment(),
        ChaosExperimentLibrary.memory_pressure_experiment()
    ],
    participants=config['participants'],
    objectives=config['objectives'],
    success_criteria=config['success_criteria']
)

# Execute game day
automation = ChaosAutomation()
automation.create_game_day(game_day)
results = asyncio.run(automation.execute_game_day(config['game_day_id']))

print(f'Game day completed with {len(results[\"experiment_results\"])} experiments')
"
    else
        # Run individual experiment
        docker-compose run --rm chaos-engineering python -c "
import json
import asyncio
from chaos_engineering_framework import ChaosExperiment, ChaosExperimentRunner, FailureType
from datetime import datetime

# Load config
with open('$config_file', 'r') as f:
    config = json.load(f)

# Create experiment
experiment = ChaosExperiment(
    experiment_id=config['experiment_id'],
    name=config['name'],
    description=config['description'],
    failure_type=FailureType(config['failure_type']),
    target_component=config['target_component'],
    duration=config['duration'],
    intensity=config['intensity'],
    parameters=config['parameters'],
    hypothesis=config['hypothesis'],
    success_criteria=config['success_criteria'],
    rollback_strategy=config['rollback_strategy']
)

# Run experiment
runner = ChaosExperimentRunner()
results = asyncio.run(runner.run_experiment(experiment))

print(f'Experiment completed with status: {experiment.status.value}')
print(f'Hypothesis validated: {results.get(\"hypothesis_validated\", False)}')

# Generate report if requested
if $GENERATE_REPORT:
    report = runner.generate_experiment_report(experiment)
    with open(f'/app/reports/{experiment.experiment_id}_report.md', 'w') as f:
        f.write(report)
    print(f'Report saved: /app/reports/{experiment.experiment_id}_report.md')
"
    fi
}

# Main execution
print_status "Preparing chaos experiment: $EXPERIMENT_TYPE"

# Create experiment configuration
CONFIG_FILE=$(create_experiment_config $EXPERIMENT_TYPE)
print_status "Configuration created: $CONFIG_FILE"

# Copy config to container volume
mkdir -p ./temp
cp $CONFIG_FILE ./temp/experiment_config.json

# Run the experiment
run_experiment $EXPERIMENT_TYPE ./temp/experiment_config.json

# Cleanup
rm -f $CONFIG_FILE
rm -rf ./temp

if [[ "$GENERATE_REPORT" == true ]]; then
    print_status "📊 Report generated in ./reports/"
fi

if [[ "$KEEP_MONITORING" == true ]]; then
    print_status "🔍 Monitoring services running:"
    print_status "  Prometheus: http://localhost:9090"
    print_status "  Grafana: http://localhost:3000 (admin/chaos123)"
    print_status "Use 'docker-compose down' to stop services"
else
    print_status "Stopping services..."
    docker-compose down > /dev/null 2>&1
fi

print_status "✅ Chaos experiment completed successfully!"