"""
Je Ne Sais Quoi — Companion Manager
Each companion gets their own room. Nothing shared.

This module handles:
- Listing available companions
- Saving current state as a companion
- Loading a companion's state
- Creating new companions from template
- One-time migration of legacy persona/memory to companion format

Directory structure per companion:
    companions/{name}/
        who_i_am/           # Identity files (immutable)
            persona.json
            personality.md
            modules.json
            oscillator_profile.json
        my_life/            # State files (mutable)
            memory/
            sessions/
            chronicle/
            documents/
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class CompanionManager:
    """
    Manages companion lifecycle: save, load, create, migrate.

    Philosophy: Each companion is fully isolated. Their memories,
    personality, and state never leak between companions.
    """

    def __init__(self, wrapper_root: str):
        self.root = Path(wrapper_root)
        self.companions_dir = self.root / "companions"
        self.active_file = self.root / "active_companion.json"
        self.template_dir = self.companions_dir / "_template"
        self.companions_dir.mkdir(exist_ok=True)
        self._ensure_template()
        self._load_active()

    def _ensure_template(self):
        """Create template directory if missing."""
        if not self.template_dir.exists():
            (self.template_dir / "who_i_am").mkdir(parents=True, exist_ok=True)
            (self.template_dir / "my_life" / "memory" / "vector_db").mkdir(parents=True, exist_ok=True)
            (self.template_dir / "my_life" / "memory" / "resonant").mkdir(parents=True, exist_ok=True)
            (self.template_dir / "my_life" / "sessions").mkdir(parents=True, exist_ok=True)
            (self.template_dir / "my_life" / "chronicle").mkdir(parents=True, exist_ok=True)
            (self.template_dir / "my_life" / "documents").mkdir(parents=True, exist_ok=True)
            print("[JNSQ] Created companion template directory")

    def _load_active(self):
        """Load active companion tracking file."""
        if self.active_file.exists():
            try:
                with open(self.active_file) as f:
                    self._active = json.load(f)
            except json.JSONDecodeError:
                self._active = {"current": None, "last_used": {}, "port_assignments": {}}
        else:
            self._active = {"current": None, "last_used": {}, "port_assignments": {}}

    def _save_active(self):
        """Save active companion tracking file."""
        with open(self.active_file, 'w') as f:
            json.dump(self._active, f, indent=2)

    def get_current(self) -> Optional[str]:
        """Get the name of the currently active companion."""
        return self._active.get("current")

    def set_current(self, name: str):
        """Set the currently active companion."""
        self._active["current"] = name
        self._active["last_used"][name] = datetime.now().isoformat()
        self._save_active()

    def list_companions(self) -> List[Dict[str, Any]]:
        """
        List all companions with basic info.

        Returns list of dicts with:
            name: Directory name
            display_name: From persona config
            pronouns: Dict with subject/object/possessive
            description: Relationship description
            active: True if this is the current companion
            has_memories: True if memory directory has content
        """
        result = []
        for d in sorted(self.companions_dir.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue

            info = {"name": d.name, "active": d.name == self.get_current()}

            # Try to read display name from config
            for config_name in ["persona.json", "persona_config.json"]:
                config_file = d / "who_i_am" / config_name
                if config_file.exists():
                    try:
                        with open(config_file) as f:
                            cfg = json.load(f)
                        info["display_name"] = cfg.get("entity", {}).get("display_name", d.name)
                        info["pronouns"] = cfg.get("entity", {}).get("pronouns", {})
                        info["description"] = cfg.get("relationship", {}).get("relationship_description", "")
                    except Exception:
                        pass
                    break

            if "display_name" not in info:
                info["display_name"] = d.name

            # Check if has saved state
            memory_dir = d / "my_life" / "memory"
            info["has_memories"] = memory_dir.exists() and any(memory_dir.iterdir()) if memory_dir.exists() else False
            result.append(info)

        return result

    def get_companion_dir(self, name: str) -> Optional[Path]:
        """Get the directory path for a companion, or None if not found."""
        path = self.companions_dir / name
        if path.exists() and path.is_dir():
            return path
        return None

    def save_companion(self, name: str, source_dirs: Dict[str, str] = None) -> str:
        """
        Save current state as a companion.

        Args:
            name: Companion name (directory name)
            source_dirs: Dict mapping category to source path:
                {"persona": "persona/", "memory": "memory/", "sessions": "sessions/", ...}

        Returns:
            Path to the saved companion directory.
        """
        if source_dirs is None:
            source_dirs = {}

        dest = self.companions_dir / name
        who = dest / "who_i_am"
        life = dest / "my_life"
        who.mkdir(parents=True, exist_ok=True)
        life.mkdir(parents=True, exist_ok=True)

        # Save identity files
        persona_dir = Path(source_dirs.get("persona", self.root / "persona"))
        if persona_dir.exists():
            for f in persona_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, who / f.name)

        # Save modules.json if at root
        modules_src = self.root / "modules.json"
        if modules_src.exists():
            shutil.copy2(modules_src, who / "modules.json")

        # Save state directories
        for subdir in ["memory", "sessions", "chronicle", "documents"]:
            src = Path(source_dirs.get(subdir, self.root / subdir))
            dst = life / subdir
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                dst.mkdir(parents=True, exist_ok=True)

        self._active["current"] = name
        self._active["last_used"][name] = datetime.now().isoformat()
        self._save_active()

        return str(dest)

    def load_companion(self, name: str) -> bool:
        """
        Load a companion's files into the active directories.

        Args:
            name: Companion name to load

        Returns:
            True if successful, False if companion not found.
        """
        src = self.companions_dir / name
        if not src.exists():
            return False

        who = src / "who_i_am"
        life = src / "my_life"

        # Load identity → persona/
        persona_dest = self.root / "persona"
        persona_dest.mkdir(exist_ok=True)

        if who.exists():
            # Clear current persona files
            for f in persona_dest.iterdir():
                if f.is_file():
                    f.unlink()
            # Copy companion's identity
            for f in who.iterdir():
                if f.is_file() and f.name != "modules.json":
                    shutil.copy2(f, persona_dest / f.name)
            # Copy modules.json to root if present
            mod_src = who / "modules.json"
            if mod_src.exists():
                shutil.copy2(mod_src, self.root / "modules.json")

        # Load state directories
        for subdir in ["memory", "sessions", "chronicle"]:
            src_dir = life / subdir
            dst_dir = self.root / subdir
            if src_dir.exists():
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(src_dir, dst_dir)

        self._active["current"] = name
        self._active["last_used"][name] = datetime.now().isoformat()
        self._save_active()
        return True

    def create_companion(self, name: str) -> Optional[str]:
        """
        Create a new empty companion from template.

        Args:
            name: Name for the new companion (directory name)

        Returns:
            Path to the created companion, or None if already exists.
        """
        dest = self.companions_dir / name
        if dest.exists():
            return None  # Already exists
        shutil.copytree(self.template_dir, dest)
        return str(dest)

    def delete_companion(self, name: str) -> bool:
        """
        Delete a companion entirely.

        Args:
            name: Companion name to delete

        Returns:
            True if deleted, False if not found.
        """
        path = self.companions_dir / name
        if not path.exists() or name.startswith("_"):
            return False

        shutil.rmtree(path)

        # Clear from active if it was current
        if self._active.get("current") == name:
            self._active["current"] = None
        if name in self._active.get("last_used", {}):
            del self._active["last_used"][name]
        self._save_active()

        return True

    def migrate_current(self) -> Optional[str]:
        """
        One-time migration: save current legacy persona+memory as a companion.

        Called on first run when companions/ is empty but persona/ exists.
        Does NOT delete the original files — just creates a copy in companions/.

        Returns:
            Name of the migrated companion, or None if nothing to migrate.
        """
        persona_config = self.root / "persona" / "persona_config.json"
        if not persona_config.exists():
            return None

        try:
            with open(persona_config) as f:
                cfg = json.load(f)
            name = cfg.get("entity", {}).get("entity_id", "default")
        except Exception:
            name = "default"

        dest = self.companions_dir / name
        if dest.exists():
            # Already migrated
            self._active["current"] = name
            self._save_active()
            return name

        # Perform migration
        self.save_companion(name, {
            "persona": str(self.root / "persona"),
            "memory": str(self.root / "memory"),
            "sessions": str(self.root / "sessions"),
            "chronicle": str(self.root / "chronicle"),
        })

        print(f"[JNSQ] Migrated existing companion to companions/{name}/")
        return name

    def get_port_for_companion(self, name: str, base_port: int = 8780) -> int:
        """
        Get or assign a unique port for a companion.
        Used for multi-instance mode where each companion needs its own port.
        """
        ports = self._active.get("port_assignments", {})
        if name in ports:
            return ports[name]

        # Find next available port
        used_ports = set(ports.values())
        port = base_port
        while port in used_ports:
            port += 1

        ports[name] = port
        self._active["port_assignments"] = ports
        self._save_active()
        return port

    def export_companion(self, name: str, export_path: str, include_memories: bool = False) -> str:
        """
        Export a companion as a zip file.

        Args:
            name: Companion name to export
            export_path: Directory to save the export
            include_memories: If True, include my_life/. If False, only who_i_am/.

        Returns:
            Path to the created zip file.
        """
        import zipfile

        src = self.companions_dir / name
        if not src.exists():
            raise FileNotFoundError(f"Companion '{name}' not found")

        # Create export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "_full" if include_memories else "_identity"
        zip_name = f"{name}{suffix}_{timestamp}.zip"
        zip_path = Path(export_path) / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Always include who_i_am
            for root, dirs, files in os.walk(src / "who_i_am"):
                for file in files:
                    file_path = Path(root) / file
                    arcname = f"{name}/who_i_am/{file_path.relative_to(src / 'who_i_am')}"
                    zf.write(file_path, arcname)

            # Optionally include my_life
            if include_memories:
                for root, dirs, files in os.walk(src / "my_life"):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = f"{name}/my_life/{file_path.relative_to(src / 'my_life')}"
                        zf.write(file_path, arcname)

        return str(zip_path)

    def import_companion(self, zip_path: str) -> str:
        """
        Import a companion from a zip file.

        Args:
            zip_path: Path to the companion zip file

        Returns:
            Name of the imported companion.
        """
        import zipfile

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Get companion name from zip structure
            names = zf.namelist()
            if not names:
                raise ValueError("Empty zip file")

            # First path component is the companion name
            name = names[0].split('/')[0]

            dest = self.companions_dir / name
            if dest.exists():
                # Add timestamp to avoid overwrite
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"{name}_{timestamp}"
                dest = self.companions_dir / name

            # Extract
            dest.mkdir(parents=True, exist_ok=True)
            for member in zf.namelist():
                # Rebase paths
                parts = member.split('/', 1)
                if len(parts) > 1:
                    new_path = dest / parts[1]
                    if member.endswith('/'):
                        new_path.mkdir(parents=True, exist_ok=True)
                    else:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(new_path, 'wb') as dst:
                            dst.write(src.read())

        return name
