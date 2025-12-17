#!/bin/bash

# Quick Start Script for S13 Partner Consultation Service
# This script helps set up and run the service for development

set -e

echo "============================================"
echo "S13 Partner Consultation Service - Quick Start"
echo "============================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "✅ uv is installed"

# Check if MongoDB is running
if ! pgrep -x mongod > /dev/null; then
    echo "⚠️  Warning: MongoDB doesn't appear to be running"
    echo "   Please start MongoDB:"
    echo "   sudo systemctl start mongod"
    echo ""
else
    echo "✅ MongoDB is running"
fi

# Check if RabbitMQ is running
if ! pgrep -x beam.smp > /dev/null; then
    echo "⚠️  Warning: RabbitMQ doesn't appear to be running"
    echo "   Please start RabbitMQ:"
    echo "   sudo systemctl start rabbitmq-server"
    echo ""
else
    echo "✅ RabbitMQ is running"
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please review and update .env with your configuration"
    echo ""
else
    echo "✅ .env file exists"
fi

# Sync dependencies
echo "📦 Syncing dependencies with uv..."
uv sync
echo "✅ Dependencies synced"
echo ""

# Ask user if they want to start the service
read -p "Do you want to start the service now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting S13 Partner Consultation Service..."
    echo ""
    echo "Press Ctrl+C to stop the service"
    echo ""
    uv run -m app
else
    echo ""
    echo "To start the service manually, run:"
    echo "  uv run -m app"
    echo ""
fi
