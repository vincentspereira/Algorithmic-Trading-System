#!/bin/bash

# Lobe Chat Integration Startup Script
# This script starts the AI Assistant, Lobe Chat Adapter, and Lobe Chat Frontend

set -e

echo "🚀 Starting Lobe Chat Integration for Algorithmic Trading System"
echo "================================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo "📝 Please edit .env file with your API keys and configuration"
    else
        echo "❌ .env.example file not found. Please create .env file manually."
        exit 1
    fi
fi

# Start prerequisite services first
echo "📦 Starting prerequisite services..."
docker-compose up -d postgres redis kafka feast

# Wait for services to be ready
echo "⏳ Waiting for prerequisite services to be ready..."
sleep 10

# Start AI Assistant services
echo "🤖 Starting AI Assistant services..."
docker-compose up -d ai_assistant lobe_chat_adapter lobe_chat

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 15

# Check service health
echo "🔍 Checking service health..."

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is healthy"
            return 0
        else
            echo "⏳ Waiting for $service_name (attempt $attempt/$max_attempts)..."
            sleep 3
            ((attempt++))
        fi
    done
    
    echo "❌ $service_name failed to start properly"
    return 1
}

# Check each service
check_service "AI Assistant" "http://localhost:8002/health"
check_service "Lobe Chat Adapter" "http://localhost:8003/health"
check_service "Lobe Chat Frontend" "http://localhost:3210"

echo ""
echo "🎉 Lobe Chat Integration is ready!"
echo "================================================================"
echo "📱 Lobe Chat Interface: http://localhost:3210"
echo "🤖 AI Assistant API: http://localhost:8002"
echo "🔗 Lobe Chat Adapter: http://localhost:8003"
echo ""
echo "📚 Documentation: ai_assistant/LOBE_CHAT_SETUP.md"
echo "🧪 Run tests: python ai_assistant/test_lobe_chat_integration.py"
echo ""
echo "💡 Tips:"
echo "  - Open http://localhost:3210 in your browser to start chatting"
echo "  - The AI assistant has access to trading tools and reasoning capabilities"
echo "  - Check logs with: docker-compose logs -f lobe_chat"
echo ""
echo "🛑 To stop services: docker-compose down"
echo "================================================================"