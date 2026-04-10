#!/usr/bin/env python3
"""
Start a single persona backend. Called by Godot launcher.

Usage: python start_backend.py PERSONA_NAME PORT [PERSONAS_DIR]

Environment variables set for the subprocess:
  COMPANION_NAME - The persona name
  COMPANION_PORT - The WebSocket port
  COMPANION_PERSONA_DIR - Path to persona/config directory
  COMPANION_STATE_DIR - Path to persona/state directory
  PERSONA_CONFIG_DIR - Path to persona config (for persona_loader.py)
"""
import sys
import os
import subprocess
import json
import time

def main():
    if len(sys.argv) < 3:
        print("Usage: start_backend.py PERSONA_NAME PORT [PERSONAS_DIR]")
        sys.exit(1)

    name = sys.argv[1]
    port = int(sys.argv[2])

    # Default personas directory is ./personas relative to wrapper root
    wrapper_root = os.path.dirname(os.path.abspath(__file__))
    personas_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(wrapper_root, "personas")

    persona_dir = os.path.join(personas_dir, name)
    config_dir = os.path.join(persona_dir, "config")
    state_dir = os.path.join(persona_dir, "state")

    # Validate persona exists
    if not os.path.exists(config_dir):
        print(json.dumps({"error": f"Persona config not found: {config_dir}"}))
        sys.exit(1)

    # Ensure state directory exists
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(os.path.join(state_dir, "memory"), exist_ok=True)
    os.makedirs(os.path.join(state_dir, "sessions"), exist_ok=True)
    os.makedirs(os.path.join(state_dir, "chronicle"), exist_ok=True)

    # Set environment variables for persona isolation
    env = os.environ.copy()
    env["COMPANION_NAME"] = name
    env["COMPANION_PORT"] = str(port)
    env["COMPANION_PERSONA_DIR"] = config_dir
    env["COMPANION_STATE_DIR"] = state_dir
    env["PERSONA_CONFIG_DIR"] = config_dir

    # Start the backend process
    # CREATE_NEW_PROCESS_GROUP on Windows makes the process independent
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [sys.executable, "main.py", "--ui", "--room-port", str(port)],
        cwd=wrapper_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags
    )

    # Write PID to registry file for tracking
    registry_file = os.path.join(wrapper_root, "running_backends.json")
    registry = {}
    if os.path.exists(registry_file):
        try:
            with open(registry_file, 'r') as f:
                registry = json.load(f)
        except (json.JSONDecodeError, IOError):
            registry = {}

    registry[name] = {
        "port": port,
        "pid": proc.pid,
        "started": time.time(),
        "config_dir": config_dir,
        "state_dir": state_dir
    }

    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)

    # Output success JSON for Godot to parse
    print(json.dumps({
        "status": "ok",
        "name": name,
        "port": port,
        "pid": proc.pid
    }))


if __name__ == "__main__":
    main()
