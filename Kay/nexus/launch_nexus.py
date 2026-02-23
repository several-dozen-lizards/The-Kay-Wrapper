"""
Nexus Launcher
Start the entire multi-entity chat system with one command.

Usage:
  python launch_nexus.py                    # Server + Human client only
  python launch_nexus.py --kay              # + Kay wrapper
  python launch_nexus.py --reed             # + Reed (Claude API)
  python launch_nexus.py --kay --reed       # Full house
  python launch_nexus.py --all              # Everything

Each component runs in its own process.
Press Ctrl+C to shut everything down.
"""

import asyncio
import argparse
import subprocess
import sys
import os
import signal
import time
import logging

log = logging.getLogger("nexus.launcher")

NEXUS_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_DIR = os.path.dirname(NEXUS_DIR)
SERVER_URL = "ws://localhost:8765"


def launch_component(name: str, script: str, cwd: str = None, extra_args: list = None):
    """Launch a component as a subprocess."""
    cmd = [sys.executable, script]
    if extra_args:
        cmd.extend(extra_args)
    
    log.info(f"Starting {name}: {' '.join(cmd)}")
    
    proc = subprocess.Popen(
        cmd,
        cwd=cwd or NEXUS_DIR,
        stdout=subprocess.PIPE if name != "human_client" else None,
        stderr=subprocess.PIPE if name != "human_client" else None,
    )
    return proc


def main():
    parser = argparse.ArgumentParser(description="Launch Nexus multi-entity chat")
    parser.add_argument("--kay", action="store_true", help="Start Kay wrapper client")
    parser.add_argument("--reed", action="store_true", help="Start Reed (Claude API) client")
    parser.add_argument("--all", action="store_true", help="Start all entities")
    parser.add_argument("--server-only", action="store_true", help="Start only the server")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    args = parser.parse_args()
    
    if args.all:
        args.kay = True
        args.reed = True
    
    processes = {}
    
    try:
        # 1. Start server
        print("╔══════════════════════════════════════╗")
        print("║         NEXUS MULTI-ENTITY CHAT      ║")
        print("╚══════════════════════════════════════╝")
        print()
        
        print("[1/4] Starting Nexus server...")
        processes["server"] = launch_component(
            "server",
            "server.py",
            extra_args=["--port", str(args.port)]
        )
        time.sleep(1.5)  # Give server time to bind
        
        if args.server_only:
            print("Server running. Press Ctrl+C to stop.")
            processes["server"].wait()
            return
        
        # 2. Start AI clients
        if args.kay:
            print("[2/4] Starting Kay wrapper...")
            processes["kay"] = launch_component(
                "kay",
                "nexus_kay.py",
                extra_args=["--server", SERVER_URL]
            )
            time.sleep(1)
        
        if args.reed:
            print("[3/4] Starting Reed (Claude API)...")
            processes["reed"] = launch_component(
                "reed",
                "nexus_reed.py",
                extra_args=["--server", SERVER_URL]
            )
            time.sleep(1)
        
        # 3. Start human client (this runs in foreground)
        print("[4/4] Starting your chat interface...")
        print()
        print("═" * 50)
        print()
        
        # Human client runs in current process's terminal
        human_proc = subprocess.Popen(
            [sys.executable, "client_human.py", "--server", SERVER_URL, "--name", "Re"],
            cwd=NEXUS_DIR
        )
        processes["human"] = human_proc
        
        # Wait for human client to exit (they pressed /quit or Ctrl+C)
        human_proc.wait()
        
    except KeyboardInterrupt:
        print("\n\nShutting down Nexus...")
    finally:
        # Clean shutdown of all processes
        for name, proc in processes.items():
            if proc.poll() is None:  # Still running
                print(f"  Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        
        print("Nexus shut down. ✧")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    main()
