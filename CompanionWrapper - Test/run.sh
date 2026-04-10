#!/bin/bash
# Companion Wrapper — Launcher
# Works on Linux and macOS

set -e
cd "$(dirname "$0")"

echo ""
echo "  ============================================"
echo "   Companion Wrapper"
echo "  ============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ERROR: python3 not found. Install Python 3.10+."
    exit 1
fi

# Setup wizard if no persona
if [ ! -f "persona/persona_config.json" ]; then
    echo "  No companion configured yet. Let's set one up!"
    echo ""
    python3 setup_wizard.py
    if [ ! -f "persona/persona_config.json" ]; then
        echo "  Setup cancelled."
        exit 1
    fi
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "  No .env file found. Creating from template..."
    if [ -f "env_template.txt" ]; then
        cp env_template.txt .env
        echo ""
        echo "  ================================================"
        echo "   IMPORTANT: Edit .env with your API key!"
        echo "  ================================================"
        echo ""
        echo "  Get an API key from:"
        echo "    Anthropic: https://console.anthropic.com/"
        echo "    OpenAI:    https://platform.openai.com/api-keys"
        echo ""
        echo "  After adding your key, run this script again."
        exit 1
    fi
fi

# Install dependencies if needed
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "  Installing dependencies..."
    pip3 install -r requirements.txt -q
fi

# Detect Godot executable
GODOT_BIN=""
if [ -f "godot-ui/Companion.x86_64" ]; then
    GODOT_BIN="godot-ui/Companion.x86_64"
elif [ -d "godot-ui/Companion.app" ]; then
    GODOT_BIN="godot-ui/Companion.app"
fi

# Mode selection
if [ -n "$GODOT_BIN" ]; then
    echo "  Choose mode:"
    echo "    1. Terminal mode (text only)"
    echo "    2. Godot UI (graphical)"
    echo ""
    read -p "  Mode [2]: " MODE
    MODE=${MODE:-2}
else
    MODE=1
fi

if [ "$MODE" = "2" ] && [ -n "$GODOT_BIN" ]; then
    echo ""
    echo "  Starting backend + Godot UI..."
    
    # Start backend in background
    python3 main_bridge.py --room-port 8780 &
    BACKEND_PID=$!
    
    sleep 3
    
    # Launch Godot
    if [ -d "$GODOT_BIN" ]; then
        open "$GODOT_BIN" &  # macOS .app
    else
        chmod +x "$GODOT_BIN"
        ./"$GODOT_BIN" &
    fi
    
    echo "  Backend running (PID $BACKEND_PID). Press Ctrl+C to stop."
    
    # Cleanup on exit
    trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM
    wait $BACKEND_PID
else
    echo ""
    echo "  Starting in terminal mode..."
    echo "  Type 'quit' or 'exit' to end session."
    echo "  ============================================"
    echo ""
    python3 main.py
fi

echo ""
echo "  Session ended."
