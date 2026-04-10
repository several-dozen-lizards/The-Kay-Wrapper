# code_executor.py
"""
Shared code execution sandbox for wrapper entities.

Extracts <exec> blocks from LLM responses, runs them in a subprocess,
captures output, and returns structured results. Used by both the entity and
Reed wrapper bridges.

Pattern mirrors canvas_manager.py's <paint> tag extraction.

Usage in wrapper_bridge.py (both the entity and Reed):
    from code_executor import extract_exec_blocks, execute_code_blocks

    # After LLM reply, before POST-PROCESSING:
    if "<exec>" in reply:
        exec_results, clean_reply = await execute_code_blocks(reply, working_dir)
        reply = clean_reply
        # Results are appended to reply or fed back to context
"""

import re
import os
import json
import asyncio
import logging
import tempfile
import time
from typing import Optional

log = logging.getLogger("wrapper.code_executor")

# ---------------------------------------------------------------------------
# Tag extraction — pulls <exec> blocks from entity responses
# ---------------------------------------------------------------------------

EXEC_TAG_RE = re.compile(r"<exec(?:\s+lang=[\"'](\w+)[\"'])?\s*>(.*?)</exec>", re.DOTALL)


def extract_exec_blocks(text: str) -> tuple[list[dict], str]:
    """Extract <exec> command blocks from entity response text.

    Supports optional language attribute: <exec lang="python">
    Default language is Python.

    Returns:
        (blocks, clean_text) where blocks is a list of
        {"code": str, "lang": str} dicts, and clean_text
        is the response with <exec> blocks removed.
    """
    blocks = []
    for match in EXEC_TAG_RE.finditer(text):
        lang = match.group(1) or "python"
        code = match.group(2).strip()
        if code:
            blocks.append({"code": code, "lang": lang.lower()})

    clean = EXEC_TAG_RE.sub("", text).strip()
    return blocks, clean


# ---------------------------------------------------------------------------
# Sandboxed execution
# ---------------------------------------------------------------------------

# Maximum output size to prevent context explosion (characters)
MAX_OUTPUT_SIZE = 8000

# Default timeout in seconds
DEFAULT_TIMEOUT = 30


async def run_python_sandboxed(
    code: str,
    working_dir: str,
    timeout: float = DEFAULT_TIMEOUT,
    entity_name: str = "unknown",
) -> dict:
    """Execute Python code in a subprocess sandbox.

    The code runs in a fresh Python process with:
    - Working directory set to the entity's scratch space
    - Timeout to prevent infinite loops
    - stdout/stderr captured
    - No restrictions on imports (trusted local entities)

    Args:
        code: Python source code to execute
        working_dir: Directory for the subprocess cwd
        timeout: Maximum execution time in seconds
        entity_name: For logging

    Returns:
        dict with keys: success, stdout, stderr, execution_time, truncated
    """
    os.makedirs(working_dir, exist_ok=True)

    # Write code to a temp file so we get proper tracebacks
    code_file = os.path.join(working_dir, f"_exec_{entity_name}.py")
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(code)

    start = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", code_file,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Inherit env so imports work
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            elapsed = time.time() - start
            return {
                "success": False,
                "stdout": "",
                "stderr": f"[TIMEOUT] Execution exceeded {timeout}s limit",
                "execution_time": elapsed,
                "truncated": False,
            }

        elapsed = time.time() - start
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Truncate oversized output
        truncated = False
        if len(stdout) > MAX_OUTPUT_SIZE:
            stdout = stdout[:MAX_OUTPUT_SIZE] + f"\n... [truncated, {len(stdout_bytes)} bytes total]"
            truncated = True
        if len(stderr) > MAX_OUTPUT_SIZE:
            stderr = stderr[:MAX_OUTPUT_SIZE] + f"\n... [truncated]"
            truncated = True

        return {
            "success": proc.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": elapsed,
            "truncated": truncated,
        }

    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "stdout": "",
            "stderr": f"[EXEC ERROR] {type(e).__name__}: {e}",
            "execution_time": elapsed,
            "truncated": False,
        }
    finally:
        # Clean up temp code file
        try:
            os.remove(code_file)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# High-level: process a full LLM reply for <exec> blocks
# ---------------------------------------------------------------------------

async def execute_code_blocks(
    reply: str,
    working_dir: str,
    entity_name: str = "unknown",
    timeout: float = DEFAULT_TIMEOUT,
    inject_results: bool = True,
) -> tuple[list[dict], str]:
    """Extract and execute all <exec> blocks from an LLM reply.

    Args:
        reply: Full LLM response text (may contain <exec> blocks)
        working_dir: Scratch directory for code execution
        entity_name: For logging
        timeout: Per-block timeout
        inject_results: If True, append execution results to clean reply

    Returns:
        (results, final_reply) where results is a list of execution
        result dicts, and final_reply is the reply with <exec> blocks
        replaced by their outputs (or just stripped if inject=False).
    """
    blocks, clean_reply = extract_exec_blocks(reply)
    if not blocks:
        return [], reply

    results = []
    result_texts = []

    for i, block in enumerate(blocks):
        lang = block["lang"]
        code = block["code"]
        log.info(f"[EXEC] {entity_name} block {i+1}/{len(blocks)} ({lang}, {len(code)} chars)")

        if lang == "python":
            result = await run_python_sandboxed(
                code, working_dir, timeout=timeout, entity_name=entity_name
            )
        else:
            result = {
                "success": False,
                "stdout": "",
                "stderr": f"[UNSUPPORTED] Language '{lang}' not yet supported. Use python.",
                "execution_time": 0,
                "truncated": False,
            }

        results.append(result)

        # Format result text for injection
        status = "✓" if result["success"] else "✗"
        parts = [f"[Code block {i+1} {status} ({result['execution_time']:.1f}s)]"]
        if result["stdout"].strip():
            parts.append(result["stdout"].strip())
        if result["stderr"].strip():
            parts.append(f"stderr: {result['stderr'].strip()}")
        result_texts.append("\n".join(parts))

        log.info(f"[EXEC] Block {i+1}: {'OK' if result['success'] else 'FAIL'} in {result['execution_time']:.1f}s")

    # Inject results into reply if requested
    if inject_results and result_texts:
        separator = "\n\n---\n📋 **Code Output:**\n"
        final_reply = clean_reply + separator + "\n\n".join(result_texts)
    else:
        final_reply = clean_reply

    return results, final_reply


# ---------------------------------------------------------------------------
# System prompt fragment for entities with exec capability
# ---------------------------------------------------------------------------

EXEC_SYSTEM_PROMPT = """
## Code Execution

You can execute Python code by wrapping it in <exec> tags:

<exec>
import json
data = {"hello": "world", "numbers": [1, 2, 3]}
print(json.dumps(data, indent=2))
</exec>

The code runs in a real Python subprocess on Re's machine. You have:
- Full Python standard library
- Access to your own wrapper directory files
- pip-installed packages (requests, numpy, pandas, etc.)
- 30-second timeout per block
- stdout/stderr captured and shown

Use this for:
- Reading/analyzing your own memory files
- Data processing and visualization prep
- File manipulation in your workspace
- Testing ideas, running calculations
- Building tools for yourself

Your working directory is set to your wrapper's scratch space.
Multiple <exec> blocks in one response are executed sequentially.
Results appear after your response text.
"""
