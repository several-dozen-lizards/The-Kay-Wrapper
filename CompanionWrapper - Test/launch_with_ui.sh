#!/bin/bash
echo "============================================"
echo "  Companion Wrapper + Godot UI"
echo "============================================"
echo

if [ ! -f "persona/persona_config.json" ]; then
    echo "  No persona found. Running setup wizard..."
    echo
    python3 setup_wizard.py
    echo
fi

if [ ! -f ".env" ]; then
    echo "  No .env found. Copying template..."
    cp env_template.txt .env
    echo "  Edit .env with your API key, then run this again."
    exit 1
fi

echo "  Starting Python backend on port 8780..."
python3 main.py --room-port 8780 &
BACKEND_PID=$!

echo "  Waiting for backend to initialize..."
sleep 3

echo "  Launching Godot UI..."
if [ -f "godot-ui/Companion.x86_64" ]; then
    ./godot-ui/Companion.x86_64 &
elif [ -f "godot-ui/Companion.app" ]; then
    open godot-ui/Companion.app &
else
    echo "  NOTE: Godot executable not found."
    echo "  Open godot-ui in Godot Engine and press F5 to run."
    echo "  Or export the project to godot-ui/Companion.x86_64 or Companion.app"
fi

echo
echo "  Backend running (PID: $BACKEND_PID)"
echo "  Press Enter to stop the backend..."
read
kill $BACKEND_PID 2>/dev/null
echo "  Stopped."
