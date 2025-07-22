#!/bin/bash

# AI Betting Platform - Dependency Installation Script
echo "Installing dependencies for AI Betting Platform..."

# Check if we're in the correct directory
if [[ ! -f "pyproject.toml" ]]; then
    echo "Error: pyproject.toml not found. Please run from the ai-betting-platform root directory."
    exit 1
fi

# Install Poetry if not already installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install main dependencies
echo "Installing main project dependencies..."
poetry install

# Install prediction engine dependencies
echo "Installing prediction engine dependencies..."
cd services/prediction-engine
poetry install
cd ../..

# Install user management dependencies
echo "Installing user management dependencies..."
cd services/user-management
poetry install
cd ../..

# Install chat assistant dependencies
echo "Installing chat assistant dependencies..."
cd services/chat-assistant
poetry install
cd ../..

# Install additional dependencies that might be missing
echo "Installing additional Python packages..."
poetry run pip install opentelemetry-exporter-prometheus opentelemetry-exporter-otlp-proto-grpc
poetry run pip install opentelemetry-propagator-b3 opentelemetry-instrumentation-requests
poetry run pip install opentelemetry-instrumentation-sqlalchemy

# Check if original model services have their dependencies
echo "Checking original model dependencies..."

# Check logistic regression predictor
if [[ -d "../logistic-regression-predictor" ]]; then
    echo "Found logistic regression predictor"
    if [[ -f "../logistic-regression-predictor/requirements.txt" ]]; then
        echo "Installing LR predictor dependencies..."
        poetry run pip install -r ../logistic-regression-predictor/requirements.txt
    fi
fi

# Check lightgbm predictor
if [[ -d "../lightgbm-predictor" ]]; then
    echo "Found lightgbm predictor"
    if [[ -f "../lightgbm-predictor/requirements.txt" ]]; then
        echo "Installing LightGBM predictor dependencies..."
        poetry run pip install -r ../lightgbm-predictor/requirements.txt
    fi
fi

# Check transformer predictor
if [[ -d "../transformer-predictor" ]]; then
    echo "Found transformer predictor"
    if [[ -f "../transformer-predictor/requirements.txt" ]]; then
        echo "Installing Transformer predictor dependencies..."
        poetry run pip install -r ../transformer-predictor/requirements.txt
    fi
fi

# Check RL predictor
if [[ -d "../reinforcement-learning-predictor" ]]; then
    echo "Found RL predictor"
    if [[ -f "../reinforcement-learning-predictor/requirements.txt" ]]; then
        echo "Installing RL predictor dependencies..."
        poetry run pip install -r ../reinforcement-learning-predictor/requirements.txt
    fi
fi

echo ""
echo "Dependencies installation complete!"
echo ""
echo "Next steps:"
echo "1. Run the unified API: python scripts/run_unified_api.py"
echo "2. Or start with monitoring: cd monitoring && docker-compose up -d"
echo "3. Access API docs at: http://localhost:8001/docs"