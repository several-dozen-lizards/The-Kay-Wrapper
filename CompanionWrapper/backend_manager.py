"""
Backend Manager - Manages multiple persona backend processes.

Provides utilities for:
- Starting/stopping persona backends
- Port allocation and tracking
- Process health monitoring
- Session state persistence

Used by the Godot launcher and stop_backend.py script.
"""

import subprocess
import json
import os
import sys
import time
import signal
import socket
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


PORT_BASE = 8780
PORT_MAX = 8799
# Reserved ports: 8765 (Nexus main), 8770-8771 (Kay/Reed private rooms)
RESERVED_PORTS = {8765, 8770, 8771}


@dataclass
class BackendInfo:
    name: str
    port: int
    pid: int
    started: float
    config_dir: str
    state_dir: str


class BackendManager:
    """
    Manages multiple persona backend processes.

    Each persona gets its own Python process running main.py with
    environment variables for isolation.
    """

    def __init__(self, wrapper_root: str = None):
        if wrapper_root is None:
            wrapper_root = os.path.dirname(os.path.abspath(__file__))
        self.root = wrapper_root
        self.personas_dir = os.path.join(wrapper_root, "personas")
        self.registry_file = os.path.join(wrapper_root, "running_backends.json")
        self._registry: Dict[str, BackendInfo] = {}
        self._load_registry()

    def _load_registry(self):
        """Load running backends from registry file."""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                for name, info in data.items():
                    self._registry[name] = BackendInfo(
                        name=name,
                        port=info.get("port", 0),
                        pid=info.get("pid", 0),
                        started=info.get("started", 0),
                        config_dir=info.get("config_dir", ""),
                        state_dir=info.get("state_dir", "")
                    )
            except (json.JSONDecodeError, IOError) as e:
                print(f"[BACKEND] Failed to load registry: {e}")
                self._registry = {}

    def _save_registry(self):
        """Save running backends to registry file."""
        data = {}
        for name, info in self._registry.items():
            data[name] = asdict(info)
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('localhost', port)) == 0

    def _process_alive(self, pid: int) -> bool:
        """Check if a process is still running."""
        try:
            if sys.platform == "win32":
                # Windows: use tasklist
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True
                )
                return str(pid) in result.stdout
            else:
                # Unix: send signal 0
                os.kill(pid, 0)
                return True
        except (ProcessLookupError, PermissionError, OSError):
            return False

    def get_available_port(self) -> int:
        """Find next available port in range."""
        used = {info.port for info in self._registry.values()}
        used.update(RESERVED_PORTS)

        for port in range(PORT_BASE, PORT_MAX + 1):
            if port not in used and not self._port_in_use(port):
                return port
        raise RuntimeError(f"No available ports in range {PORT_BASE}-{PORT_MAX}")

    def list_personas(self) -> List[Dict[str, Any]]:
        """List all available personas from personas/ directory."""
        personas = []
        if not os.path.exists(self.personas_dir):
            return personas

        for entry in os.scandir(self.personas_dir):
            if entry.is_dir():
                config_path = os.path.join(entry.path, "config", "persona_config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        personas.append({
                            "name": entry.name,
                            "display_name": config.get("name", entry.name),
                            "description": config.get("description", ""),
                            "theme_color": config.get("room", {}).get("color", "#808080"),
                            "running": entry.name in self._registry and self._process_alive(self._registry[entry.name].pid),
                            "port": self._registry.get(entry.name, BackendInfo("", 0, 0, 0, "", "")).port
                        })
                    except (json.JSONDecodeError, IOError):
                        personas.append({
                            "name": entry.name,
                            "display_name": entry.name,
                            "description": "(config error)",
                            "theme_color": "#808080",
                            "running": False,
                            "port": 0
                        })
        return personas

    def start_persona(self, name: str, port: int = None) -> BackendInfo:
        """Start a backend for a persona."""
        # Check if already running
        if name in self._registry:
            info = self._registry[name]
            if self._process_alive(info.pid):
                return info
            else:
                # Stale entry - remove it
                del self._registry[name]

        # Get port
        if port is None:
            port = self.get_available_port()

        persona_dir = os.path.join(self.personas_dir, name)
        config_dir = os.path.join(persona_dir, "config")
        state_dir = os.path.join(persona_dir, "state")

        if not os.path.exists(config_dir):
            raise FileNotFoundError(f"Persona config not found: {config_dir}")

        # Ensure state directories exist
        os.makedirs(state_dir, exist_ok=True)
        for subdir in ["memory", "sessions", "chronicle"]:
            os.makedirs(os.path.join(state_dir, subdir), exist_ok=True)

        # Set environment variables for persona isolation
        env = os.environ.copy()
        env["COMPANION_NAME"] = name
        env["COMPANION_PORT"] = str(port)
        env["COMPANION_PERSONA_DIR"] = config_dir
        env["COMPANION_STATE_DIR"] = state_dir
        env["PERSONA_CONFIG_DIR"] = config_dir

        # Start the backend process
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            [sys.executable, "main.py", "--ui", "--room-port", str(port)],
            cwd=self.root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags
        )

        info = BackendInfo(
            name=name,
            port=port,
            pid=proc.pid,
            started=time.time(),
            config_dir=config_dir,
            state_dir=state_dir
        )
        self._registry[name] = info
        self._save_registry()
        return info

    def stop_persona(self, name: str, timeout: float = 10.0) -> bool:
        """Stop a persona's backend. Returns True if stopped successfully."""
        if name not in self._registry:
            return True

        info = self._registry[name]
        pid = info.pid

        if not self._process_alive(pid):
            del self._registry[name]
            self._save_registry()
            return True

        # Try graceful termination first
        try:
            if sys.platform == "win32":
                # Windows: CTRL_BREAK_EVENT for process groups
                os.kill(pid, signal.CTRL_BREAK_EVENT)
            else:
                os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass

        # Wait for graceful shutdown
        start = time.time()
        while time.time() - start < timeout:
            if not self._process_alive(pid):
                break
            time.sleep(0.5)

        # Force kill if still running
        if self._process_alive(pid):
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass

        del self._registry[name]
        self._save_registry()
        return True

    def stop_all(self, timeout: float = 10.0) -> int:
        """Stop all running backends. Returns count of stopped backends."""
        count = 0
        for name in list(self._registry.keys()):
            if self.stop_persona(name, timeout):
                count += 1
        return count

    def list_running(self) -> Dict[str, int]:
        """Return dict of running persona names to ports."""
        running = {}
        for name, info in list(self._registry.items()):
            if self._process_alive(info.pid):
                running[name] = info.port
            else:
                # Clean up stale entry
                del self._registry[name]
        self._save_registry()
        return running

    def get_info(self, name: str) -> Optional[BackendInfo]:
        """Get info for a running persona."""
        if name in self._registry:
            info = self._registry[name]
            if self._process_alive(info.pid):
                return info
        return None

    def cleanup_stale(self) -> int:
        """Remove stale entries from registry. Returns count cleaned."""
        count = 0
        for name in list(self._registry.keys()):
            if not self._process_alive(self._registry[name].pid):
                del self._registry[name]
                count += 1
        if count > 0:
            self._save_registry()
        return count


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backend Manager CLI")
    parser.add_argument("command", choices=["list", "start", "stop", "stop-all", "status", "cleanup"])
    parser.add_argument("--name", help="Persona name")
    parser.add_argument("--port", type=int, help="Port number")
    args = parser.parse_args()

    mgr = BackendManager()

    if args.command == "list":
        personas = mgr.list_personas()
        print(json.dumps(personas, indent=2))

    elif args.command == "start":
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        try:
            info = mgr.start_persona(args.name, args.port)
            print(json.dumps(asdict(info), indent=2))
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)

    elif args.command == "stop":
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        success = mgr.stop_persona(args.name)
        print(json.dumps({"stopped": success}))

    elif args.command == "stop-all":
        count = mgr.stop_all()
        print(json.dumps({"stopped": count}))

    elif args.command == "status":
        running = mgr.list_running()
        print(json.dumps(running, indent=2))

    elif args.command == "cleanup":
        count = mgr.cleanup_stale()
        print(json.dumps({"cleaned": count}))
