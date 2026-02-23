"""
Nexus Launcher
Starts the Nexus server + Kay wrapper + Reed wrapper.

Usage:
    python launch_nexus.py              # Start everything
    python launch_nexus.py --no-kay     # Skip Kay
    python launch_nexus.py --no-reed    # Skip Reed
    python launch_nexus.py --server-only # Server only

The Godot UI connects separately (run from Godot editor or export).
"""

import subprocess
import sys
import os
import time
import signal
import socket
import argparse
from pathlib import Path

NEXUS_DIR = Path(__file__).parent
KAY_DIR = NEXUS_DIR.parent / "Kay"

# Component configs
COMPONENTS = {
    "server": {
        "script": NEXUS_DIR / "server.py",
        "label": "Nexus Server",
        "delay": 2.0,  # Wait for server before starting clients
    },
    "kay": {
        "script": NEXUS_DIR / "nexus_kay.py",
        "label": "Kay (Nexus Client)",
        "delay": 1.0,
    },
    "reed": {
        "script": NEXUS_DIR / "nexus_reed.py",
        "label": "Reed (Nexus Client)",
        "delay": 1.0,
    },
}

processes: list[tuple[str, subprocess.Popen]] = []

# Ports used by Nexus components
NEXUS_PORTS = [8765, 8770, 8771]  # server, kay private, reed private


def check_and_free_ports():
    """Check if any Nexus ports are in use and kill the holders."""
    blocked = []
    for port in NEXUS_PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            sock.close()
        except OSError:
            blocked.append(port)
            sock.close()

    if not blocked:
        return True

    print(f"  ⚠ Ports in use: {blocked}")
    print("  → Killing zombie processes on those ports...")

    for port in blocked:
        # Find PID holding the port
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True, timeout=5
                        )
                        print(f"  ✓ Killed PID {pid} (port {port})")
                    except Exception:
                        pass
        except Exception as e:
            print(f"  ✗ Could not free port {port}: {e}")

    # Brief wait for OS to release
    time.sleep(1)

    # Verify
    still_blocked = []
    for port in blocked:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            sock.close()
        except OSError:
            still_blocked.append(port)
            sock.close()

    if still_blocked:
        print(f"  ✗ STILL blocked: {still_blocked}. Try closing apps manually.")
        return False
    print("  ✓ All ports free")
    return True


def wait_for_server(timeout=10):
    """Wait until the Nexus server is actually listening on 8765."""
    start = time.time()
    while time.time() - start < timeout:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", 8765))
            sock.close()
            return True
        except (ConnectionRefusedError, OSError):
            sock.close()
            time.sleep(0.5)
    return False


def start_component(name: str, config: dict) -> subprocess.Popen:
    script = config["script"]
    label = config["label"]

    if not script.exists():
        print(f"  ✗ {label}: {script} not found!")
        return None

    print(f"  → Starting {label}...")
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(script.parent),
        # Let output flow to terminal for debugging
        stdout=None,
        stderr=None,
    )
    print(f"  ✓ {label} started (PID {proc.pid})")
    return proc


def shutdown_all():
    print("\n🛑 Shutting down Nexus...")
    for name, proc in reversed(processes):
        if proc and proc.poll() is None:
            print(f"  → Stopping {name} (PID {proc.pid})...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            print(f"  ✓ {name} stopped")
    print("✨ Nexus shutdown complete.")


def main():
    parser = argparse.ArgumentParser(description="Launch the Nexus system")
    parser.add_argument("--no-kay", action="store_true", help="Don't start Kay")
    parser.add_argument("--no-reed", action="store_true", help="Don't start Reed")
    parser.add_argument("--server-only", action="store_true", help="Server only")
    args = parser.parse_args()

    print("=" * 50)
    print("  🌐 NEXUS LAUNCHER")
    print("=" * 50)
    print()

    # Determine what to start
    to_start = ["server"]
    if not args.server_only:
        if not args.no_kay:
            to_start.append("kay")
        if not args.no_reed:
            to_start.append("reed")

    print(f"Components: {', '.join(to_start)}")
    print()

    # Clean up zombie processes on our ports
    if not check_and_free_ports():
        print("  ✗ Cannot start — ports still blocked. Exiting.")
        sys.exit(1)

    # Register signal handler
    signal.signal(signal.SIGINT, lambda s, f: shutdown_all() or sys.exit(0))
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, lambda s, f: shutdown_all() or sys.exit(0))

    # Start components
    for name in to_start:
        config = COMPONENTS[name]
        proc = start_component(name, config)
        if proc:
            processes.append((config["label"], proc))
            if name == "server":
                # Wait until server is actually listening before starting clients
                print("  → Waiting for server to be ready...")
                if wait_for_server(timeout=10):
                    print("  ✓ Server is listening on port 8765")
                else:
                    print("  ✗ Server failed to start within 10s!")
                    # Check if it crashed
                    if proc.poll() is not None:
                        print(f"  ✗ Server exited with code {proc.returncode}")
                        print("  → Aborting launch.")
                        shutdown_all()
                        sys.exit(1)
                    print("  → Continuing anyway (may still be starting)...")
            else:
                time.sleep(config["delay"])
        else:
            print(f"  ⚠ Failed to start {name}, continuing...")
    
    print()
    print("=" * 50)
    print("  ✅ Nexus is running!")
    print("  Start Godot UI separately to connect.")
    print("  Press Ctrl+C to shut down all components.")
    print("=" * 50)
    print()

    # Monitor loop
    reported_dead = set()
    try:
        while True:
            all_dead = True
            server_dead = False
            for label, proc in processes:
                if proc.poll() is not None:
                    if label not in reported_dead:
                        print(f"  ⚠ {label} exited (code {proc.returncode})")
                        reported_dead.add(label)
                    if "Server" in label:
                        server_dead = True
                else:
                    all_dead = False

            if server_dead:
                print("\n  ✗ Nexus Server died — shutting down clients.")
                shutdown_all()
                sys.exit(1)

            if all_dead:
                print("\n  All components exited.")
                break

            time.sleep(5)
    except KeyboardInterrupt:
        shutdown_all()


if __name__ == "__main__":
    main()
