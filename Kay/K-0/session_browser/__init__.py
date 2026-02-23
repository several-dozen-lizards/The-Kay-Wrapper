"""
Session Browser for Kay Zero
Complete session management, browsing, and review system
"""

from .session_manager import SessionManager
from .session_metadata import SessionMetadataGenerator, SessionMetadata
from .session_loader import SessionLoader
from .session_browser_ui import SessionBrowserUI
from .session_viewer import SessionViewerWindow
from .kay_integration import SessionBrowserIntegration, add_session_browser_to_kay_ui

__version__ = "1.0.0"

__all__ = [
    # Core components
    "SessionManager",
    "SessionMetadataGenerator",
    "SessionMetadata",
    "SessionLoader",

    # UI components
    "SessionBrowserUI",
    "SessionViewerWindow",

    # Integration
    "SessionBrowserIntegration",
    "add_session_browser_to_kay_ui",
]
