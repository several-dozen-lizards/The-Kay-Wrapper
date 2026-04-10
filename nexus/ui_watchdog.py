"""
Godot UI Watchdog
Monitors the Nexus Godot UI and restarts it if it dies.

Can run alongside the main launcher, or be integrated into it.

Usage:
    python ui_watchdog.py              # Start and monitor UI
    python ui_watchdog.py --once       # Launch once, no restart

SETUP: Set GODOT_EXE below to your Godot executable path.
       Find it: open Godot editor, Help → About → look at the window title bar
       Or check where you installed Godot (e.g., C:\\Godot\\Godot_v4.3-stable_win64.exe)
"""

import subprocess
import sys
import time
import signal
from pathlib import Path
from datetime import datetime

# =============================================
# CONFIGURE THESE
# =============================================

# Path to your Godot executable
# Common locations:
#   C:\Godot\Godot_v4.3-stable_win64.exe
#   C:\Users\lewis\Downloads\Godot_v4.3-stable_win64.exe  
#   Wherever you extracted/installed Godot
GODOT_EXE = r"C:\Godot\Godot_v4.3-stable_win64.exe"

# Path to the Nexus UI project
PROJECT_DIR = Path(__file__).parent / "godot-ui"

# How long to wait before restarting after a crash (seconds)
RESTART_DELAY = 10

# Max restarts before giving up (0 = unlimited)
MAX_RESTARTS = 0

# =============================================

class UIWatchdog:
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.running = True
    
    def launch_godot(self) -> bool:
        """Launch the Godot game window (not the editor)."""
        godot = Path(GODOT_EXE)
        if not godot.exists():
            print(f"  ✗ Godot not found at: {GODOT_EXE}")
            print(f"  → Edit GODOT_EXE in {__file__}")
            return False
        
        if not PROJECT_DIR.exists():
            print(f"  ✗ Project not found at: {PROJECT_DIR}")
            return False
        
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] → Launching Godot UI...")
        
        # Run the project directly (not the editor)
        # --path: project directory
        # No --editor flag = runs the game
        self.process = subprocess.Popen(
            [str(godot), "--path", str(PROJECT_DIR)],
            cwd=str(PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        print(f"  [{ts}] ✓ Godot UI started (PID {self.process.pid})")
        return True
    
    def monitor(self, restart=True):
        """Monitor the Godot process and restart if it dies."""
        if not self.launch_godot():
            return
        
        print(f"  → Monitoring Godot UI (PID {self.process.pid})...")
        if restart:
            print(f"  → Auto-restart: ON (delay: {RESTART_DELAY}s)")
        print()
        
        try:
            while self.running:
                retcode = self.process.poll()
                
                if retcode is not None:
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"\n  [{ts}] ⚠ Godot UI exited (code {retcode})")
                    
                    if not restart:
                        print(f"  [{ts}] → Single-run mode, not restarting.")
                        break
                    
                    self.restart_count += 1
                    if MAX_RESTARTS > 0 and self.restart_count >= MAX_RESTARTS:
                        print(f"  [{ts}] ✗ Max restarts ({MAX_RESTARTS}) reached. Giving up.")
                        break
                    
                    print(f"  [{ts}] → Restarting in {RESTART_DELAY}s... (restart #{self.restart_count})")
                    time.sleep(RESTART_DELAY)
                    
                    if not self.launch_godot():
                        print(f"  [{ts}] ✗ Failed to restart. Giving up.")
                        break
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n  → Shutting down Godot UI...")
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            print("  ✓ Godot UI stopped.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Godot UI Watchdog")
    parser.add_argument("--once", action="store_true",
                        help="Launch once, don't restart on crash")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  🖥️  GODOT UI WATCHDOG")
    print("=" * 50)
    print()
    
    watchdog = UIWatchdog()
    
    # Handle Ctrl+C gracefully  
    signal.signal(signal.SIGINT, lambda s, f: setattr(watchdog, 'running', False))
    
    watchdog.monitor(restart=not args.once)


if __name__ == "__main__":
    main()
