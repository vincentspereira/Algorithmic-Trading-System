#!/bin/bash

# Development Environment Setup Script using Docker
# This script sets up a Python development environment using Docker for isolation

echo "🐳 Algorithmic Trading System - Docker Development Environment Setup"
echo "===================================================================="

# Check if Docker is available
echo "🔍 Checking Docker installation..."

if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    echo "Please install Docker Desktop from https://docker.com and try again."
    exit 1
fi

echo "✅ Found Docker: $(docker --version)"

# Build the development container
echo ""
echo "🏗️  Building development container..."

if ! docker-compose -f docker-compose.dev.yml build; then
    echo "❌ Error: Failed to build development container"
    exit 1
fi

echo "✅ Development container built successfully"

# Create convenience scripts
echo ""
echo "🛠️  Creating convenience scripts..."

cat > run_dev_container.sh << 'EOF'
#!/bin/bash
# Quick script to run the development container

echo "🐳 Starting development container..."
docker-compose -f docker-compose.dev.yml run --rm algo-trading-dev
echo ""
echo "💡 Inside the container, you can:"
echo "   - Install dependencies with pip"
echo "   - Run tests"
echo "   - Develop and test your code"
echo ""
echo "🔚 Type 'exit' to leave the container"
EOF

chmod +x run_dev_container.sh

cat > start_dev_services.sh << 'EOF'
#!/bin/bash
# Quick script to start development services

echo "🚀 Starting development services..."
docker-compose -f docker-compose.dev.yml up
EOF

chmod +x start_dev_services.sh

# Display usage instructions
echo ""
echo "🎉 Docker development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Run the development container:"
echo "   ./run_dev_container.sh"
echo ""
echo "2. Or start development services:"
echo "   ./start_dev_services.sh"
echo ""
echo "3. Inside the container, all dependencies will be properly isolated"
echo "   and won't affect your global Python environment."
echo ""
echo "⚠️  IMPORTANT: All development should be done inside the Docker container"
echo "🔒 This ensures packages are installed only in the container, not globally"
echo ""