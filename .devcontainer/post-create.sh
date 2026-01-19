#!/bin/bash
set -e

echo "🚀 Setting up Home Assistant S-Bus Integration Development Environment..."

# Upgrade pip
python -m pip install --upgrade pip

# Install Home Assistant and development dependencies
echo "📦 Installing Home Assistant and development dependencies..."
pip install -r requirements_test.txt

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Create Home Assistant config directory
echo "📁 Creating Home Assistant configuration directory..."
mkdir -p config
mkdir -p config/custom_components

# Create symlink for custom component
echo "🔗 Creating symlink for custom component..."
if [ ! -L "config/custom_components/sbus" ]; then
    ln -s /workspaces/S-Bus_HA/custom_components/sbus config/custom_components/sbus
fi

# Create basic Home Assistant configuration
if [ ! -f "config/configuration.yaml" ]; then
    echo "📝 Creating basic configuration.yaml..."
    cat > config/configuration.yaml << EOF
# Home Assistant Configuration
default_config:

# Configure logger for development
logger:
  default: info
  logs:
    custom_components.sbus: debug

# Allow Home Assistant to be embedded in VS Code
http:
  cors_allowed_origins:
    - http://localhost:8123
EOF
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 To start Home Assistant, run:"
echo "   hass -c config"
echo ""
echo "🌐 Access Home Assistant at: http://localhost:8123"
