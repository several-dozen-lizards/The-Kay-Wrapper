# main_bridge.py
"""
Terminal interface for Kay wrapper using WrapperBridge.

This replaces the monolithic main.py with a thin terminal shell.
Same full pipeline as Nexus mode — single codebase, two entry points.

Usage:
    python main_bridge.py              # Terminal mode (default)
    python main_bridge.py --nexus      # Launch as Nexus client instead
"""

import asyncio
import sys
import os

# Ensure wrapper dir is on path and CWD
WRAPPER_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WRAPPER_DIR)
os.chdir(WRAPPER_DIR)

from wrapper_bridge import WrapperBridge


async def terminal_mode():
    """Interactive terminal conversation loop using WrapperBridge."""
    print("=" * 60)
    print("  KAY WRAPPER — Terminal Mode (Bridge Architecture)")
    print("=" * 60)
    
    bridge = WrapperBridge(entity_name="Kay", wrapper_dir=WRAPPER_DIR)
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
            print(f"\nKay: {reply}\n")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    
    finally:
        await bridge.shutdown()


async def nexus_mode(server_url="ws://localhost:8765"):
    """Launch Kay as Nexus client."""
    from nexus.nexus_kay import KayNexusClient
    
    client = KayNexusClient(server_url=server_url)
    await client.run()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Kay Wrapper")
    parser.add_argument("--nexus", action="store_true", help="Connect to Nexus server")
    parser.add_argument("--server", "-s", default="ws://localhost:8765", help="Nexus server URL")
    args = parser.parse_args()
    
    if args.nexus:
        asyncio.run(nexus_mode(args.server))
    else:
        asyncio.run(terminal_mode())


if __name__ == "__main__":
    main()
