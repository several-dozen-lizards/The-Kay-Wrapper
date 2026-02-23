"""
Reed UI Integration Adapter
Helper functions for integrating Session Browser into existing Reed UI
"""

import tkinter as tk
from tkinter import messagebox
import asyncio
from typing import Optional, Callable

from .session_manager import SessionManager
from .session_metadata import SessionMetadataGenerator
from .session_loader import SessionLoader
from .session_browser_ui import SessionBrowserUI
from .session_viewer import SessionViewerWindow


class SessionBrowserIntegration:
    """
    Integration adapter for adding Session Browser to Reed UI

    Usage in reed_ui.py:

        from session_browser import SessionBrowserIntegration

        # In KayApp.__init__():
        self.session_browser_integration = SessionBrowserIntegration(
            self,
            llm_client=self.llm_client,
            memory_engine=self.memory_engine,
            current_session_callback=lambda: self.current_session_id,
            resume_session_callback=self.resume_session
        )

        # Add menu or button:
        self.session_browser_integration.add_browser_button(parent_frame)
        # OR
        self.session_browser_integration.add_to_menu(menubar)

        # When saving sessions, also generate metadata:
        await self.session_browser_integration.save_session_with_metadata(
            session_data,
            conversation_history
        )
    """

    def __init__(
        self,
        kay_app,
        llm_client,
        memory_engine=None,
        session_dir: str = "saved_sessions",
        current_session_callback: Optional[Callable] = None,
        resume_session_callback: Optional[Callable] = None
    ):
        """
        Args:
            kay_app: KayApp instance (or parent window)
            llm_client: LLM client for metadata generation
            memory_engine: Memory engine for loading sessions into memory
            session_dir: Directory where sessions are stored
            current_session_callback: Callback() -> session_id for current session
            resume_session_callback: Callback(session_id) to resume a session
        """

        self.kay_app = kay_app
        self.llm_client = llm_client
        self.memory_engine = memory_engine
        self.current_session_callback = current_session_callback
        self.resume_session_callback = resume_session_callback

        # Initialize components
        self.session_manager = SessionManager(session_dir)
        self.metadata_generator = SessionMetadataGenerator(llm_client)
        self.session_loader = SessionLoader(memory_engine)

        # Browser window reference
        self.browser_window = None

    def add_browser_button(
        self,
        parent_frame: tk.Frame,
        text: str = "📚 Sessions",
        **button_kwargs
    ) -> tk.Button:
        """
        Add a button to open session browser

        Args:
            parent_frame: Frame to add button to
            text: Button text
            **button_kwargs: Additional button configuration

        Returns:
            Created button widget
        """

        default_kwargs = {
            "bg": "#3c3c3c",
            "fg": "#ffffff",
            "relief": tk.FLAT,
            "padx": 15,
            "pady": 8,
            "font": ("Segoe UI", 10)
        }
        default_kwargs.update(button_kwargs)

        button = tk.Button(
            parent_frame,
            text=text,
            command=self.open_browser,
            **default_kwargs
        )

        return button

    def add_to_menu(self, menubar: tk.Menu):
        """
        Add "Sessions" menu to menubar

        Args:
            menubar: Menubar to add to
        """

        sessions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Sessions", menu=sessions_menu)

        sessions_menu.add_command(
            label="Browse Sessions...",
            command=self.open_browser,
            accelerator="Ctrl+B"
        )

        sessions_menu.add_separator()

        sessions_menu.add_command(
            label="Generate Metadata for Current Session",
            command=lambda: asyncio.create_task(self._generate_current_metadata())
        )

        # TODO: Add keyboard binding
        # self.kay_app.bind("<Control-b>", lambda e: self.open_browser())

    def open_browser(self, as_sidebar: bool = False):
        """
        Open session browser window

        Args:
            as_sidebar: If True, show as sidebar (not yet implemented)
        """

        if self.browser_window and self.browser_window.winfo_exists():
            # Browser already open, bring to front
            self.browser_window.lift()
            self.browser_window.focus()
            return

        # Create new browser window
        self.browser_window = tk.Toplevel(self.kay_app)
        self.browser_window.title("Kay - Session Browser")
        self.browser_window.geometry("800x600")
        self.browser_window.configure(bg="#2b2b2b")

        # Get current session ID
        current_session_id = None
        if self.current_session_callback:
            current_session_id = self.current_session_callback()

        # Create browser UI
        browser = SessionBrowserUI(
            self.browser_window,
            session_manager=self.session_manager,
            on_view_session=self._handle_view_session,
            on_resume_session=self._handle_resume_session,
            on_load_for_review=self._handle_load_for_review,
            current_session_id=current_session_id
        )
        browser.pack(fill=tk.BOTH, expand=True)

        # Cleanup on close
        def on_close():
            self.browser_window.destroy()
            self.browser_window = None

        self.browser_window.protocol("WM_DELETE_WINDOW", on_close)

    def _handle_view_session(self, session_id: str):
        """Handle viewing a session"""

        session_data = self.session_manager.load_session(session_id)
        if not session_data:
            messagebox.showerror("Error", f"Failed to load session {session_id}")
            return

        # Open viewer window
        viewer = SessionViewerWindow(
            self.kay_app,
            session_data,
            session_manager=self.session_manager
        )

    def _handle_resume_session(self, session_id: str):
        """Handle resuming a session"""

        if self.resume_session_callback:
            self.resume_session_callback(session_id)
        else:
            messagebox.showwarning(
                "Not Available",
                "Resume functionality not configured.\n\n"
                "Implement resume_session_callback in KayApp."
            )

    def _handle_load_for_review(self, session_id: str):
        """Handle loading session into memory for review"""

        session_data = self.session_manager.load_session(session_id)
        if not session_data:
            messagebox.showerror("Error", f"Failed to load session {session_id}")
            return

        if not self.memory_engine:
            messagebox.showwarning(
                "Not Available",
                "Memory engine not configured.\n\n"
                "Cannot load session into memory without memory engine."
            )
            return

        # Ask for compression level
        from tkinter import simpledialog

        compression = simpledialog.askstring(
            "Load for Review",
            "Compression level? (high/medium/low)\n\n"
            "- high: Summary only\n"
            "- medium: Summary + key moments (recommended)\n"
            "- low: All turns",
            initialvalue="medium"
        )

        if not compression:
            return

        compression = compression.lower()
        if compression not in ["high", "medium", "low"]:
            compression = "medium"

        try:
            # Get current turn
            current_turn = getattr(self.kay_app, "current_turn", 0)

            # Load session
            count = self.session_loader.integrate_with_memory_engine(
                session_data,
                current_turn,
                compression_level=compression
            )

            # Show confirmation
            session_ref = self.session_loader.get_session_reference_string(session_data)

            messagebox.showinfo(
                "Session Loaded",
                f"Loaded session into memory:\n\n{session_ref}\n\n"
                f"Added {count} memories.\n\n"
                f"Kay can now reference this conversation."
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session:\n\n{e}")

    async def save_session_with_metadata(
        self,
        session_data: dict,
        generate_metadata: bool = True
    ) -> bool:
        """
        Save session with auto-generated metadata

        Call this instead of directly saving session JSON

        Args:
            session_data: Session data dict (must include session_id, conversation)
            generate_metadata: Whether to generate metadata (True = yes, takes a few seconds)

        Returns:
            True if successful
        """

        try:
            # Generate metadata if requested
            if generate_metadata:
                conversation = session_data.get("conversation", [])

                if len(conversation) > 0:
                    metadata = await self.metadata_generator.generate_metadata(
                        conversation,
                        session_data
                    )

                    # Add to session data
                    session_data["metadata"] = self.metadata_generator.to_dict(metadata)

            # Save
            success = self.session_manager.save_session(session_data)

            return success

        except Exception as e:
            print(f"Error saving session with metadata: {e}")
            return False

    async def _generate_current_metadata(self):
        """Generate metadata for current session"""

        if not self.current_session_callback:
            messagebox.showwarning("Not Available", "Current session callback not configured")
            return

        current_session_id = self.current_session_callback()
        if not current_session_id:
            messagebox.showwarning("No Session", "No active session")
            return

        session_data = self.session_manager.load_session(current_session_id)
        if not session_data:
            messagebox.showerror("Error", "Failed to load current session")
            return

        try:
            # Generate
            conversation = session_data.get("conversation", [])
            metadata = await self.metadata_generator.generate_metadata(
                conversation,
                session_data
            )

            # Update session
            session_data["metadata"] = self.metadata_generator.to_dict(metadata)
            self.session_manager.save_session(session_data)

            messagebox.showinfo(
                "Metadata Generated",
                f"Title: {metadata.title}\n\n"
                f"Summary: {metadata.summary}\n\n"
                f"Topics: {', '.join(metadata.key_topics)}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate metadata:\n\n{e}")

    def update_current_session(self, session_id: str):
        """
        Update the current session indicator in browser

        Call this when the current session changes

        Args:
            session_id: New current session ID
        """

        if self.browser_window and self.browser_window.winfo_exists():
            # Find browser widget and update
            for widget in self.browser_window.winfo_children():
                if isinstance(widget, SessionBrowserUI):
                    widget.set_current_session(session_id)
                    break


# Standalone helper function for quick integration
def add_session_browser_to_kay_ui(
    kay_app,
    llm_client,
    memory_engine=None,
    session_dir: str = "saved_sessions",
    add_to_menu: bool = True,
    add_button_to: Optional[tk.Frame] = None
):
    """
    Quick integration helper

    Args:
        kay_app: KayApp instance
        llm_client: LLM client
        memory_engine: Memory engine
        session_dir: Session directory
        add_to_menu: Whether to add Sessions menu
        add_button_to: Frame to add browser button to (if any)

    Returns:
        SessionBrowserIntegration instance for further customization
    """

    integration = SessionBrowserIntegration(
        kay_app,
        llm_client,
        memory_engine,
        session_dir,
        current_session_callback=lambda: getattr(kay_app, "current_session_id", None),
        resume_session_callback=getattr(kay_app, "resume_session", None)
    )

    if add_to_menu and hasattr(kay_app, "menubar"):
        integration.add_to_menu(kay_app.menubar)

    if add_button_to:
        integration.add_browser_button(add_button_to).pack(side=tk.LEFT, padx=5)

    return integration
