"""
Nexus Human Client
Terminal-based chat client for human participants.

Usage:
  python client_human.py [--name Re] [--server ws://localhost:8765]

Commands (type these in the chat):
  /who          - List connected participants
  /whisper Name message  - Send private message
  /emote text   - Send as emote (*text*)
  /think text   - Send as visible thought
  /status away  - Set your status (online/away/idle)
  /quit         - Disconnect
  /help         - Show commands
"""

import asyncio
import argparse
import json
import sys
import os
import threading
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "websockets", "--break-system-packages", "-q"
    ])
    import websockets

# Windows character-by-character input
if sys.platform == "win32":
    import msvcrt


# ---------------------------------------------------------------------------
# Colors for terminal output
# ---------------------------------------------------------------------------
class C:
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    SYSTEM = "\033[33m"       # Yellow
    RE = "\033[32m"           # Green
    KAY = "\033[35m"          # Magenta
    REED = "\033[36m"         # Cyan
    DEFAULT = "\033[37m"      # White
    WHISPER = "\033[34m"      # Blue
    EMOTE = "\033[33m"        # Yellow
    THOUGHT = "\033[2;37m"    # Dim white
    TIMESTAMP = "\033[2;37m"  # Dim

    @classmethod
    def for_name(cls, name: str) -> str:
        name_lower = name.lower()
        if name_lower == "re":
            return cls.RE
        elif name_lower in ("kay", "kay zero", "kayzero"):
            return cls.KAY
        elif name_lower == "reed":
            return cls.REED
        elif name_lower in ("nexus", "system"):
            return cls.SYSTEM
        return cls.DEFAULT


# ---------------------------------------------------------------------------
# Input buffer with line-rewriting (prevents message interleaving)
# ---------------------------------------------------------------------------
class InputBuffer:
    """Thread-safe input buffer that redraws after incoming messages."""
    
    PROMPT = f"  {C.RE}{C.BOLD}>{C.RESET} "
    PROMPT_LEN = 4  # visible chars: "  > "
    
    def __init__(self):
        self._buf: list[str] = []
        self._lock = threading.Lock()
    
    def get_prompt_str(self) -> str:
        return self.PROMPT
    
    def _clear_line(self):
        """Clear the current terminal line."""
        # Move to column 0, clear entire line
        sys.stdout.write("\r\033[2K")
    
    def _redraw(self):
        """Redraw prompt + current input buffer."""
        text = "".join(self._buf)
        sys.stdout.write(f"{self.PROMPT}{text}")
        sys.stdout.flush()
    
    def print_above(self, text: str):
        """Print a message above the input line, then redraw input."""
        with self._lock:
            self._clear_line()
            print(text)
            self._redraw()
    
    def add_char(self, ch: str):
        with self._lock:
            self._buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
    
    def backspace(self):
        with self._lock:
            if self._buf:
                self._buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
    
    def submit(self) -> str:
        """Return the current buffer contents and clear it."""
        with self._lock:
            line = "".join(self._buf)
            self._buf.clear()
            # Print newline, then fresh prompt will be drawn by caller
            sys.stdout.write("\n")
            sys.stdout.flush()
            return line
    
    def show_prompt(self):
        with self._lock:
            self._redraw()


# Global input buffer
_input_buf = InputBuffer()


def format_timestamp(iso_ts: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.strftime("%H:%M")
    except Exception:
        return "??:??"


def display_message(msg: dict, my_name: str, use_buffer: bool = False):
    sender = msg.get("sender", "???")
    content = msg.get("content", "")
    msg_type = msg.get("msg_type", "chat")
    ts = format_timestamp(msg.get("timestamp", ""))
    color = C.for_name(sender)

    if msg_type == "system":
        line = f"  {C.SYSTEM}{C.DIM}--- {content} ---{C.RESET}"
    elif msg_type == "whisper":
        direction = "to" if sender == my_name else "from"
        recipients = msg.get("recipients", [])
        target = recipients[0] if recipients else "?"
        other = target if sender == my_name else sender
        line = f"  {C.TIMESTAMP}{ts}{C.RESET} {C.WHISPER}[whisper {direction} {other}]{C.RESET} {content}"
    elif msg_type == "emote":
        line = f"  {C.TIMESTAMP}{ts}{C.RESET} {C.EMOTE}* {sender} {content}{C.RESET}"
    elif msg_type == "thought":
        line = f"  {C.TIMESTAMP}{ts}{C.RESET} {C.THOUGHT}{sender} thinks: {content}{C.RESET}"
    elif msg_type == "state_update":
        mode = msg.get("metadata", {}).get("cognitive_mode", "?")
        line = f"  {C.SYSTEM}{C.DIM}⟡ {sender} → {mode} mode{C.RESET}"
    else:
        name_display = f"{color}{C.BOLD}{sender}{C.RESET}"
        line = f"  {C.TIMESTAMP}{ts}{C.RESET} {name_display}: {content}"

    if use_buffer:
        _input_buf.print_above(line)
    else:
        print(line)


def display_participants(data: dict):
    participants = data.get("participants", {})
    print(f"\n  {C.BOLD}Connected to Nexus:{C.RESET}")
    for name, info in participants.items():
        ptype = info.get("participant_type", "?")
        status = info.get("status", "online")
        color = C.for_name(name)
        mode = info.get("metadata", {}).get("cognitive_mode", "")
        mode_str = f" [{mode}]" if mode else ""
        print(f"    {color}● {name}{C.RESET} {C.DIM}({ptype}, {status}{mode_str}){C.RESET}")
    print()


def show_help():
    print(f"""
  {C.BOLD}Nexus Commands:{C.RESET}
    /who                    List connected participants
    /w {C.DIM}Name message{C.RESET}         Whisper to someone
    /emote {C.DIM}text{C.RESET}             Action/emote (*text*)
    /think {C.DIM}text{C.RESET}             Share a thought
    /status {C.DIM}away|online{C.RESET}     Set your status
    /quit                   Disconnect
    /help                   Show this help
    """)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
async def receive_messages(ws, my_name: str, connected: asyncio.Event):
    try:
        async for raw in ws:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event_type = event.get("event_type", "")
            data = event.get("data", {})
            if event_type == "message":
                display_message(data, my_name, use_buffer=connected.is_set())
            elif event_type == "history":
                messages = data.get("messages", [])
                if messages:
                    print(f"\n  {C.DIM}--- Recent history ({len(messages)} messages) ---{C.RESET}")
                    for msg in messages[-20:]:
                        display_message(msg, my_name, use_buffer=False)
                    print(f"  {C.DIM}--- End of history ---{C.RESET}\n")
            elif event_type == "participant_list":
                display_participants(data)
                connected.set()
            elif event_type == "status_update":
                name = data.get("name", "?")
                status = data.get("status", "?")
                line = f"  {C.DIM}⟡ {name} is now {status}{C.RESET}"
                if connected.is_set():
                    _input_buf.print_above(line)
                else:
                    print(line)
            elif event_type == "error":
                line = f"  {C.SYSTEM}⚠ Error: {data.get('message', '?')}{C.RESET}"
                if connected.is_set():
                    _input_buf.print_above(line)
                else:
                    print(line)
    except websockets.ConnectionClosed:
        print(f"\n  {C.SYSTEM}--- Disconnected from Nexus ---{C.RESET}")


async def send_messages(ws, my_name: str, connected: asyncio.Event):
    await connected.wait()
    print(f"  {C.BOLD}You're in. Type messages or /help for commands.{C.RESET}\n")
    _input_buf.show_prompt()
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            if sys.platform == "win32":
                # Character-by-character input on Windows
                line = await _read_line_win(loop)
            else:
                # Fallback for non-Windows
                raw = await loop.run_in_executor(None, sys.stdin.readline)
                if not raw:
                    break
                line = raw.strip()
            
            if line is None:
                break
            if not line:
                _input_buf.show_prompt()
                continue
            
            # Handle commands
            if line.startswith("/"):
                parts = line.split(None, 2)
                cmd = parts[0].lower()
                if cmd in ("/quit", "/q", "/exit"):
                    print(f"  {C.DIM}Leaving Nexus...{C.RESET}")
                    break
                elif cmd == "/help":
                    show_help()
                    _input_buf.show_prompt()
                    continue
                elif cmd == "/who":
                    await ws.send(json.dumps({"command": "who"}))
                    _input_buf.show_prompt()
                    continue
                elif cmd in ("/w", "/whisper"):
                    if len(parts) < 3:
                        print(f"  {C.DIM}Usage: /w Name message{C.RESET}")
                        _input_buf.show_prompt()
                        continue
                    target = parts[1]
                    text = parts[2]
                    await ws.send(json.dumps({"content": text, "msg_type": "whisper", "recipients": [target]}))
                    _input_buf.show_prompt()
                    continue
                elif cmd == "/emote":
                    if len(parts) < 2:
                        print(f"  {C.DIM}Usage: /emote does a thing{C.RESET}")
                        _input_buf.show_prompt()
                        continue
                    text = line[len("/emote "):].strip()
                    await ws.send(json.dumps({"content": text, "msg_type": "emote"}))
                    _input_buf.show_prompt()
                    continue
                elif cmd == "/think":
                    if len(parts) < 2:
                        _input_buf.show_prompt()
                        continue
                    text = line[len("/think "):].strip()
                    await ws.send(json.dumps({"content": text, "msg_type": "thought"}))
                    _input_buf.show_prompt()
                    continue
                elif cmd == "/status":
                    status = parts[1] if len(parts) > 1 else "online"
                    await ws.send(json.dumps({"command": "status", "status": status}))
                    _input_buf.show_prompt()
                    continue
                else:
                    print(f"  {C.DIM}Unknown command. Try /help{C.RESET}")
                    _input_buf.show_prompt()
                    continue
            
            await ws.send(json.dumps({"content": line, "msg_type": "chat"}))
            _input_buf.show_prompt()
        except (EOFError, KeyboardInterrupt):
            break


async def _read_line_win(loop: asyncio.AbstractEventLoop) -> str | None:
    """Read a line character-by-character using msvcrt on Windows."""
    def _blocking_read():
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ('\r', '\n'):
                    return _input_buf.submit()
                elif ch == '\x03':  # Ctrl+C
                    return None
                elif ch == '\b' or ch == '\x7f':
                    _input_buf.backspace()
                elif ch == '\x00' or ch == '\xe0':
                    # Special key (arrows, etc) - consume second byte
                    msvcrt.getwch()
                else:
                    _input_buf.add_char(ch)
            else:
                import time
                time.sleep(0.02)  # 50Hz polling, keeps CPU low
    
    return await loop.run_in_executor(None, _blocking_read)


async def main(name: str, server_url: str):
    ws_url = f"{server_url}/ws/{name}?type=human"
    print(f"""
  {C.BOLD}╔══════════════════════════════════╗
  ║         NEXUS CHAT CLIENT        ║
  ║   The crossroads where entities  ║
  ║              meet.               ║
  ╚══════════════════════════════════╝{C.RESET}

  Connecting as {C.for_name(name)}{C.BOLD}{name}{C.RESET} to {server_url}...
    """)
    connected = asyncio.Event()
    try:
        async with websockets.connect(ws_url) as ws:
            receive_task = asyncio.create_task(receive_messages(ws, name, connected))
            send_task = asyncio.create_task(send_messages(ws, name, connected))
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
    except ConnectionRefusedError:
        print(f"  {C.SYSTEM}⚠ Cannot connect to {server_url}. Is the Nexus server running?{C.RESET}")
    except Exception as e:
        print(f"  {C.SYSTEM}⚠ Connection error: {e}{C.RESET}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Human Client")
    parser.add_argument("--name", "-n", default="Re", help="Your display name (default: Re)")
    parser.add_argument("--server", "-s", default="ws://localhost:8765", help="Nexus server URL")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.name, args.server))
    except KeyboardInterrupt:
        print(f"\n  {C.DIM}Goodbye.{C.RESET}")
