# code_executor.py
"""
Sandboxed code execution for Nexus entities.

Allows Kay and Reed to write and execute Python (and optionally other languages)
through their wrapper infrastructure. Execution happens in a sandboxed subprocess
with timeout, size limits, and directory restrictions.

Used by:
  - nexus_reed.py (via Claude tool_use)
  - nexus_kay.py (via <exec> tag extraction OR tool_use)
  - wrapper_bridge.py (standalone mode, future)

Design: Entities write code → wrapper executes in subprocess → result fed back.
This is NOT independence (Re maintains infrastructure), but shifts entities from
"describe what I want" to "write something and watch it run."
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from code_safety import (
    EntityPermissions, ExecutionLog, SnapshotManager, ApprovalQueue,
    build_jail_preamble,
)

log = logging.getLogger("nexus.code_executor")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Where entity scratch files live
SCRATCH_ROOT = Path("D:/Wrappers/nexus/scratch")

# Execution limits
DEFAULT_TIMEOUT_S = 30          # Max execution time
MAX_OUTPUT_CHARS = 8000         # Truncate stdout/stderr beyond this
MAX_CODE_CHARS = 50000          # Reject code blocks larger than this
ALLOWED_LANGUAGES = {"python"}  # Expandable later (node, bash, etc.)

# Safety: blocked imports/operations (basic guardrails, not adversarial-proof)
# These are guardrails for accidental damage, not security boundaries.
# The entities are trusted — this just prevents oops-I-deleted-the-wrapper moments.
BLOCKED_PATTERNS = [
    "shutil.rmtree",
    "os.remove(",
    "os.unlink(",
    "os.rmdir(",
    "subprocess.call",     # No shell-out from sandbox
    "subprocess.run",
    "subprocess.Popen",
    "exec(",               # No meta-exec inside exec
    "eval(",
    "__import__('os').system",
]


# ---------------------------------------------------------------------------
# Scratch directory management
# ---------------------------------------------------------------------------

def ensure_scratch_dir(entity: str) -> Path:
    """Create and return scratch directory for an entity."""
    entity_dir = SCRATCH_ROOT / entity.lower()
    entity_dir.mkdir(parents=True, exist_ok=True)
    return entity_dir


def list_scratch_files(entity: str) -> list[dict]:
    """List files in entity's scratch directory."""
    entity_dir = SCRATCH_ROOT / entity.lower()
    if not entity_dir.exists():
        return []
    files = []
    for f in sorted(entity_dir.iterdir()):
        if f.is_file():
            stat = f.stat()
            files.append({
                "name": f.name,
                "size": stat.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            })
    return files


# ---------------------------------------------------------------------------
# Code validation
# ---------------------------------------------------------------------------

def validate_code(code: str, language: str = "python") -> Optional[str]:
    """
    Check code for basic safety issues.
    Returns error string if blocked, None if ok.
    """
    if language not in ALLOWED_LANGUAGES:
        return f"Language '{language}' not supported. Allowed: {', '.join(ALLOWED_LANGUAGES)}"
    
    if len(code) > MAX_CODE_CHARS:
        return f"Code too long ({len(code)} chars, max {MAX_CODE_CHARS})"
    
    if not code.strip():
        return "Empty code block"
    
    # Check for accidentally destructive patterns
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return f"Blocked pattern detected: '{pattern}'. If you need this, ask Re to run it manually."
    
    return None


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

async def execute_code(
    code: str,
    entity: str,
    language: str = "python",
    timeout: int = DEFAULT_TIMEOUT_S,
    description: str = "",
    force: bool = False,
) -> dict:
    """
    Execute code in a sandboxed subprocess with full safety layers.

    Safety layers:
      1. Code validation (blocked patterns, size limits)
      2. Permission check (supervised → queue for approval, unless force=True)
      3. File write jail (injected preamble restricts writes to allowed paths)
      4. Pre-execution snapshot (scratch dir backed up for revert)
      5. Execution logging (every run recorded in .exec_log.jsonl)

    Args:
        code: The code to execute
        entity: Entity name (for scratch dir, permissions, logging)
        language: Programming language (currently: python)
        timeout: Max execution time in seconds
        description: Optional description (for logging)
        force: Skip approval queue even in supervised mode (for Re-approved runs)

    Returns:
        dict with: success, stdout, stderr, return_code, execution_time,
                   scratch_dir, files_created, exec_id, error (if any)
    """
    # Generate unique execution ID
    exec_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Load entity permissions
    perms = EntityPermissions(entity)
    exec_log = ExecutionLog(entity)

    # Validate code
    error = validate_code(code, language)
    if error:
        log.warning(f"[EXEC] {entity} code rejected: {error}")
        exec_log.record({
            "exec_id": exec_id, "action": "rejected",
            "description": description, "error": error,
        })
        return {"success": False, "error": error, "exec_id": exec_id}

    # Check entity-specific blocked patterns
    for pattern in perms.config.get("blocked_patterns", []):
        if pattern in code:
            msg = f"Entity-blocked pattern: '{pattern}'"
            exec_log.record({
                "exec_id": exec_id, "action": "rejected",
                "description": description, "error": msg,
            })
            return {"success": False, "error": msg, "exec_id": exec_id}

    # Supervised mode → queue for approval (unless forced)
    if perms.mode == "supervised" and not force:
        queue = ApprovalQueue(entity)
        entry = queue.enqueue(exec_id, code, language, description)
        exec_log.record({
            "exec_id": exec_id, "action": "queued",
            "description": description, "code_length": len(code),
        })
        return {
            "success": False,
            "queued": True,
            "exec_id": exec_id,
            "message": (
                f"Code queued for Re's approval (ID: {exec_id}). "
                f"Mode is 'supervised'. Ask Re to review and approve."
            ),
        }

    # Set up scratch directory
    scratch_dir = ensure_scratch_dir(entity)

    # Take pre-execution snapshot
    snapshots = SnapshotManager(entity)
    snapshots.take_snapshot(exec_id)
    snapshots.cleanup_old(keep=30)

    # Build jailed code (preamble + user code)
    jail_preamble = build_jail_preamble(entity, perms)
    jailed_code = jail_preamble + code

    # Write code to temp file
    code_filename = f"exec_{exec_id}.py"
    code_path = scratch_dir / code_filename

    desc = f" ({description})" if description else ""
    log.info(f"[EXEC] {entity} executing {language} code{desc} — {len(code)} chars, timeout={timeout}s, id={exec_id}")

    try:
        code_path.write_text(jailed_code, encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"Failed to write code file: {e}", "exec_id": exec_id}

    # Snapshot files before execution (to detect what was created)
    files_before = set(
        f.name for f in scratch_dir.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )

    # Execute in subprocess
    start_time = time.time()
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [sys.executable, str(code_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(scratch_dir),
                env={
                    **os.environ,
                    "ENTITY_NAME": entity,
                    "SCRATCH_DIR": str(scratch_dir),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
        )
        execution_time = round(time.time() - start_time, 3)

        # Truncate output
        stdout = result.stdout
        stderr = result.stderr
        if len(stdout) > MAX_OUTPUT_CHARS:
            stdout = stdout[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(result.stdout)} total chars]"
        if len(stderr) > MAX_OUTPUT_CHARS:
            stderr = stderr[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {len(result.stderr)} total chars]"

        # Filter jail preamble errors from stderr (don't confuse entity)
        if "SAFETY JAIL" in stderr:
            stderr_lines = stderr.split("\n")
            stderr = "\n".join(l for l in stderr_lines if "SAFETY JAIL" not in l)

        # Detect new files
        files_after = set(
            f.name for f in scratch_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")
        )
        files_created = sorted(files_after - files_before - {code_filename})

        success = result.returncode == 0

        log.info(
            f"[EXEC] {entity} code {'succeeded' if success else 'failed'} "
            f"in {execution_time}s (return={result.returncode}, id={exec_id})"
        )

        # Log execution
        exec_log.record({
            "exec_id": exec_id,
            "action": "executed",
            "success": success,
            "description": description,
            "code_length": len(code),
            "execution_time": execution_time,
            "return_code": result.returncode,
            "files_created": files_created,
            "stdout_preview": stdout[:200],
            "stderr_preview": stderr[:200] if stderr.strip() else "",
        })

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": result.returncode,
            "execution_time": execution_time,
            "scratch_dir": str(scratch_dir),
            "files_created": files_created,
            "code_file": code_filename,
            "exec_id": exec_id,
        }

    except subprocess.TimeoutExpired:
        execution_time = round(time.time() - start_time, 3)
        log.warning(f"[EXEC] {entity} code timed out after {timeout}s")
        exec_log.record({
            "exec_id": exec_id, "action": "timeout",
            "description": description, "execution_time": execution_time,
        })
        return {
            "success": False,
            "error": f"Execution timed out after {timeout}s",
            "execution_time": execution_time,
            "scratch_dir": str(scratch_dir),
            "code_file": code_filename,
            "exec_id": exec_id,
        }
    except Exception as e:
        execution_time = round(time.time() - start_time, 3)
        log.error(f"[EXEC] {entity} code execution error: {e}")
        exec_log.record({
            "exec_id": exec_id, "action": "error",
            "description": description, "error": str(e),
        })
        return {
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
            "scratch_dir": str(scratch_dir),
            "exec_id": exec_id,
        }


async def execute_approved(entity: str, exec_id: str) -> dict:
    """
    Execute a previously approved queued item.
    Called after Re approves via approve_exec() or approve-all.
    Handles both pending (auto-approves) and already-approved items.
    """
    queue = ApprovalQueue(entity)

    # Try to approve if still pending
    entry = queue.approve(exec_id)
    if not entry:
        # Maybe already approved — search for it
        all_entries = queue._load_queue()
        for e in all_entries:
            if e["exec_id"] == exec_id and e["status"] == "approved":
                entry = e
                break
    if not entry:
        return {"success": False, "error": f"No entry with id '{exec_id}' (pending or approved)"}

    return await execute_code(
        code=entry["code"],
        entity=entity,
        language=entry.get("language", "python"),
        description=entry.get("description", ""),
        force=True,  # Already approved, skip queue
    )


# ---------------------------------------------------------------------------
# Tag extraction (for Kay's <exec> tag pattern)
# ---------------------------------------------------------------------------

import re

EXEC_TAG_RE = re.compile(r"<exec(?:\s+lang=[\"'](\w+)[\"'])?\s*>(.*?)</exec>", re.DOTALL)


def extract_exec_commands(text: str) -> tuple[list[dict], str]:
    """
    Extract <exec> code blocks from entity response text.
    Mirrors canvas_manager.extract_paint_commands pattern.
    
    Supports:
        <exec>python code here</exec>
        <exec lang="python">code here</exec>
    
    Returns:
        (commands, clean_text) where commands is list of
        {"code": str, "language": str} dicts and clean_text
        has <exec> blocks removed.
    """
    commands = []
    clean = text
    
    for match in EXEC_TAG_RE.finditer(text):
        language = match.group(1) or "python"
        code = match.group(2).strip()
        if code:
            commands.append({"code": code, "language": language})
    
    clean = EXEC_TAG_RE.sub("", text).strip()
    return commands, clean


# ---------------------------------------------------------------------------
# Claude tool_use definition (for Reed and future Kay upgrade)
# ---------------------------------------------------------------------------

EXEC_TOOL_DEFINITION = {
    "name": "exec",
    "description": (
        "Execute Python code in your sandbox. Use this to run experiments, "
        "analyze data, process files, test ideas, or build things. "
        "Your code runs in your personal scratch directory where you can "
        "create and read files. Output (stdout/stderr) is returned to you. "
        "Available libraries: standard library, plus anything installed "
        "in the wrapper's Python environment (numpy, etc). "
        "You CANNOT: delete files outside scratch, shell out to subprocesses, "
        "or access the network. If you need those, ask Re."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute.",
            },
            "description": {
                "type": "string",
                "description": "Brief description of what this code does (for logging).",
            },
        },
        "required": ["code"],
    },
}

SCRATCH_TOOL_DEFINITION = {
    "name": "list_scratch",
    "description": (
        "List files in your personal scratch directory. "
        "See what you've created, check file sizes and dates."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
    },
}

READ_SCRATCH_TOOL_DEFINITION = {
    "name": "read_scratch",
    "description": (
        "Read a file from your scratch directory. "
        "Returns the file contents as text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Name of the file in your scratch directory to read.",
            },
        },
        "required": ["filename"],
    },
}

# Convenience: all code-related tools as a list
CODE_TOOLS = [EXEC_TOOL_DEFINITION, SCRATCH_TOOL_DEFINITION, READ_SCRATCH_TOOL_DEFINITION]


# ---------------------------------------------------------------------------
# Read scratch file helper
# ---------------------------------------------------------------------------

def read_scratch_file(entity: str, filename: str, max_chars: int = 10000) -> dict:
    """Read a file from entity's scratch directory."""
    scratch_dir = SCRATCH_ROOT / entity.lower()
    filepath = scratch_dir / filename
    
    # Security: prevent path traversal
    try:
        filepath = filepath.resolve()
        if not str(filepath).startswith(str(scratch_dir.resolve())):
            return {"error": "Path traversal not allowed"}
    except Exception:
        return {"error": "Invalid filename"}
    
    if not filepath.exists():
        return {"error": f"File not found: {filename}"}
    
    try:
        content = filepath.read_text(encoding="utf-8")
        truncated = False
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... [truncated, {len(content)} total chars]"
            truncated = True
        return {
            "success": True,
            "filename": filename,
            "content": content,
            "size": filepath.stat().st_size,
            "truncated": truncated,
        }
    except UnicodeDecodeError:
        return {"error": f"File is binary, can't read as text: {filename}"}
    except Exception as e:
        return {"error": str(e)}
