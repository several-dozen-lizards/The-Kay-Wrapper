"""
Log Router - Captures print statements, routes to terminal dashboard, persists to disk.

Features:
- Intercepts stdout to capture print statements
- Routes logs to both console and dashboard
- Persists ALL terminal output to a .log file on disk
- Thread-safe operation
- Graceful degradation if dashboard or file fails
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Default log directory (Reed session logs)
DEFAULT_LOG_DIR = Path(__file__).parent / "session_logs"


class LogRouter:
    """
    Routes log messages to console, dashboard, AND disk.

    Intercepts stdout and routes messages to dashboard while preserving
    console output. Simultaneously persists everything to a .log file
    so no terminal output is ever lost.
    """

    def __init__(self, dashboard=None):
        self.dashboard = dashboard
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.enabled = False
        self._log_file = None
        self._log_path: Optional[Path] = None
        self._session_id: Optional[str] = None

    def start(self, log_dir: Optional[str] = None, session_id: Optional[str] = None):
        """Start intercepting stdout/stderr and persisting to disk.
        
        Args:
            log_dir: Directory for log files. Defaults to Kay/session_logs/
            session_id: Optional session ID for file naming (e.g. nexus session ID).
                       If not provided, generates one from current timestamp.
        """
        if self.enabled:
            return

        # Generate or use provided session ID
        self._session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Set up log directory
        log_path = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Open log file
        self._log_path = log_path / f"reed_{self._session_id}.log"
        try:
            self._log_file = open(self._log_path, "a", encoding="utf-8")
            # Write header
            self._log_file.write(f"=== Kay Terminal Log: {self._session_id} ===\n")
            self._log_file.write(f"Started: {datetime.now(timezone.utc).isoformat()}\n")
            self._log_file.write("=" * 60 + "\n\n")
            self._log_file.flush()
        except Exception as e:
            self.original_stdout.write(f"[LOG ROUTER] Failed to open log file: {e}\n")
            self._log_file = None

        # Intercept stdout/stderr
        sys.stdout = self
        sys.stderr = self
        self.enabled = True
        print(f"[LOG ROUTER] Logging started → {self._log_path}")

    def stop(self):
        """Stop intercepting and restore original stdout/stderr."""
        if not self.enabled:
            return
        
        # Write footer before closing
        if self._log_file:
            try:
                self._log_file.write(f"\n{'=' * 60}\n")
                self._log_file.write(f"Session ended: {datetime.now(timezone.utc).isoformat()}\n")
                self._log_file.flush()
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None

        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.enabled = False
        print(f"[LOG ROUTER] Logging stopped. Log saved to {self._log_path}")

    def write(self, message):
        """Write method for stdout/stderr interface."""
        # Always write to original stdout
        self.original_stdout.write(message)
        self.original_stdout.flush()

        # Persist to disk
        if self._log_file and message.strip():
            try:
                self._log_file.write(message)
                # Flush periodically (every line that ends with newline)
                if message.endswith("\n"):
                    self._log_file.flush()
            except Exception:
                pass  # Don't break console output if file write fails

        # Route to dashboard if available
        if self.dashboard and message.strip():
            try:
                self.dashboard.parse_and_route_log(message.strip())
            except Exception as e:
                self.original_stdout.write(f"[LOG ROUTER ERROR] {e}\n")

    def flush(self):
        """Flush method for stdout/stderr interface."""
        self.original_stdout.flush()
        if self._log_file:
            try:
                self._log_file.flush()
            except Exception:
                pass

    def set_dashboard(self, dashboard):
        """Update dashboard reference."""
        self.dashboard = dashboard

    def set_session_id(self, session_id: str):
        """Update session ID (e.g. when nexus session ID becomes available).
        
        If logging is already active, renames the log file to match.
        """
        old_id = self._session_id
        self._session_id = session_id
        
        if self._log_file and self._log_path and old_id != session_id:
            # Close current file, rename, reopen
            try:
                self._log_file.flush()
                self._log_file.close()
                new_path = self._log_path.parent / f"kay_{session_id}.log"
                self._log_path.rename(new_path)
                self._log_path = new_path
                self._log_file = open(self._log_path, "a", encoding="utf-8")
                self._log_file.write(f"\n[LOG ROUTER] Session ID updated: {old_id} → {session_id}\n")
                self._log_file.flush()
            except Exception as e:
                self.original_stdout.write(f"[LOG ROUTER] Failed to rename log: {e}\n")
                # Try to reopen old file
                try:
                    self._log_file = open(self._log_path, "a", encoding="utf-8")
                except Exception:
                    self._log_file = None

    @property
    def log_path(self) -> Optional[str]:
        """Return the current log file path."""
        return str(self._log_path) if self._log_path else None

    @property
    def session_id(self) -> Optional[str]:
        """Return the current session ID."""
        return self._session_id


# ---------------------------------------------------------------------------
# Global singleton + convenience functions
# ---------------------------------------------------------------------------

_log_router: Optional[LogRouter] = None


def get_log_router():
    """Get global log router instance."""
    global _log_router
    if _log_router is None:
        _log_router = LogRouter()
    return _log_router


def start_logging(dashboard=None, log_dir=None, session_id=None):
    """Start routing logs to dashboard AND persisting to disk.
    
    Args:
        dashboard: Optional terminal dashboard for UI routing
        log_dir: Directory for log files (default: Kay/session_logs/)
        session_id: Optional session ID for pairing with nexus logs
    """
    router = get_log_router()
    if dashboard:
        router.set_dashboard(dashboard)
    router.start(log_dir=log_dir, session_id=session_id)


def stop_logging():
    """Stop routing logs and close log file."""
    router = get_log_router()
    router.stop()


def log_to_dashboard(message: str, section: str = "System Status", level: str = "INFO"):
    """
    Direct log to dashboard (bypasses stdout).

    Args:
        message: Log message
        section: Dashboard section to route to
        level: Log level (INFO, WARNING, ERROR, DEBUG, etc.)
    """
    router = get_log_router()
    if router.dashboard:
        try:
            router.dashboard.log(message, section, level)
        except Exception as e:
            print(f"[LOG ROUTER ERROR] Failed to log to dashboard: {e}")
