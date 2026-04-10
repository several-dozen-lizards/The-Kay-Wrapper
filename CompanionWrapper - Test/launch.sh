#!/bin/bash
echo "============================================"
echo "  Companion Wrapper — Starting Up"
echo "============================================"
echo ""

if [ ! -f "persona/persona_config.json" ]; then
    echo "  No persona found. Running setup wizard..."
    echo ""
    python3 setup_wizard.py
    echo ""
fi

if [ ! -f ".env" ]; then
    echo "  No .env found. Copying template..."
    cp env_template.txt .env
    echo "  Edit .env with your API key, then run this again."
    exit 1
fi

echo "  Loading persona..."
python3 main.py
