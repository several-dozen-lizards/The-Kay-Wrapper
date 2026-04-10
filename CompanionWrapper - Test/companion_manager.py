#!/usr/bin/env python3
"""
Je Ne Sais Quoi — Companion Manager

Multi-instance persona management CLI for the JNSQ framework.

Usage:
  jnsq list                      # List all personas + status
  jnsq create                    # Interactive creation
  jnsq create --from-doc FILE    # Create from document
  jnsq start PERSONA_NAME        # Start a companion instance
  jnsq stop PERSONA_NAME         # Stop a running instance
  jnsq stop --all                # Stop all running instances
  jnsq status                    # Show running instances
  jnsq export PERSONA_NAME       # Export persona as .zip
  jnsq import FILE.zip           # Import a persona package
  jnsq delete PERSONA_NAME       # Delete persona
  jnsq port PERSONA_NAME [PORT]  # Show/change port
  jnsq edit PERSONA_NAME         # Edit system prompt
  jnsq clone PERSONA_NAME NEW    # Clone persona
  jnsq migrate                   # Migrate existing instance
  jnsq info PERSONA_NAME         # Show persona details
"""

import os
import sys
import json
import shutil
import socket
import signal
import zipfile
import argparse
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

# Base directory for the companion wrapper
WRAPPER_ROOT = Path(__file__).parent.absolute()
PERSONAS_DIR = WRAPPER_ROOT / "personas"
INSTANCES_DIR = WRAPPER_ROOT / "instances"
MANAGER_PATH = WRAPPER_ROOT / "manager.json"

# Port configuration
NEXUS_RESERVED_PORTS = [8765, 8770, 8771]  # Never use these
PORT_RANGE_START = 8780
PORT_RANGE_END = 8799


def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def load_manager() -> Dict[str, Any]:
    """Load or create the manager registry."""
    if MANAGER_PATH.exists():
        with open(MANAGER_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Create default manager config
    return {
        "personas": {},
        "port_range": [PORT_RANGE_START, PORT_RANGE_END],
        "next_port": PORT_RANGE_START,
        "nexus_ports": NEXUS_RESERVED_PORTS
    }


def save_manager(manager: Dict[str, Any]):
    """Save the manager registry."""
    with open(MANAGER_PATH, 'w', encoding='utf-8') as f:
        json.dump(manager, f, indent=2)


def ensure_directories():
    """Create the personas/ and instances/ directories if they don't exist."""
    PERSONAS_DIR.mkdir(exist_ok=True)
    INSTANCES_DIR.mkdir(exist_ok=True)


def is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    if port in NEXUS_RESERVED_PORTS:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False


def get_next_available_port(manager: Dict[str, Any]) -> int:
    """Find the next available port in the allowed range."""
    used_ports = set()
    for persona in manager.get("personas", {}).values():
        if persona.get("port"):
            used_ports.add(persona["port"])

    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if port not in used_ports and port not in NEXUS_RESERVED_PORTS:
            if is_port_available(port):
                return port

    raise RuntimeError(f"No available ports in range {PORT_RANGE_START}-{PORT_RANGE_END}")


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    if pid is None:
        return False
    try:
        if platform.system() == "Windows":
            # Windows: check if process exists
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                capture_output=True, text=True
            )
            return str(pid) in result.stdout
        else:
            # Unix: send signal 0 to check existence
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.SubprocessError):
        return False


def cleanup_stale_entries(manager: Dict[str, Any]) -> int:
    """Check for and clean up stale entries. Returns count of cleaned entries."""
    cleaned = 0
    for name, persona in manager.get("personas", {}).items():
        if persona.get("status") == "running":
            pid = persona.get("pid")
            if not is_process_running(pid):
                print(f"  [!] {name}: Process {pid} not running, marking as stopped")
                persona["status"] = "stopped"
                persona["pid"] = None
                cleaned += 1
    return cleaned


def get_persona_description(persona_dir: Path) -> str:
    """Extract description from persona config."""
    config_path = persona_dir / "persona_config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            rel = config.get("relationship", {})
            return rel.get("relationship_description", "")[:50]
        except:
            pass
    return ""


# ============================================================================
# COMMANDS
# ============================================================================

def cmd_list(args):
    """List all personas and their status."""
    ensure_directories()
    manager = load_manager()
    cleaned = cleanup_stale_entries(manager)
    if cleaned:
        save_manager(manager)

    personas = manager.get("personas", {})

    if not personas:
        print("\n  No personas registered.")
        print("  Run 'python companion_manager.py create' to create one.")
        print("  Or 'python companion_manager.py migrate' to import an existing persona.\n")
        return

    print("\n  " + "=" * 75)
    print(f"  {'Name':<15} {'Status':<10} {'Port':<6} {'Last Active':<18} Description")
    print("  " + "-" * 75)

    for name, info in sorted(personas.items()):
        status = info.get("status", "unknown")
        port = info.get("port", "-")
        last_active = info.get("last_active", "")[:16].replace("T", " ")
        desc = info.get("description", "")[:30]

        # Status indicator
        status_display = f"{'●' if status == 'running' else '○'} {status}"

        print(f"  {name:<15} {status_display:<10} {port:<6} {last_active:<18} {desc}")

    print("  " + "=" * 75 + "\n")


def cmd_create(args):
    """Create a new persona."""
    ensure_directories()
    manager = load_manager()

    # Run the setup wizard
    if args.from_doc:
        # Document import mode
        wizard_args = ["python", str(WRAPPER_ROOT / "setup_wizard.py"), "--import", args.from_doc]
    else:
        # Interactive mode
        wizard_args = ["python", str(WRAPPER_ROOT / "setup_wizard.py")]

    print("\n  Starting persona setup wizard...\n")

    # The wizard writes to persona/ directory by default
    # We need to capture the name and move it to personas/NAME/
    result = subprocess.run(wizard_args, cwd=str(WRAPPER_ROOT))

    if result.returncode != 0:
        print("  [!] Setup wizard failed or was cancelled.")
        return

    # Check if a new persona was created in persona/
    default_persona_dir = WRAPPER_ROOT / "persona"
    config_path = default_persona_dir / "persona_config.json"

    if not config_path.exists():
        print("  [!] No persona config found after wizard.")
        return

    # Read the persona name
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    entity_id = config.get("entity", {}).get("entity_id", "companion")
    name = entity_id.lower().replace(" ", "_")

    # Check if persona already exists
    if name in manager.get("personas", {}):
        print(f"  [!] Persona '{name}' already exists. Use a different name.")
        return

    # Create persona directory
    new_persona_dir = PERSONAS_DIR / name
    new_persona_dir.mkdir(exist_ok=True)

    # Copy files to the new location
    for filename in ["persona_config.json", "system_prompt.md", "resonance_profile.json", "modules.json"]:
        src = default_persona_dir / filename
        if src.exists():
            shutil.copy2(src, new_persona_dir / filename)

    # Create instance directory
    instance_dir = INSTANCES_DIR / name
    instance_dir.mkdir(exist_ok=True)
    (instance_dir / "memory").mkdir(exist_ok=True)
    (instance_dir / "sessions").mkdir(exist_ok=True)
    (instance_dir / "chronicle").mkdir(exist_ok=True)

    # Assign port
    port = get_next_available_port(manager)

    # Register in manager
    manager.setdefault("personas", {})[name] = {
        "persona_dir": f"personas/{name}",
        "instance_dir": f"instances/{name}",
        "port": port,
        "status": "stopped",
        "pid": None,
        "created": get_timestamp(),
        "last_active": get_timestamp(),
        "description": get_persona_description(new_persona_dir)
    }

    save_manager(manager)

    print(f"\n  [+] Created persona '{name}' on port {port}")
    print(f"      Persona files: {new_persona_dir}")
    print(f"      Instance data: {instance_dir}")
    print(f"\n  Start with: python companion_manager.py start {name}\n")


def cmd_start(args):
    """Start a companion instance."""
    ensure_directories()
    manager = load_manager()
    cleanup_stale_entries(manager)

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.")
        print(f"  Available: {', '.join(personas.keys()) or 'none'}\n")
        return

    persona = personas[name]

    if persona.get("status") == "running" and is_process_running(persona.get("pid")):
        print(f"\n  [!] '{name}' is already running (PID {persona['pid']}, port {persona['port']})\n")
        return

    # Verify port is available
    port = persona.get("port", PORT_RANGE_START)
    if not is_port_available(port):
        print(f"\n  [!] Port {port} is in use. Finding alternative...")
        port = get_next_available_port(manager)
        persona["port"] = port
        print(f"  [+] Assigned new port: {port}")

    # Build paths
    persona_dir = WRAPPER_ROOT / persona["persona_dir"]
    instance_dir = WRAPPER_ROOT / persona["instance_dir"]

    # Verify persona exists
    if not (persona_dir / "persona_config.json").exists():
        print(f"\n  [!] Persona config not found at {persona_dir}\n")
        return

    # Set up environment
    env = os.environ.copy()
    env["COMPANION_NAME"] = name
    env["COMPANION_PORT"] = str(port)
    env["COMPANION_PERSONA_DIR"] = str(persona_dir)
    env["COMPANION_MEMORY_DIR"] = str(instance_dir / "memory")
    env["COMPANION_SESSION_DIR"] = str(instance_dir / "sessions")
    env["COMPANION_INSTANCE_DIR"] = str(instance_dir)

    # Start the process
    print(f"\n  Starting {name} on port {port}...")

    # Use main.py with --ui flag to enable the private room server
    main_py = WRAPPER_ROOT / "main.py"

    if platform.system() == "Windows":
        # Windows: use CREATE_NEW_PROCESS_GROUP for proper subprocess handling
        process = subprocess.Popen(
            [sys.executable, str(main_py), "--ui", "--room-port", str(port)],
            cwd=str(WRAPPER_ROOT),
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        # Unix: start in new process group
        process = subprocess.Popen(
            [sys.executable, str(main_py), "--ui", "--room-port", str(port)],
            cwd=str(WRAPPER_ROOT),
            env=env,
            start_new_session=True
        )

    # Update manager
    persona["status"] = "running"
    persona["pid"] = process.pid
    persona["last_active"] = get_timestamp()
    save_manager(manager)

    # Write instance state
    instance_state = {
        "persona_name": name,
        "port": port,
        "pid": process.pid,
        "started_at": get_timestamp(),
        "status": "running",
        "memory_dir": str(instance_dir / "memory"),
        "session_dir": str(instance_dir / "sessions")
    }
    with open(instance_dir / "instance.json", 'w', encoding='utf-8') as f:
        json.dump(instance_state, f, indent=2)

    print(f"  [+] Started '{name}' (PID {process.pid})")
    print(f"      WebSocket: ws://localhost:{port}")
    print(f"      HTTP API:  http://localhost:{port + 5}\n")


def cmd_stop(args):
    """Stop a running instance."""
    ensure_directories()
    manager = load_manager()

    if args.all:
        # Stop all running instances
        stopped = 0
        for name, persona in manager.get("personas", {}).items():
            if persona.get("status") == "running":
                _stop_persona(name, persona)
                stopped += 1
        save_manager(manager)
        print(f"\n  [+] Stopped {stopped} instance(s)\n")
        return

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.\n")
        return

    persona = personas[name]

    if persona.get("status") != "running":
        print(f"\n  [!] '{name}' is not running.\n")
        return

    _stop_persona(name, persona)
    save_manager(manager)
    print(f"\n  [+] Stopped '{name}'\n")


def _stop_persona(name: str, persona: Dict[str, Any]):
    """Internal: Stop a persona process."""
    pid = persona.get("pid")

    if pid and is_process_running(pid):
        try:
            if platform.system() == "Windows":
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
                # Wait up to 10 seconds for graceful shutdown
                import time
                for _ in range(10):
                    if not is_process_running(pid):
                        break
                    time.sleep(1)
                else:
                    os.kill(pid, signal.SIGKILL)
        except Exception as e:
            print(f"  [!] Error stopping {name}: {e}")

    persona["status"] = "stopped"
    persona["pid"] = None
    persona["last_active"] = get_timestamp()

    # Update instance state
    instance_dir = WRAPPER_ROOT / persona.get("instance_dir", f"instances/{name}")
    instance_json = instance_dir / "instance.json"
    if instance_json.exists():
        try:
            with open(instance_json, 'r', encoding='utf-8') as f:
                state = json.load(f)
            state["status"] = "stopped"
            state["stopped_at"] = get_timestamp()
            with open(instance_json, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except:
            pass


def cmd_status(args):
    """Show status of all running instances."""
    ensure_directories()
    manager = load_manager()
    cleanup_stale_entries(manager)
    save_manager(manager)

    running = []
    for name, persona in manager.get("personas", {}).items():
        if persona.get("status") == "running":
            running.append((name, persona))

    if not running:
        print("\n  No companions currently running.\n")
        return

    print(f"\n  Running Companions ({len(running)}):")
    print("  " + "-" * 50)

    for name, persona in running:
        pid = persona.get("pid", "?")
        port = persona.get("port", "?")
        print(f"  {name:<15} PID: {pid:<8} Port: {port}")
        print(f"                  ws://localhost:{port}")

    print("  " + "-" * 50 + "\n")


def cmd_export(args):
    """Export a persona as a portable .zip package."""
    ensure_directories()
    manager = load_manager()

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.\n")
        return

    persona = personas[name]
    persona_dir = WRAPPER_ROOT / persona["persona_dir"]

    # Create zip file
    output_name = f"{name}_persona.zip"
    output_path = WRAPPER_ROOT / output_name

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in ["persona_config.json", "system_prompt.md", "resonance_profile.json", "modules.json"]:
            filepath = persona_dir / filename
            if filepath.exists():
                zf.write(filepath, filename)

    print(f"\n  [+] Exported '{name}' to {output_name}")
    print(f"      (Memory and API keys NOT included)\n")


def cmd_import(args):
    """Import a persona from a .zip package."""
    ensure_directories()
    manager = load_manager()

    zip_path = Path(args.file)
    if not zip_path.exists():
        print(f"\n  [!] File not found: {zip_path}\n")
        return

    # Extract to temp location first to read config
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)

        config_path = Path(tmpdir) / "persona_config.json"
        if not config_path.exists():
            print("\n  [!] Invalid persona package: missing persona_config.json\n")
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        name = config.get("entity", {}).get("entity_id", "imported").lower()

        # Check if already exists
        if name in manager.get("personas", {}):
            confirm = input(f"  Persona '{name}' already exists. Overwrite? [y/N]: ")
            if confirm.lower() != 'y':
                print("  Cancelled.\n")
                return

        # Copy to personas directory
        new_persona_dir = PERSONAS_DIR / name
        new_persona_dir.mkdir(exist_ok=True)

        for filename in ["persona_config.json", "system_prompt.md", "resonance_profile.json", "modules.json"]:
            src = Path(tmpdir) / filename
            if src.exists():
                shutil.copy2(src, new_persona_dir / filename)

    # Create instance directory
    instance_dir = INSTANCES_DIR / name
    instance_dir.mkdir(exist_ok=True)
    (instance_dir / "memory").mkdir(exist_ok=True)
    (instance_dir / "sessions").mkdir(exist_ok=True)
    (instance_dir / "chronicle").mkdir(exist_ok=True)

    # Assign port
    port = get_next_available_port(manager)

    # Register
    manager.setdefault("personas", {})[name] = {
        "persona_dir": f"personas/{name}",
        "instance_dir": f"instances/{name}",
        "port": port,
        "status": "stopped",
        "pid": None,
        "created": get_timestamp(),
        "last_active": get_timestamp(),
        "description": get_persona_description(new_persona_dir)
    }
    save_manager(manager)

    print(f"\n  [+] Imported '{name}' on port {port}")
    print(f"      Add your API key to: {new_persona_dir}/.env")
    print(f"      Or use the global .env in the wrapper root.\n")


def cmd_delete(args):
    """Delete a persona (with confirmation)."""
    ensure_directories()
    manager = load_manager()

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.\n")
        return

    persona = personas[name]

    # Stop if running
    if persona.get("status") == "running":
        print(f"  [!] '{name}' is running. Stopping first...")
        _stop_persona(name, persona)

    # Confirm
    print(f"\n  WARNING: This will delete ALL data for '{name}':")
    print(f"    - Persona configuration")
    print(f"    - All memories")
    print(f"    - All session logs")
    print(f"    - All chronicle data")

    confirm = input(f"\n  Type '{name}' to confirm deletion: ")
    if confirm != name:
        print("  Cancelled.\n")
        return

    # Delete directories
    persona_dir = WRAPPER_ROOT / persona["persona_dir"]
    instance_dir = WRAPPER_ROOT / persona["instance_dir"]

    if persona_dir.exists():
        shutil.rmtree(persona_dir)
    if instance_dir.exists():
        shutil.rmtree(instance_dir)

    # Remove from manager
    del personas[name]
    save_manager(manager)

    print(f"\n  [+] Deleted '{name}'\n")


def cmd_port(args):
    """Show or change port assignment."""
    ensure_directories()
    manager = load_manager()

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.\n")
        return

    persona = personas[name]

    if args.new_port:
        new_port = int(args.new_port)

        # Validate
        if new_port in NEXUS_RESERVED_PORTS:
            print(f"\n  [!] Port {new_port} is reserved for Nexus.\n")
            return

        if not is_port_available(new_port):
            print(f"\n  [!] Port {new_port} is in use.\n")
            return

        if persona.get("status") == "running":
            print(f"  [!] '{name}' is running. Stop it first to change ports.\n")
            return

        persona["port"] = new_port
        save_manager(manager)
        print(f"\n  [+] '{name}' port changed to {new_port}\n")
    else:
        print(f"\n  {name}: port {persona.get('port', 'unassigned')}\n")


def cmd_edit(args):
    """Open persona files in editor."""
    ensure_directories()
    manager = load_manager()

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.\n")
        return

    persona = personas[name]
    persona_dir = WRAPPER_ROOT / persona["persona_dir"]

    # Determine which file to edit
    if args.config:
        filepath = persona_dir / "persona_config.json"
    elif args.modules:
        filepath = persona_dir / "modules.json"
    elif args.resonance:
        filepath = persona_dir / "resonance_profile.json"
    else:
        filepath = persona_dir / "system_prompt.md"

    if not filepath.exists():
        print(f"\n  [!] File not found: {filepath}\n")
        return

    # Open in editor
    editor = os.environ.get("EDITOR", None)

    if platform.system() == "Windows":
        os.startfile(str(filepath))
    elif platform.system() == "Darwin":
        subprocess.run(["open", str(filepath)])
    elif editor:
        subprocess.run([editor, str(filepath)])
    else:
        subprocess.run(["xdg-open", str(filepath)])

    print(f"\n  [+] Opened: {filepath}")

    if persona.get("status") == "running":
        print(f"  [!] '{name}' is running. Restart to apply changes.\n")


def cmd_clone(args):
    """Clone a persona."""
    ensure_directories()
    manager = load_manager()

    source_name = args.name.lower()
    new_name = args.new_name.lower().replace(" ", "_")

    personas = manager.get("personas", {})

    if source_name not in personas:
        print(f"\n  [!] Persona '{source_name}' not found.\n")
        return

    if new_name in personas:
        print(f"\n  [!] Persona '{new_name}' already exists.\n")
        return

    source = personas[source_name]
    source_persona_dir = WRAPPER_ROOT / source["persona_dir"]
    source_instance_dir = WRAPPER_ROOT / source["instance_dir"]

    # Create new directories
    new_persona_dir = PERSONAS_DIR / new_name
    new_instance_dir = INSTANCES_DIR / new_name

    new_persona_dir.mkdir(exist_ok=True)
    new_instance_dir.mkdir(exist_ok=True)

    # Copy persona files
    for filename in ["persona_config.json", "system_prompt.md", "resonance_profile.json", "modules.json"]:
        src = source_persona_dir / filename
        if src.exists():
            shutil.copy2(src, new_persona_dir / filename)

    # Update the cloned config with new name
    config_path = new_persona_dir / "persona_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config["entity"]["entity_id"] = new_name
    config["entity"]["name"] = new_name.replace("_", " ").title()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    # Optionally copy memory
    if args.with_memory:
        if source_instance_dir.exists():
            shutil.copytree(source_instance_dir, new_instance_dir, dirs_exist_ok=True)
        print(f"  [+] Copied memories from '{source_name}'")
    else:
        # Create empty instance directories
        (new_instance_dir / "memory").mkdir(exist_ok=True)
        (new_instance_dir / "sessions").mkdir(exist_ok=True)
        (new_instance_dir / "chronicle").mkdir(exist_ok=True)

    # Assign port
    port = get_next_available_port(manager)

    # Register
    personas[new_name] = {
        "persona_dir": f"personas/{new_name}",
        "instance_dir": f"instances/{new_name}",
        "port": port,
        "status": "stopped",
        "pid": None,
        "created": get_timestamp(),
        "last_active": get_timestamp(),
        "description": f"Clone of {source_name}"
    }
    save_manager(manager)

    print(f"\n  [+] Cloned '{source_name}' -> '{new_name}' on port {port}")
    if not args.with_memory:
        print(f"      (Fresh memory - use --with-memory to copy memories)\n")


def cmd_migrate(args):
    """Migrate existing persona from default location into management system."""
    ensure_directories()
    manager = load_manager()

    # Look for existing persona in the default location
    default_persona_dir = WRAPPER_ROOT / "persona"
    default_memory_dir = WRAPPER_ROOT / "memory"
    default_sessions_dir = WRAPPER_ROOT / "sessions"

    config_path = default_persona_dir / "persona_config.json"

    if not config_path.exists():
        print("\n  [!] No existing persona found in ./persona/")
        print("  Run 'python companion_manager.py create' to create a new one.\n")
        return

    # Read persona config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    entity_id = config.get("entity", {}).get("entity_id", "companion")
    name = entity_id.lower().replace(" ", "_")
    display_name = config.get("entity", {}).get("display_name", name)

    print(f"\n  Found persona: {display_name} ({name})")

    # Check if already migrated
    if name in manager.get("personas", {}):
        print(f"  [!] Persona '{name}' already exists in management system.")
        print(f"  Use 'python companion_manager.py info {name}' to see details.\n")
        return

    # Check for memory
    has_memory = default_memory_dir.exists() and any(default_memory_dir.iterdir())
    has_sessions = default_sessions_dir.exists() and any(default_sessions_dir.iterdir())

    if has_memory:
        print(f"  Found memory directory with {len(list(default_memory_dir.iterdir()))} items")
    if has_sessions:
        print(f"  Found sessions directory with {len(list(default_sessions_dir.iterdir()))} items")

    # Ask for confirmation
    print(f"\n  This will move files into the management structure:")
    print(f"    ./persona/ -> ./personas/{name}/")
    if has_memory:
        print(f"    ./memory/  -> ./instances/{name}/memory/")
    if has_sessions:
        print(f"    ./sessions/ -> ./instances/{name}/sessions/")

    confirm = input("\n  Proceed? [Y/n]: ")
    if confirm.lower() == 'n':
        print("  Cancelled.\n")
        return

    # Create new directories
    new_persona_dir = PERSONAS_DIR / name
    new_instance_dir = INSTANCES_DIR / name

    new_persona_dir.mkdir(exist_ok=True)
    new_instance_dir.mkdir(exist_ok=True)

    # Move persona files
    for filename in ["persona_config.json", "system_prompt.md", "resonance_profile.json", "modules.json"]:
        src = default_persona_dir / filename
        if src.exists():
            shutil.copy2(src, new_persona_dir / filename)

    # Move memory and sessions (copy, don't delete originals until confirmed working)
    if has_memory:
        shutil.copytree(default_memory_dir, new_instance_dir / "memory", dirs_exist_ok=True)
    else:
        (new_instance_dir / "memory").mkdir(exist_ok=True)

    if has_sessions:
        shutil.copytree(default_sessions_dir, new_instance_dir / "sessions", dirs_exist_ok=True)
    else:
        (new_instance_dir / "sessions").mkdir(exist_ok=True)

    (new_instance_dir / "chronicle").mkdir(exist_ok=True)

    # Assign port
    port = get_next_available_port(manager)

    # Register
    manager.setdefault("personas", {})[name] = {
        "persona_dir": f"personas/{name}",
        "instance_dir": f"instances/{name}",
        "port": port,
        "status": "stopped",
        "pid": None,
        "created": get_timestamp(),
        "last_active": get_timestamp(),
        "description": get_persona_description(new_persona_dir)
    }
    save_manager(manager)

    print(f"\n  [+] Migrated '{name}' to management system")
    print(f"      Port: {port}")
    print(f"      Persona: ./personas/{name}/")
    print(f"      Instance: ./instances/{name}/")
    print(f"\n  Original files preserved in ./persona/, ./memory/, ./sessions/")
    print(f"  Delete them manually after confirming migration works.\n")
    print(f"  Start with: python companion_manager.py start {name}\n")


def cmd_info(args):
    """Show detailed information about a persona."""
    ensure_directories()
    manager = load_manager()

    name = args.name.lower()
    personas = manager.get("personas", {})

    if name not in personas:
        print(f"\n  [!] Persona '{name}' not found.\n")
        return

    persona = personas[name]
    persona_dir = WRAPPER_ROOT / persona["persona_dir"]
    instance_dir = WRAPPER_ROOT / persona["instance_dir"]

    # Load persona config
    config_path = persona_dir / "persona_config.json"
    config = {}
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # Load modules
    modules_path = persona_dir / "modules.json"
    modules = {}
    if modules_path.exists():
        with open(modules_path, 'r', encoding='utf-8') as f:
            modules = json.load(f)

    # Count memory items
    memory_dir = instance_dir / "memory"
    memory_count = 0
    vector_count = 0
    if memory_dir.exists():
        for f in memory_dir.glob("**/*"):
            if f.is_file():
                if "chroma" in str(f) or "vector" in str(f):
                    vector_count += 1
                else:
                    memory_count += 1

    # Count sessions
    sessions_dir = instance_dir / "sessions"
    session_count = len(list(sessions_dir.glob("*.json"))) if sessions_dir.exists() else 0

    # Display
    entity = config.get("entity", {})
    rel = config.get("relationship", {})

    print(f"\n  {'=' * 60}")
    print(f"  Persona: {entity.get('display_name', name)}")
    print(f"  {'=' * 60}")
    print(f"\n  Status: {'● running' if persona.get('status') == 'running' else '○ stopped'}")
    print(f"  Port: {persona.get('port', 'unassigned')}")
    if persona.get("pid"):
        print(f"  PID: {persona['pid']}")
    print(f"  Created: {persona.get('created', 'unknown')[:16].replace('T', ' ')}")
    print(f"  Last Active: {persona.get('last_active', 'unknown')[:16].replace('T', ' ')}")

    print(f"\n  Identity:")
    print(f"    Entity ID: {entity.get('entity_id', name)}")
    pronouns = entity.get("pronouns", {})
    print(f"    Pronouns: {pronouns.get('subject', 'they')}/{pronouns.get('object', 'them')}")
    print(f"    Voice: {entity.get('voice_description', 'Not specified')[:50]}")

    if modules:
        print(f"\n  Modules:")
        for mod, enabled in modules.items():
            status = "ON" if enabled else "OFF"
            print(f"    {mod}: {status}")

    print(f"\n  Memory:")
    print(f"    Memory files: {memory_count}")
    print(f"    Vector store files: {vector_count}")
    print(f"    Session logs: {session_count}")

    print(f"\n  Files:")
    print(f"    {persona_dir}/persona_config.json")
    print(f"    {persona_dir}/system_prompt.md")
    print(f"    {instance_dir}/memory/")
    print(f"    {instance_dir}/sessions/")
    print(f"\n  {'=' * 60}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Print banner
    print()
    print("=" * 45)
    print("  JE NE SAIS QUOI — Companion Manager")
    print("=" * 45)
    print()

    parser = argparse.ArgumentParser(
        description="Je Ne Sais Quoi — Companion Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog="jnsq"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list
    subparsers.add_parser("list", help="List all personas and their status")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new persona")
    create_parser.add_argument("--from-doc", metavar="FILE", help="Create from document")

    # start
    start_parser = subparsers.add_parser("start", help="Start a companion instance")
    start_parser.add_argument("name", help="Persona name to start")

    # stop
    stop_parser = subparsers.add_parser("stop", help="Stop a running instance")
    stop_parser.add_argument("name", nargs="?", help="Persona name to stop")
    stop_parser.add_argument("--all", action="store_true", help="Stop all running instances")

    # status
    subparsers.add_parser("status", help="Show running instances")

    # export
    export_parser = subparsers.add_parser("export", help="Export persona as .zip")
    export_parser.add_argument("name", help="Persona name to export")

    # import
    import_parser = subparsers.add_parser("import", help="Import persona from .zip")
    import_parser.add_argument("file", help="Path to .zip file")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a persona")
    delete_parser.add_argument("name", help="Persona name to delete")

    # port
    port_parser = subparsers.add_parser("port", help="Show or change port assignment")
    port_parser.add_argument("name", help="Persona name")
    port_parser.add_argument("new_port", nargs="?", help="New port number")

    # edit
    edit_parser = subparsers.add_parser("edit", help="Edit persona files")
    edit_parser.add_argument("name", help="Persona name")
    edit_parser.add_argument("--config", action="store_true", help="Edit persona_config.json")
    edit_parser.add_argument("--modules", action="store_true", help="Edit modules.json")
    edit_parser.add_argument("--resonance", action="store_true", help="Edit resonance_profile.json")

    # clone
    clone_parser = subparsers.add_parser("clone", help="Clone a persona")
    clone_parser.add_argument("name", help="Source persona name")
    clone_parser.add_argument("new_name", help="New persona name")
    clone_parser.add_argument("--with-memory", action="store_true", help="Copy memories too")

    # migrate
    subparsers.add_parser("migrate", help="Migrate existing persona into management system")

    # info
    info_parser = subparsers.add_parser("info", help="Show persona details")
    info_parser.add_argument("name", help="Persona name")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "list": cmd_list,
        "create": cmd_create,
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "export": cmd_export,
        "import": cmd_import,
        "delete": cmd_delete,
        "port": cmd_port,
        "edit": cmd_edit,
        "clone": cmd_clone,
        "migrate": cmd_migrate,
        "info": cmd_info,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
