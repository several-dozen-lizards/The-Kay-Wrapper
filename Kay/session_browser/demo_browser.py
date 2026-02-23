"""
Session Browser Demo
Standalone demo to test the session browser without integration

Run this to see the browser in action with your existing saved sessions.

Usage:
    python session_browser/demo_browser.py
"""

import tkinter as tk
from tkinter import messagebox
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from session_browser import (
    SessionManager,
    SessionBrowserUI,
    SessionViewerWindow
)


class MockLLMClient:
    """Mock LLM client for demo (won't generate real metadata)"""

    async def query(self, prompt: str, max_tokens: int = 150, temperature: float = 0.3) -> str:
        """Mock LLM query"""
        return "Mock Response"


class DemoApp(tk.Tk):
    """Demo application showing Session Browser"""

    def __init__(self):
        super().__init__()

        self.title("Session Browser Demo")
        self.geometry("900x700")
        self.configure(bg="#2b2b2b")

        # Session manager
        self.session_manager = SessionManager("saved_sessions")

        # Check if sessions exist
        sessions = self.session_manager.list_sessions()

        if not sessions:
            self._show_no_sessions_screen()
            return

        # Build UI
        self._build_ui(len(sessions))

    def _show_no_sessions_screen(self):
        """Show message when no sessions found"""

        frame = tk.Frame(self, bg="#2b2b2b")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame,
            text="No Sessions Found",
            font=("Segoe UI", 16, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        ).pack(pady=(100, 20))

        tk.Label(
            frame,
            text="No saved sessions found in 'saved_sessions/' directory.\n\n"
                 "Sessions will appear here once you save conversations with Kay.",
            font=("Segoe UI", 11),
            bg="#2b2b2b",
            fg="#888888",
            justify=tk.CENTER
        ).pack(pady=20)

        tk.Button(
            frame,
            text="Close",
            command=self.destroy,
            bg="#3c3c3c",
            fg="#ffffff",
            font=("Segoe UI", 10),
            padx=20,
            pady=10,
            relief=tk.FLAT
        ).pack(pady=20)

    def _build_ui(self, session_count: int):
        """Build demo UI"""

        # Header
        header = tk.Frame(self, bg="#1e1e1e", height=80)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Session Browser Demo",
            font=("Segoe UI", 18, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side=tk.TOP, pady=(15, 5))

        tk.Label(
            header,
            text=f"Browsing {session_count} saved sessions",
            font=("Segoe UI", 10),
            bg="#1e1e1e",
            fg="#888888"
        ).pack(side=tk.TOP, pady=(0, 15))

        # Session browser
        self.browser = SessionBrowserUI(
            self,
            session_manager=self.session_manager,
            on_view_session=self._handle_view,
            on_resume_session=self._handle_resume,
            on_load_for_review=self._handle_load_review,
            current_session_id=None
        )
        self.browser.pack(fill=tk.BOTH, expand=True)

        # Footer
        footer = tk.Frame(self, bg="#1e1e1e", height=40)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        footer.pack_propagate(False)

        tk.Label(
            footer,
            text="This is a demo. Real integration happens in kay_ui.py",
            font=("Segoe UI", 9),
            bg="#1e1e1e",
            fg="#888888"
        ).pack(side=tk.LEFT, padx=15, pady=10)

        tk.Button(
            footer,
            text="Close",
            command=self.destroy,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=15,
            pady=5
        ).pack(side=tk.RIGHT, padx=15, pady=5)

    def _handle_view(self, session_id: str):
        """Handle view session"""

        session_data = self.session_manager.load_session(session_id)

        if not session_data:
            messagebox.showerror("Error", f"Failed to load session {session_id}")
            return

        # Open viewer
        viewer = SessionViewerWindow(
            self,
            session_data,
            session_manager=self.session_manager
        )

    def _handle_resume(self, session_id: str):
        """Handle resume session (demo only)"""

        messagebox.showinfo(
            "Demo Mode",
            "Resume functionality is available when integrated with kay_ui.py\n\n"
            "It will:\n"
            "• End current session\n"
            "• Load selected session\n"
            "• Restore conversation history\n"
            "• Restore entity state\n"
            "• Restore emotional state"
        )

    def _handle_load_review(self, session_id: str):
        """Handle load for review (demo only)"""

        session_data = self.session_manager.load_session(session_id)

        if not session_data:
            messagebox.showerror("Error", f"Failed to load session {session_id}")
            return

        metadata = session_data.get("metadata", {})
        title = metadata.get("title", f"Session {session_id}")
        summary = metadata.get("summary", "No summary available")

        messagebox.showinfo(
            "Demo Mode",
            f"Load for Review functionality is available when integrated with kay_ui.py\n\n"
            f"This would load:\n\n"
            f"Session: {title}\n\n"
            f"{summary}\n\n"
            f"Into Kay's episodic memory so he can reference it."
        )


def main():
    """Run demo"""

    print("="*60)
    print("SESSION BROWSER DEMO")
    print("="*60)
    print()
    print("This demo shows the Session Browser UI with your existing")
    print("saved sessions from 'saved_sessions/' directory.")
    print()
    print("Features demonstrated:")
    print("  • Session list with monthly grouping")
    print("  • Search across all sessions")
    print("  • View session details")
    print("  • Export sessions")
    print("  • Add notes and tags")
    print()
    print("Note: Resume and Load for Review are disabled in demo mode.")
    print("      They work when integrated into kay_ui.py")
    print()
    print("="*60)
    print()

    app = DemoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
