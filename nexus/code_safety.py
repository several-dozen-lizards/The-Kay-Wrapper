# code_safety.py
"""
Safety, logging, and permission system for entity code execution.

Four layers:
  1. Execution Log   — every run logged with full details
  2. File Write Jail  — restrict writes to scratch + explicitly permitted paths
  3. Snapshots        — backup scratch state before each run, one-command revert
  4. Approval Mode    — optional human-in-the-loop per entity

Used by code_executor.py. Config stored per-entity in:
  D:/Wrappers/nexus/scratch/{entity}/.exec_config.json

Execution log stored at:
  D:/Wrappers/nexus/scratch/{entity}/.exec_log.jsonl
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger("nexus.code_safety")

SCRATCH_ROOT = Path("D:/Wrappers/nexus/scratch")


# ---------------------------------------------------------------------------
# Entity Permissions
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "mode": "supervised",           # "supervised" (queue for approval) or "autonomous" (run immediately)
    "allowed_write_paths": [],      # Extra paths entity can write to (scratch always allowed)
    "allowed_read_paths": [],       # Extra restricted read paths (empty = read anything)
    "blocked_patterns": [],         # Additional blocked code patterns beyond global list
    "max_timeout_s": 30,            # Max timeout this entity can request
    "max_file_size_bytes": 10_000_000,  # 10MB max file creation size
    "notes": "",                    # Re's notes about this entity's permissions
}


class EntityPermissions:
    """Per-entity permission configuration."""

    def __init__(self, entity: str):
        self.entity = entity
        self.config_path = SCRATCH_ROOT / entity.lower() / ".exec_config.json"
        self.config = self._load()

    def _load(self) -> dict:
        """Load config from disk, creating defaults if missing."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    stored = json.load(f)
                # Merge with defaults (handles new fields added later)
                merged = {**DEFAULT_CONFIG, **stored}
                return merged
            except Exception as e:
                log.warning(f"Failed to load config for {self.entity}: {e}")
        return {**DEFAULT_CONFIG}

    def save(self):
        """Persist config to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
        log.info(f"[SAFETY] Saved config for {self.entity}")

    @property
    def mode(self) -> str:
        return self.config.get("mode", "supervised")

    @mode.setter
    def mode(self, value: str):
        if value not in ("supervised", "autonomous"):
            raise ValueError(f"Mode must be 'supervised' or 'autonomous', got '{value}'")
        self.config["mode"] = value
        self.save()

    @property
    def allowed_write_paths(self) -> list[str]:
        return self.config.get("allowed_write_paths", [])

    def add_write_path(self, path: str):
        """Grant write access to a specific path or directory."""
        resolved = str(Path(path).resolve())
        if resolved not in self.config["allowed_write_paths"]:
            self.config["allowed_write_paths"].append(resolved)
            self.save()
            log.info(f"[SAFETY] {self.entity}: granted write access to {resolved}")

    def remove_write_path(self, path: str):
        """Revoke write access to a path."""
        resolved = str(Path(path).resolve())
        if resolved in self.config["allowed_write_paths"]:
            self.config["allowed_write_paths"].remove(resolved)
            self.save()
            log.info(f"[SAFETY] {self.entity}: revoked write access to {resolved}")

    def is_write_allowed(self, filepath: str) -> bool:
        """Check if writing to this path is permitted."""
        resolved = str(Path(filepath).resolve())
        scratch = str((SCRATCH_ROOT / self.entity.lower()).resolve())

        # Scratch dir always allowed
        if resolved.startswith(scratch):
            return True

        # Check explicit permissions
        for allowed in self.allowed_write_paths:
            if resolved.startswith(allowed) or resolved == allowed:
                return True

        return False


# ---------------------------------------------------------------------------
# Execution Log
# ---------------------------------------------------------------------------

class ExecutionLog:
    """Append-only log of all code executions per entity."""

    def __init__(self, entity: str):
        self.entity = entity
        self.log_path = SCRATCH_ROOT / entity.lower() / ".exec_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry: dict):
        """Append an execution record."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "entity": self.entity,
            **entry,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            log.error(f"[SAFETY] Failed to write exec log: {e}")

    def get_recent(self, n: int = 20) -> list[dict]:
        """Get the N most recent log entries."""
        if not self.log_path.exists():
            return []
        entries = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            log.error(f"[SAFETY] Failed to read exec log: {e}")
        return entries[-n:]

    def get_by_id(self, exec_id: str) -> Optional[dict]:
        """Find a specific execution by its ID."""
        for entry in self.get_recent(1000):
            if entry.get("exec_id") == exec_id:
                return entry
        return None

    def summary(self, n: int = 10) -> str:
        """Human-readable summary of recent executions."""
        entries = self.get_recent(n)
        if not entries:
            return f"No executions logged for {self.entity}."
        lines = [f"=== Last {len(entries)} executions for {self.entity} ==="]
        for e in entries:
            ts = e.get("timestamp", "?")[:19]
            status = "OK" if e.get("success") else "FAIL"
            desc = e.get("description", "")[:60] or "(no description)"
            duration = e.get("execution_time", "?")
            action = e.get("action", "exec")
            files_touched = e.get("files_written", [])
            file_str = f" → {', '.join(files_touched)}" if files_touched else ""
            lines.append(f"  {status} [{ts}] {action}: {desc} ({duration}s){file_str}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Snapshot Manager — pre-execution backups + revert
# ---------------------------------------------------------------------------

class SnapshotManager:
    """Backup scratch state before executions, allow revert."""

    def __init__(self, entity: str):
        self.entity = entity
        self.scratch_dir = SCRATCH_ROOT / entity.lower()
        self.snapshot_dir = SCRATCH_ROOT / entity.lower() / ".snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def take_snapshot(self, exec_id: str) -> str:
        """Snapshot current scratch state. Returns snapshot path."""
        snap_path = self.snapshot_dir / exec_id
        snap_path.mkdir(parents=True, exist_ok=True)

        count = 0
        for f in self.scratch_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                shutil.copy2(str(f), str(snap_path / f.name))
                count += 1

        log.info(f"[SNAPSHOT] {self.entity}: saved {count} files as {exec_id}")
        return str(snap_path)

    def revert_to(self, exec_id: str) -> dict:
        """Revert scratch directory to a previous snapshot."""
        snap_path = self.snapshot_dir / exec_id
        if not snap_path.exists():
            return {"success": False, "error": f"Snapshot '{exec_id}' not found"}

        # Clear current non-hidden files
        removed = []
        for f in self.scratch_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                f.unlink()
                removed.append(f.name)

        # Restore from snapshot
        restored = []
        for f in snap_path.iterdir():
            if f.is_file():
                shutil.copy2(str(f), str(self.scratch_dir / f.name))
                restored.append(f.name)

        log.info(f"[SNAPSHOT] {self.entity}: reverted to {exec_id} "
                 f"(removed {len(removed)}, restored {len(restored)})")
        return {
            "success": True,
            "removed": removed,
            "restored": restored,
        }

    def list_snapshots(self) -> list[dict]:
        """List available snapshots."""
        if not self.snapshot_dir.exists():
            return []
        snaps = []
        for d in sorted(self.snapshot_dir.iterdir()):
            if d.is_dir():
                files = [f.name for f in d.iterdir() if f.is_file()]
                snaps.append({
                    "exec_id": d.name,
                    "file_count": len(files),
                    "created": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(d.stat().st_mtime)
                    ),
                })
        return snaps

    def cleanup_old(self, keep: int = 20):
        """Remove oldest snapshots, keeping the N most recent."""
        snaps = sorted(self.snapshot_dir.iterdir(), key=lambda d: d.stat().st_mtime)
        dirs = [d for d in snaps if d.is_dir()]
        if len(dirs) <= keep:
            return
        for d in dirs[:-keep]:
            shutil.rmtree(str(d))
            log.info(f"[SNAPSHOT] Cleaned up old snapshot: {d.name}")


# ---------------------------------------------------------------------------
# Approval Queue — human-in-the-loop for supervised mode
# ---------------------------------------------------------------------------

class ApprovalQueue:
    """Queue code for human review before execution."""

    def __init__(self, entity: str):
        self.entity = entity
        self.queue_path = SCRATCH_ROOT / entity.lower() / ".pending_queue.json"
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_queue(self) -> list[dict]:
        if self.queue_path.exists():
            try:
                with open(self.queue_path, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_queue(self, queue: list[dict]):
        with open(self.queue_path, "w") as f:
            json.dump(queue, f, indent=2)

    def enqueue(self, exec_id: str, code: str, language: str = "python",
                description: str = "", context: str = "") -> dict:
        """Add code to the approval queue. Returns the pending entry."""
        entry = {
            "exec_id": exec_id,
            "entity": self.entity,
            "code": code,
            "language": language,
            "description": description,
            "context": context,
            "queued_at": datetime.now().isoformat(),
            "status": "pending",  # pending, approved, denied
        }
        queue = self._load_queue()
        queue.append(entry)
        self._save_queue(queue)
        log.info(f"[APPROVAL] {self.entity}: queued exec {exec_id} for review")
        return entry

    def get_pending(self) -> list[dict]:
        """Get all pending (unapproved) entries."""
        return [e for e in self._load_queue() if e["status"] == "pending"]

    def approve(self, exec_id: str) -> Optional[dict]:
        """Approve a pending execution. Returns the entry if found."""
        queue = self._load_queue()
        for entry in queue:
            if entry["exec_id"] == exec_id and entry["status"] == "pending":
                entry["status"] = "approved"
                entry["reviewed_at"] = datetime.now().isoformat()
                self._save_queue(queue)
                log.info(f"[APPROVAL] {self.entity}: approved exec {exec_id}")
                return entry
        return None

    def deny(self, exec_id: str, reason: str = "") -> Optional[dict]:
        """Deny a pending execution."""
        queue = self._load_queue()
        for entry in queue:
            if entry["exec_id"] == exec_id and entry["status"] == "pending":
                entry["status"] = "denied"
                entry["deny_reason"] = reason
                entry["reviewed_at"] = datetime.now().isoformat()
                self._save_queue(queue)
                log.info(f"[APPROVAL] {self.entity}: denied exec {exec_id}: {reason}")
                return entry
        return None

    def approve_all(self) -> list[dict]:
        """Approve all pending entries. Returns list of approved."""
        queue = self._load_queue()
        approved = []
        for entry in queue:
            if entry["status"] == "pending":
                entry["status"] = "approved"
                entry["reviewed_at"] = datetime.now().isoformat()
                approved.append(entry)
        self._save_queue(queue)
        return approved

    def summary(self) -> str:
        """Human-readable summary of the queue."""
        pending = self.get_pending()
        if not pending:
            return f"No pending executions for {self.entity}."
        lines = [f"=== {len(pending)} pending execution(s) for {self.entity} ==="]
        for e in pending:
            desc = e.get("description", "")[:60] or "(no description)"
            code_preview = e["code"][:120].replace("\n", "\\n")
            lines.append(f"\n  ID: {e['exec_id']}")
            lines.append(f"  Desc: {desc}")
            lines.append(f"  Code: {code_preview}...")
            lines.append(f"  Queued: {e['queued_at'][:19]}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# File Write Jail — injected preamble that restricts file I/O
# ---------------------------------------------------------------------------

def build_jail_preamble(entity: str, perms: EntityPermissions) -> str:
    """
    Generate Python code that gets prepended to every execution.
    Monkey-patches open(), Path.write_text/write_bytes/open to enforce
    write restrictions. Reads are unrestricted.
    All file write attempts are logged to .file_access.jsonl
    """
    scratch = str((SCRATCH_ROOT / entity.lower()).resolve()).replace("\\", "/")
    allowed = [scratch]
    for p in perms.allowed_write_paths:
        allowed.append(str(Path(p).resolve()).replace("\\", "/"))

    allowed_json = json.dumps(allowed)

    return f'''
# === SAFETY JAIL (injected by code_safety.py) ===
import builtins as _builtins
import pathlib as _pathlib
import json as _json
import os as _os
from datetime import datetime as _datetime

_ALLOWED_WRITE_ROOTS = {allowed_json}
_ENTITY = {json.dumps(entity)}
_ACCESS_LOG = {json.dumps(str((SCRATCH_ROOT / entity.lower() / ".file_access.jsonl").resolve()).replace(chr(92), "/"))}

_original_open = _builtins.open
_original_path_write_text = _pathlib.Path.write_text
_original_path_write_bytes = _pathlib.Path.write_bytes
_original_path_open = _pathlib.Path.open
_original_path_mkdir = _pathlib.Path.mkdir

def _log_access(action, path, allowed, detail=""):
    try:
        record = {{
            "timestamp": _datetime.now().isoformat(),
            "entity": _ENTITY,
            "action": action,
            "path": str(path),
            "allowed": allowed,
            "detail": detail[:200],
        }}
        with _original_open(_ACCESS_LOG, "a", encoding="utf-8") as f:
            f.write(_json.dumps(record) + "\\n")
    except Exception:
        pass  # Don't let logging failures break execution

def _is_write_allowed(filepath):
    """Check if a resolved path is in allowed write roots."""
    try:
        resolved = str(_pathlib.Path(filepath).resolve()).replace("\\\\", "/")
        for root in _ALLOWED_WRITE_ROOTS:
            if resolved.startswith(root) or resolved == root:
                return True
        return False
    except Exception:
        return False

def _safe_open(file, mode="r", *args, **kwargs):
    """Patched open() that blocks writes outside allowed paths."""
    is_write = any(c in str(mode) for c in ("w", "a", "x", "+"))
    if is_write:
        resolved = str(_pathlib.Path(file).resolve())
        if not _is_write_allowed(resolved):
            _log_access("BLOCKED_WRITE", resolved, False, f"mode={{mode}}")
            raise PermissionError(
                f"Write blocked: {{resolved}}\\n"
                f"You can only write to your scratch directory.\\n"
                f"Ask Re to grant write access if you need to write elsewhere."
            )
        _log_access("write", resolved, True, f"mode={{mode}}")
    return _original_open(file, mode, *args, **kwargs)

def _safe_path_write_text(self, data, *args, **kwargs):
    resolved = str(self.resolve())
    if not _is_write_allowed(resolved):
        _log_access("BLOCKED_WRITE", resolved, False, "Path.write_text")
        raise PermissionError(f"Write blocked: {{resolved}}")
    _log_access("write", resolved, True, "Path.write_text")
    return _original_path_write_text(self, data, *args, **kwargs)

def _safe_path_write_bytes(self, data, *args, **kwargs):
    resolved = str(self.resolve())
    if not _is_write_allowed(resolved):
        _log_access("BLOCKED_WRITE", resolved, False, "Path.write_bytes")
        raise PermissionError(f"Write blocked: {{resolved}}")
    _log_access("write", resolved, True, "Path.write_bytes")
    return _original_path_write_bytes(self, data, *args, **kwargs)

def _safe_path_open(self, mode="r", *args, **kwargs):
    is_write = any(c in str(mode) for c in ("w", "a", "x", "+"))
    if is_write:
        resolved = str(self.resolve())
        if not _is_write_allowed(resolved):
            _log_access("BLOCKED_WRITE", resolved, False, f"Path.open mode={{mode}}")
            raise PermissionError(f"Write blocked: {{resolved}}")
        _log_access("write", resolved, True, f"Path.open mode={{mode}}")
    return _original_path_open(self, mode, *args, **kwargs)

# Apply patches
_builtins.open = _safe_open
_pathlib.Path.write_text = _safe_path_write_text
_pathlib.Path.write_bytes = _safe_path_write_bytes
_pathlib.Path.open = _safe_path_open
# === END SAFETY JAIL ===

'''


# ---------------------------------------------------------------------------
# Convenience API — for Re to manage entity permissions
# ---------------------------------------------------------------------------

def get_entity_config(entity: str) -> EntityPermissions:
    """Get or create permission config for an entity."""
    return EntityPermissions(entity)


def set_entity_mode(entity: str, mode: str):
    """Set entity to 'supervised' or 'autonomous' mode."""
    perms = EntityPermissions(entity)
    perms.mode = mode
    return f"{entity} set to {mode} mode."


def grant_write(entity: str, path: str):
    """Grant an entity write access to a specific path/directory."""
    perms = EntityPermissions(entity)
    perms.add_write_path(path)
    return f"{entity} granted write access to: {path}"


def revoke_write(entity: str, path: str):
    """Revoke write access from an entity."""
    perms = EntityPermissions(entity)
    perms.remove_write_path(path)
    return f"{entity} write access revoked for: {path}"


def get_exec_log(entity: str, n: int = 20) -> str:
    """Get human-readable execution log."""
    return ExecutionLog(entity).summary(n)


def get_file_access_log(entity: str, n: int = 50) -> list[dict]:
    """Get raw file access log entries."""
    log_path = SCRATCH_ROOT / entity.lower() / ".file_access.jsonl"
    if not log_path.exists():
        return []
    entries = []
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries[-n:]


def get_pending_approvals(entity: str) -> str:
    """Get human-readable pending approval summary."""
    return ApprovalQueue(entity).summary()


def approve_exec(entity: str, exec_id: str) -> str:
    """Approve a pending execution."""
    result = ApprovalQueue(entity).approve(exec_id)
    if result:
        return f"Approved: {exec_id}"
    return f"Not found or already reviewed: {exec_id}"


def deny_exec(entity: str, exec_id: str, reason: str = "") -> str:
    """Deny a pending execution."""
    result = ApprovalQueue(entity).deny(exec_id, reason)
    if result:
        return f"Denied: {exec_id} ({reason})"
    return f"Not found or already reviewed: {exec_id}"


def approve_all_pending(entity: str) -> str:
    """Approve all pending executions for an entity."""
    approved = ApprovalQueue(entity).approve_all()
    if approved:
        return f"Approved {len(approved)} execution(s) for {entity}."
    return f"No pending executions for {entity}."


def revert_exec(entity: str, exec_id: str) -> dict:
    """Revert scratch directory to state before a specific execution."""
    return SnapshotManager(entity).revert_to(exec_id)


def list_snapshots(entity: str) -> list[dict]:
    """List available snapshots for an entity."""
    return SnapshotManager(entity).list_snapshots()


def entity_status(entity: str) -> str:
    """Full status report for an entity's code execution."""
    perms = EntityPermissions(entity)
    exec_log = ExecutionLog(entity)
    queue = ApprovalQueue(entity)
    snaps = SnapshotManager(entity)

    lines = [
        f"=== Code Execution Status: {entity} ===",
        f"Mode: {perms.mode}",
        f"Allowed write paths: {perms.allowed_write_paths or ['(scratch only)']}",
        f"",
    ]

    pending = queue.get_pending()
    if pending:
        lines.append(f"!! {len(pending)} pending approval(s)")
        for p in pending[:3]:
            lines.append(f"  - {p['exec_id']}: {p.get('description', '?')[:50]}")
    else:
        lines.append("No pending approvals.")

    lines.append("")
    recent = exec_log.get_recent(5)
    if recent:
        lines.append("Recent executions:")
        for e in recent:
            ts = e.get("timestamp", "?")[:19]
            status = "OK" if e.get("success") else "FAIL"
            lines.append(f"  {status} [{ts}] {e.get('description', '?')[:40]}")
    else:
        lines.append("No executions yet.")

    snap_list = snaps.list_snapshots()
    lines.append(f"\nSnapshots available: {len(snap_list)}")

    return "\n".join(lines)
