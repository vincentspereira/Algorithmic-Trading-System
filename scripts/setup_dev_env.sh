#!/bin/bash

# Development Environment Setup Script for Linux/Mac
# This script creates a Python virtual environment and installs dependencies safely

set -e  # Exit on any error

echo "🐍 Algorithmic Trading System - Development Environment Setup"
echo "============================================================"

# Check if Python 3.11+ is available
check_python() {
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]]; then
            PYTHON_CMD="python3"
        else
            echo "❌ Error: Python 3.11+ is required. Found Python $PYTHON_VERSION"
            echo "Please install Python 3.11 or higher and try again."
            exit 1
        fi
    else
        echo "❌ Error: Python 3 is not installed or not in PATH"
        echo "Please install Python 3.11+ and try again."
        exit 1
    fi
    
    echo "✅ Found Python: $($PYTHON_CMD --version)"
}

# Create virtual environment
create_venv() {
    VENV_DIR="venv"
    
    if [ -d "$VENV_DIR" ]; then
        echo "⚠️  Virtual environment already exists at ./$VENV_DIR"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🗑️  Removing existing virtual environment..."
            rm -rf "$VENV_DIR"
        else
            echo "📁 Using existing virtual environment"
            return 0
        fi
    fi
    
    echo "🔨 Creating Python virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✅ Virtual environment created at ./$VENV_DIR"
}

# Activate virtual environment and install dependencies
install_dependencies() {
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
    
    echo "📦 Upgrading pip..."
    pip install --upgrade pip
    
    echo "📚 Installing project dependencies..."
    if [ -f "nautilus_trader_engine/requirements.txt" ]; then
        pip install -r nautilus_trader_engine/requirements.txt
        echo "✅ Dependencies installed successfully"
    else
        echo "❌ Error: requirements.txt not found at nautilus_trader_engine/requirements.txt"
        exit 1
    fi
}

# Create activation script
create_activation_script() {
    cat > activate_dev_env.sh << 'EOF'
#!/bin/bash
# Quick activation script for development environment

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup_dev_env.sh first"
    exit 1
fi

echo "🐍 Activating development environment..."
source venv/bin/activate
echo "✅ Development environment activated"
echo "💡 To deactivate, run: deactivate"
echo "📁 Current Python: $(which python)"
echo "📦 Installed packages: pip list"
EOF
    
    chmod +x activate_dev_env.sh
    echo "✅ Created activation script: ./activate_dev_env.sh"
}

# Display usage instructions
show_instructions() {
    echo ""
    echo "🎉 Development environment setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Activate the environment:"
    echo "   source venv/bin/activate"
    echo "   # OR use the convenience script:"
    echo "   source ./activate_dev_env.sh"
    echo ""
    echo "2. Verify installation:"
    echo "   python --version"
    echo "   pip list"
    echo ""
    echo "3. Run the application:"
    echo "   cd nautilus_trader_engine"
    echo "   python main.py"
    echo ""
    echo "4. To deactivate when done:"
    echo "   deactivate"
    echo ""
    echo "⚠️  IMPORTANT: Always activate the virtual environment before working on the project!"
    echo "🔒 This ensures packages are installed locally, not globally on your system."
}

# Main execution
main() {
    echo "🔍 Checking Python installation..."
    check_python
    
    echo ""
    echo "🏗️  Setting up virtual environment..."
    create_venv
    
    echo ""
    echo "📦 Installing dependencies..."
    install_dependencies
    
    echo ""
    echo "🛠️  Creating convenience scripts..."
    create_activation_script
    
    echo ""
    show_instructions
}

# Run main function
main "$@"