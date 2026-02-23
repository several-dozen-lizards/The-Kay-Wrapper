"""
INTEGRATION EXAMPLE
Shows exactly how to add Session Browser to your existing reed_ui.py

Copy the marked sections into your reed_ui.py file
"""

import tkinter as tk
from tkinter import messagebox
import asyncio

# ========================================
# ADD THIS IMPORT at top of reed_ui.py
# ========================================
from session_browser import add_session_browser_to_kay_ui


class KayApp(tk.Tk):
    """Example showing integration points"""

    def __init__(self):
        super().__init__()

        self.title("Kay Zero")
        self.geometry("1000x700")
        self.configure(bg="#2b2b2b")

        # ========================================
        # YOUR EXISTING INITIALIZATION
        # ========================================
        # (Keep all your existing code here)

        # Example: Your LLM client
        from integrations.llm_integration import LLMClient  # Your import
        self.llm_client = LLMClient()

        # Example: Your memory engine
        from engines.memory_engine import MemoryEngine  # Your import
        self.memory_engine = MemoryEngine()

        # Example: Your session tracking
        self.current_session_id = None
        self.session_start_time = None
        self.conversation_history = []

        # ========================================
        # CREATE MENUBAR (if you don't have one)
        # ========================================
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # Your existing menus...
        # file_menu = tk.Menu(self.menubar, tearoff=0)
        # self.menubar.add_cascade(label="File", menu=file_menu)
        # etc...

        # ========================================
        # CREATE TOOLBAR (if you don't have one)
        # ========================================
        self.toolbar = tk.Frame(self, bg="#2b2b2b", height=50)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.toolbar.pack_propagate(False)

        # Your existing toolbar buttons...

        # ========================================
        # ADD SESSION BROWSER - OPTION 1 (EASIEST)
        # Automatically adds to menu + button
        # ========================================
        self.session_browser = add_session_browser_to_kay_ui(
            self,
            llm_client=self.llm_client,
            memory_engine=self.memory_engine,
            session_dir="saved_sessions",
            add_to_menu=True,          # Adds "Sessions" menu
            add_button_to=self.toolbar  # Adds button to toolbar
        )

        # ========================================
        # OR OPTION 2 (MORE CONTROL)
        # Custom integration
        # ========================================
        # from session_browser import SessionBrowserIntegration
        #
        # self.session_browser = SessionBrowserIntegration(
        #     self,
        #     llm_client=self.llm_client,
        #     memory_engine=self.memory_engine,
        #     session_dir="saved_sessions",
        #     current_session_callback=self.get_current_session_id,
        #     resume_session_callback=self.resume_session
        # )
        #
        # # Add to menu manually
        # self.session_browser.add_to_menu(self.menubar)
        #
        # # OR add button manually
        # button = self.session_browser.add_browser_button(
        #     self.toolbar,
        #     text="📚 Sessions"
        # )
        # button.pack(side=tk.LEFT, padx=5)

        # Rest of your UI initialization...

    # ========================================
    # MODIFY YOUR SAVE SESSION METHOD
    # Replace direct JSON save with this
    # ========================================
    async def save_session(self):
        """Save current session with metadata"""

        if not self.current_session_id:
            return

        # Build session data (your existing code)
        session_data = {
            "session_id": self.current_session_id,
            "start_time": self.session_start_time,
            "conversation": self.conversation_history,
            "entity_graph": self.entity_graph.to_dict() if hasattr(self, 'entity_graph') else {},
            "emotional_state": self.emotional_state if hasattr(self, 'emotional_state') else {}
        }

        # ========================================
        # OLD WAY (Replace this):
        # ========================================
        # import json
        # with open(f"saved_sessions/{self.current_session_id}.json", 'w') as f:
        #     json.dump(session_data, f, indent=2)

        # ========================================
        # NEW WAY (Use this instead):
        # ========================================
        await self.session_browser.save_session_with_metadata(
            session_data,
            generate_metadata=True  # Auto-generates title, summary, topics, etc.
        )

        print(f"Session {self.current_session_id} saved with metadata")

    # ========================================
    # ADD THIS METHOD (if you don't have it)
    # Enables Resume functionality
    # ========================================
    def resume_session(self, session_id: str):
        """Resume a previous session"""

        # Load session data
        session_data = self.session_browser.session_manager.load_session(session_id)

        if not session_data:
            messagebox.showerror("Error", f"Failed to load session {session_id}")
            return

        # Close current session if any
        if self.current_session_id:
            asyncio.create_task(self.save_session())

        # Restore state
        self.current_session_id = session_id
        self.session_start_time = session_data.get("start_time", "")
        self.conversation_history = session_data.get("conversation", [])

        # Restore entity graph (if you have one)
        if hasattr(self, 'entity_graph') and "entity_graph" in session_data:
            self.entity_graph.load_from_dict(session_data["entity_graph"])

        # Restore emotional state (if you have it)
        if "emotional_state" in session_data:
            self.emotional_state = session_data["emotional_state"]

        # Update browser to show this as current session
        self.session_browser.update_current_session(session_id)

        # Refresh your UI to show conversation
        self.refresh_chat_display()

        messagebox.showinfo(
            "Session Resumed",
            f"Resumed session from {session_data.get('start_time', 'unknown')}"
        )

    # ========================================
    # ADD THIS METHOD (optional helper)
    # Returns current session ID
    # ========================================
    def get_current_session_id(self) -> str:
        """Get current session ID"""
        return self.current_session_id

    # ========================================
    # OPTIONAL: Update session tracking
    # Call this when session changes
    # ========================================
    def start_new_session(self):
        """Start a new session"""

        import time

        # Your existing session start logic
        self.current_session_id = str(int(time.time()))
        self.session_start_time = datetime.now().isoformat()
        self.conversation_history = []

        # Notify browser of new session
        if hasattr(self, 'session_browser'):
            self.session_browser.update_current_session(self.current_session_id)


# ========================================
# THAT'S IT! Session Browser is integrated
# ========================================

# Now you have:
# 1. "Sessions" menu with "Browse Sessions..." option
# 2. "📚 Sessions" button in toolbar (if add_button_to was used)
# 3. Auto-generated metadata when saving sessions
# 4. Resume session functionality
# 5. Load sessions for Reed to review

# To open browser programmatically:
# self.session_browser.open_browser()

# To generate metadata for current session:
# await self.session_browser._generate_current_metadata()
