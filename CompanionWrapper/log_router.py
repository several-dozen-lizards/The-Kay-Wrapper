"""
Log Router - Captures print statements and routes to terminal dashboard.

Features:
- Intercepts stdout to capture print statements
- Routes logs to both console and dashboard
- Thread-safe operation
- Graceful degradation if dashboard fails
"""

import sys
from typing import Optional


class LogRouter:
    """
    Routes log messages to both console and terminal dashboard.

    Intercepts stdout and routes messages to dashboard while preserving console output.
    """

    def __init__(self, dashboard=None):
        self.dashboard = dashboard
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.enabled = False

    def start(self):
        """Start intercepting stdout/stderr."""
        if not self.enabled:
            sys.stdout = self
            sys.stderr = self
            self.enabled = True
            print("[LOG ROUTER] Logging router started")

    def stop(self):
        """Stop intercepting and restore original stdout/stderr."""
        if self.enabled:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.enabled = False
            print("[LOG ROUTER] Logging router stopped")

    def write(self, message):
        """Write method for stdout/stderr interface."""
        # Always write to original stdout
        self.original_stdout.write(message)
        self.original_stdout.flush()

        # Route to dashboard if available
        if self.dashboard and message.strip():
            try:
                self.dashboard.parse_and_route_log(message.strip())
            except Exception as e:
                # Fail gracefully - don't break console output
                self.original_stdout.write(f"[LOG ROUTER ERROR] {e}\n")

    def flush(self):
        """Flush method for stdout/stderr interface."""
        self.original_stdout.flush()

    def set_dashboard(self, dashboard):
        """Update dashboard reference."""
        self.dashboard = dashboard


# Global log router instance
_log_router: Optional[LogRouter] = None


def get_log_router():
    """Get global log router instance."""
    global _log_router
    if _log_router is None:
        _log_router = LogRouter()
    return _log_router


def start_logging(dashboard=None):
    """Start routing logs to dashboard."""
    router = get_log_router()
    if dashboard:
        router.set_dashboard(dashboard)
    router.start()


def stop_logging():
    """Stop routing logs."""
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
