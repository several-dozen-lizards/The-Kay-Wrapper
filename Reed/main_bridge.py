# main_bridge.py
"""
Terminal interface for Reed wrapper using WrapperBridge.

This replaces the monolithic main.py with a thin terminal shell.
Same full pipeline as Nexus mode — single codebase, two entry points.
Includes Phase 3 engines (ContinuousSession, FlaggingSystem, CurationInterface).

Usage:
    python main_bridge.py              # Terminal mode (default)
    python main_bridge.py --nexus      # Launch as Nexus client instead
"""

import asyncio
import sys
import os
import io

# === Windows UTF-8 Encoding Fix ===
# Prevents UnicodeEncodeError on emoji/special chars in Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONUTF8', '1')

# Ensure wrapper dir is on path and CWD
WRAPPER_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WRAPPER_DIR)
os.chdir(WRAPPER_DIR)

from wrapper_bridge import WrapperBridge


async def terminal_mode():
    """Interactive terminal conversation loop using WrapperBridge."""
    print("=" * 60)
    print("  REED WRAPPER — Terminal Mode (Bridge Architecture)")
    print("  Phase 3: Continuous Session + Flagging + Curation")
    print("=" * 60)
    
    bridge = WrapperBridge(entity_name="Reed", wrapper_dir=WRAPPER_DIR)
    await bridge.startup()
    
    print("\nType 'quit' or 'exit' to end session.")
    print("Commands: /affect N, /forest, /tree NAME, /import PATH")
    print("          /forget PATTERN, /corrupt PATTERN, /prune [DAYS]")
    print("          /deletions, /github COMMAND\n")
    
    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit"):
                break
            
            # Check for commands first
            handled, cmd_response = bridge.process_command(user_input)
            if handled:
                if cmd_response:
                    print(cmd_response)
                continue
            
            # Full pipeline
            reply = await bridge.process_message(user_input, source="terminal")
            print(f"\nReed: {reply}\n")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    
    finally:
        await bridge.shutdown()


async def nexus_mode(server_url="ws://localhost:8765"):
    """Launch Reed as Nexus client."""
    from nexus.nexus_reed import ReedNexusClient
    
    client = ReedNexusClient(server_url=server_url)
    await client.run()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Reed Wrapper")
    parser.add_argument("--nexus", action="store_true", help="Connect to Nexus server")
    parser.add_argument("--server", "-s", default="ws://localhost:8765", help="Nexus server URL")
    args = parser.parse_args()
    
    if args.nexus:
        asyncio.run(nexus_mode(args.server))
    else:
        asyncio.run(terminal_mode())


if __name__ == "__main__":
    main()
