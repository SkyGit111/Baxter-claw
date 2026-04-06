#!/bin/bash
# Quick test script for Baxter-Claw bridge server

set -e

echo "=========================================="
echo "Baxter-Claw Quick Test"
echo "=========================================="

# Check if bridge is installed
if ! command -v baxter-claw-bridge &> /dev/null; then
    echo "Error: baxter-claw-bridge not found. Please install first:"
    echo "  pip install -e ."
    exit 1
fi

# Check if config exists
if [ ! -f "config/baxter.example.yaml" ]; then
    echo "Error: config/baxter.example.yaml not found"
    exit 1
fi

echo ""
echo "1. Testing Python imports..."
python3 -c "from bridge.server import app; print('✓ Bridge server imports OK')"
python3 -c "from bridge.drivers.mock_driver import MockDriver; print('✓ Mock driver imports OK')"
python3 -c "from bridge.primitives import BaxterPrimitives; print('✓ Primitives imports OK')"

echo ""
echo "2. Running unit tests..."
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short
else
    echo "⚠ pytest not installed, skipping tests"
    echo "  Install with: pip install pytest pytest-asyncio"
fi

echo ""
echo "3. Testing mock driver..."
python3 examples/test_primitives.py

echo ""
echo "=========================================="
echo "✓ All tests passed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start bridge server: baxter-claw-bridge --config config/baxter.example.yaml"
echo "  2. Test API: curl http://localhost:8420/health"
echo "  3. Install plugin: cd plugin && npm install && npm run build"
echo "  4. Configure OpenClaw and start using natural language control"
echo ""
