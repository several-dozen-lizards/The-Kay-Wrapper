"""
Ollama Watchdog — Auto-restart frozen ollama instances.

ollama accumulates resource pressure under sustained concurrent load
(visual sensor + consciousness stream + peripheral model). After hours
of continuous operation, it can freeze — accepting connections but
never responding. This watchdog detects and recovers from that state.

Usage:
    from shared.ollama_watchdog import check_ollama, ensure_ollama

    # Quick check (non-blocking)
    if not check_ollama(timeout=3.0):
        ensure_ollama()  # Kill + restart

    # Or use the periodic watchdog in a background loop
    import asyncio
    asyncio.create_task(ollama_watchdog_loop(interval=120))
"""

import subprocess
import time
import os
import logging
import asyncio

log = logging.getLogger("ollama_watchdog")

OLLAMA_URL = "http://localhost:11434/v1/models"
OLLAMA_EXE = "ollama"  # Assumes ollama is on PATH


def check_ollama(timeout: float = 3.0) -> bool:
    """Check if ollama is responsive. Returns True if healthy."""
    try:
        import urllib.request
        req = urllib.request.Request(OLLAMA_URL)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def kill_ollama() -> int:
    """Kill all ollama processes. Returns number killed."""
    killed = 0
    try:
        # Windows-specific
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "ollama.exe"],
            capture_output=True, text=True, timeout=5
        )
        if "SUCCESS" in result.stdout:
            killed += result.stdout.count("SUCCESS")
        # Also kill the app wrapper
        subprocess.run(
            ["taskkill", "/F", "/IM", "ollama app.exe"],
            capture_output=True, text=True, timeout=5
        )
    except Exception as e:
        log.warning(f"kill_ollama error: {e}")
    return killed


def start_ollama() -> bool:
    """Start ollama serve in background. Returns True if it comes up."""
    try:
        subprocess.Popen(
            [OLLAMA_EXE, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW  # Windows: no console
        )
        # Wait for it to come up
        for _ in range(10):
            time.sleep(1)
            if check_ollama(timeout=2.0):
                return True
        return False
    except Exception as e:
        log.error(f"start_ollama error: {e}")
        return False


def ensure_ollama(timeout: float = 3.0) -> bool:
    """Check ollama health; restart if frozen. Returns True if healthy after."""
    if check_ollama(timeout=timeout):
        return True

    log.warning("[OLLAMA WATCHDOG] ollama unresponsive — restarting...")
    killed = kill_ollama()
    log.info(f"[OLLAMA WATCHDOG] Killed {killed} ollama processes")
    time.sleep(2)

    if start_ollama():
        log.info("[OLLAMA WATCHDOG] ollama restarted successfully")
        return True
    else:
        log.error("[OLLAMA WATCHDOG] Failed to restart ollama!")
        return False


async def ollama_watchdog_loop(interval: float = 120.0):
    """Background async loop that checks ollama health periodically.

    Args:
        interval: Seconds between health checks (default: 2 minutes)
    """
    log.info(f"[OLLAMA WATCHDOG] Started (check every {interval}s)")
    consecutive_failures = 0

    while True:
        await asyncio.sleep(interval)
        try:
            healthy = await asyncio.get_event_loop().run_in_executor(
                None, check_ollama, 3.0
            )
            if healthy:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                log.warning(
                    f"[OLLAMA WATCHDOG] Health check failed "
                    f"({consecutive_failures} consecutive)"
                )
                if consecutive_failures >= 2:
                    # Two consecutive failures = definitely frozen, restart
                    await asyncio.get_event_loop().run_in_executor(
                        None, ensure_ollama
                    )
                    consecutive_failures = 0
        except Exception as e:
            log.error(f"[OLLAMA WATCHDOG] Loop error: {e}")
