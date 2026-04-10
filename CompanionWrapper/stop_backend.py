#!/usr/bin/env python3
"""
Stop persona backend(s). Called by Godot on shutdown.

Usage:
    python stop_backend.py PERSONA_NAME    # Stop specific persona
    python stop_backend.py --all           # Stop all running backends
"""
import sys
import os
import json

# Add wrapper root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend_manager import BackendManager


def main():
    if len(sys.argv) < 2:
        print("Usage: stop_backend.py PERSONA_NAME | --all")
        sys.exit(1)

    mgr = BackendManager()

    if sys.argv[1] == "--all":
        count = mgr.stop_all()
        print(json.dumps({"status": "ok", "stopped": count}))
    else:
        name = sys.argv[1]
        success = mgr.stop_persona(name)
        print(json.dumps({"status": "ok" if success else "error", "name": name}))


if __name__ == "__main__":
    main()
