"""
Session Viewer Window
Read-only window for viewing complete session history
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
from typing import Dict, Any
from datetime import datetime


class SessionViewerWindow(tk.Toplevel):
    """
    Standalone window for viewing session conversation history
    """

    def __init__(self, parent, session_data: Dict[str, Any], session_manager=None):
        """
        Args:
            parent: Parent widget
            session_data: Full session data dict
            session_manager: Optional SessionManager for actions
        """

        super().__init__(parent)

        self.session_data = session_data
        self.session_manager = session_manager

        self._setup_window()
        self._build_ui()
        self._populate_content()

    def _setup_window(self):
        """Configure window properties"""

        session_id = self.session_data.get("session_id", "Unknown")
        metadata = self.session_data.get("metadata", {})
        title = metadata.get("title", f"Session {session_id}")

        self.title(f"Session Viewer - {title}")
        self.geometry("900x700")
        self.configure(bg="#2b2b2b")

        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _build_ui(self):
        """Build UI layout"""

        # Header with metadata
        header_frame = tk.Frame(self, bg="#1e1e1e")
        header_frame.pack(side=tk.TOP, fill=tk.X)

        self._build_header(header_frame)

        # Toolbar
        toolbar_frame = tk.Frame(self, bg="#2b2b2b", height=40)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        toolbar_frame.pack_propagate(False)

        self._build_toolbar(toolbar_frame)

        # Conversation display
        conv_frame = tk.Frame(self, bg="#2b2b2b")
        conv_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.conversation_text = scrolledtext.ScrolledText(
            conv_frame,
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            padx=15,
            pady=15,
            spacing1=5,
            spacing2=3,
            spacing3=5
        )
        self.conversation_text.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for styling
        self.conversation_text.tag_config("user_label", foreground="#00aaff", font=("Consolas", 10, "bold"))
        self.conversation_text.tag_config("kay_label", foreground="#00ff88", font=("Consolas", 10, "bold"))
        self.conversation_text.tag_config("timestamp", foreground="#888888", font=("Consolas", 8))
        self.conversation_text.tag_config("separator", foreground="#444444")

        # Footer
        footer_frame = tk.Frame(self, bg="#1e1e1e", height=30)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)

        close_btn = tk.Button(
            footer_frame,
            text="Close",
            command=self.destroy,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=5
        )
        close_btn.pack(side=tk.RIGHT, padx=10, pady=3)

    def _build_header(self, parent):
        """Build metadata header"""

        metadata = self.session_data.get("metadata", {})
        session_id = self.session_data.get("session_id", "Unknown")

        # Title
        title = metadata.get("title", f"Session {session_id}")
        title_label = tk.Label(
            parent,
            text=title,
            font=("Segoe UI", 16, "bold"),
            bg="#1e1e1e",
            fg="#ffffff",
            anchor="w"
        )
        title_label.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(15, 5))

        # Metadata row
        meta_frame = tk.Frame(parent, bg="#1e1e1e")
        meta_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 15))

        # Date
        start_time = self.session_data.get("start_time", "")
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time)
                date_str = dt.strftime("%B %d, %Y at %I:%M %p")
            except ValueError:
                date_str = start_time
        else:
            date_str = "Unknown Date"

        date_label = tk.Label(
            meta_frame,
            text=f"📅 {date_str}",
            font=("Segoe UI", 10),
            bg="#1e1e1e",
            fg="#cccccc"
        )
        date_label.pack(side=tk.LEFT, padx=(0, 20))

        # Turn count
        turn_count = metadata.get("turn_count", len(self.session_data.get("conversation", [])) // 2)
        turns_label = tk.Label(
            meta_frame,
            text=f"💬 {turn_count} turns",
            font=("Segoe UI", 10),
            bg="#1e1e1e",
            fg="#cccccc"
        )
        turns_label.pack(side=tk.LEFT, padx=(0, 20))

        # Duration
        duration = metadata.get("duration_minutes", 0)
        if duration > 0:
            duration_label = tk.Label(
                meta_frame,
                text=f"⏱ {duration:.0f} minutes",
                font=("Segoe UI", 10),
                bg="#1e1e1e",
                fg="#cccccc"
            )
            duration_label.pack(side=tk.LEFT, padx=(0, 20))

        # Summary (if available)
        summary = metadata.get("summary", "")
        if summary:
            summary_label = tk.Label(
                parent,
                text=summary,
                font=("Segoe UI", 10),
                bg="#1e1e1e",
                fg="#aaaaaa",
                anchor="w",
                wraplength=800,
                justify=tk.LEFT
            )
            summary_label.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 10))

        # Topics/Tags
        topics_frame = tk.Frame(parent, bg="#1e1e1e")
        topics_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 15))

        key_topics = metadata.get("key_topics", [])
        if key_topics:
            topics_label = tk.Label(
                topics_frame,
                text="Topics:",
                font=("Segoe UI", 9, "bold"),
                bg="#1e1e1e",
                fg="#888888"
            )
            topics_label.pack(side=tk.LEFT, padx=(0, 10))

            for topic in key_topics[:5]:
                tag_label = tk.Label(
                    topics_frame,
                    text=topic,
                    font=("Segoe UI", 9),
                    bg="#3c3c3c",
                    fg="#ffffff",
                    padx=8,
                    pady=2
                )
                tag_label.pack(side=tk.LEFT, padx=2)

        # Emotional arc
        emotional_arc = metadata.get("emotional_arc", "")
        if emotional_arc:
            emotion_label = tk.Label(
                parent,
                text=f"Emotional Arc: {emotional_arc}",
                font=("Segoe UI", 9, "italic"),
                bg="#1e1e1e",
                fg="#888888",
                anchor="w"
            )
            emotion_label.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(0, 10))

    def _build_toolbar(self, parent):
        """Build toolbar with actions"""

        # Add note button
        add_note_btn = tk.Button(
            parent,
            text="📝 Add Note",
            command=self._add_note,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        add_note_btn.pack(side=tk.LEFT, padx=5)

        # Add tags button
        add_tags_btn = tk.Button(
            parent,
            text="🏷 Add Tags",
            command=self._add_tags,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        add_tags_btn.pack(side=tk.LEFT, padx=5)

        # Export button
        export_btn = tk.Button(
            parent,
            text="💾 Export",
            command=self._export_session,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        export_btn.pack(side=tk.LEFT, padx=5)

        # Search in session
        tk.Label(
            parent,
            text="🔍",
            bg="#2b2b2b",
            fg="#ffffff"
        ).pack(side=tk.RIGHT, padx=5)

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            parent,
            textvariable=self.search_var,
            font=("Segoe UI", 9),
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            width=20
        )
        search_entry.pack(side=tk.RIGHT, padx=5)
        search_entry.bind("<Return>", lambda e: self._search_in_conversation())

        search_btn = tk.Button(
            parent,
            text="Search",
            command=self._search_in_conversation,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=5
        )
        search_btn.pack(side=tk.RIGHT, padx=5)

    def _populate_content(self):
        """Populate conversation content"""

        conversation = self.session_data.get("conversation", [])

        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.delete(1.0, tk.END)

        for idx, turn in enumerate(conversation):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            timestamp = turn.get("timestamp", "")

            # Format timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except ValueError:
                    time_str = timestamp
            else:
                time_str = ""

            # Role label
            if role == "user":
                self.conversation_text.insert(tk.END, "USER", "user_label")
            else:
                self.conversation_text.insert(tk.END, "KAY", "kay_label")

            # Timestamp
            if time_str:
                self.conversation_text.insert(tk.END, f" [{time_str}]", "timestamp")

            self.conversation_text.insert(tk.END, ":\n")

            # Content
            self.conversation_text.insert(tk.END, content + "\n\n")

            # Separator (except for last turn)
            if idx < len(conversation) - 1:
                self.conversation_text.insert(tk.END, "─" * 80 + "\n\n", "separator")

        self.conversation_text.config(state=tk.DISABLED)

    def _search_in_conversation(self):
        """Search for text in conversation"""

        query = self.search_var.get().strip()
        if not query:
            return

        # Remove existing highlights
        self.conversation_text.tag_remove("highlight", 1.0, tk.END)

        # Configure highlight tag
        self.conversation_text.tag_config("highlight", background="#ffff00", foreground="#000000")

        # Search and highlight
        self.conversation_text.config(state=tk.NORMAL)

        start_pos = "1.0"
        count = 0

        while True:
            start_pos = self.conversation_text.search(
                query,
                start_pos,
                stopindex=tk.END,
                nocase=True
            )

            if not start_pos:
                break

            end_pos = f"{start_pos}+{len(query)}c"
            self.conversation_text.tag_add("highlight", start_pos, end_pos)
            start_pos = end_pos
            count += 1

        self.conversation_text.config(state=tk.DISABLED)

        if count > 0:
            # Scroll to first match
            first_match = self.conversation_text.tag_ranges("highlight")[0]
            self.conversation_text.see(first_match)
            messagebox.showinfo("Search", f"Found {count} matches")
        else:
            messagebox.showinfo("Search", "No matches found")

    def _add_note(self):
        """Add note to session"""

        if not self.session_manager:
            messagebox.showwarning("Not Available", "Session manager not configured")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Add Note")
        dialog.geometry("500x300")
        dialog.configure(bg="#2b2b2b")

        tk.Label(
            dialog,
            text="Add a note or annotation to this session:",
            font=("Segoe UI", 10),
            bg="#2b2b2b",
            fg="#ffffff"
        ).pack(pady=10)

        note_text = scrolledtext.ScrolledText(
            dialog,
            bg="#3c3c3c",
            fg="#ffffff",
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            height=10
        )
        note_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def save_note():
            note = note_text.get(1.0, tk.END).strip()
            if note:
                session_id = self.session_data["session_id"]
                success = self.session_manager.add_note_to_session(session_id, note)
                if success:
                    messagebox.showinfo("Note Added", "Note saved successfully")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save note")

        btn_frame = tk.Frame(dialog, bg="#2b2b2b")
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="Save",
            command=save_note,
            bg="#3c3c3c",
            fg="#ffffff",
            padx=20
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            bg="#3c3c3c",
            fg="#ffffff",
            padx=20
        ).pack(side=tk.LEFT, padx=5)

    def _add_tags(self):
        """Add tags to session"""

        if not self.session_manager:
            messagebox.showwarning("Not Available", "Session manager not configured")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Add Tags")
        dialog.geometry("400x200")
        dialog.configure(bg="#2b2b2b")

        tk.Label(
            dialog,
            text="Enter tags (comma-separated):",
            font=("Segoe UI", 10),
            bg="#2b2b2b",
            fg="#ffffff"
        ).pack(pady=10)

        tags_entry = tk.Entry(
            dialog,
            font=("Segoe UI", 10),
            bg="#3c3c3c",
            fg="#ffffff",
            width=40
        )
        tags_entry.pack(pady=10, padx=10)

        # Show existing tags
        existing_tags = self.session_data.get("metadata", {}).get("tags", [])
        if existing_tags:
            tk.Label(
                dialog,
                text=f"Existing tags: {', '.join(existing_tags)}",
                font=("Segoe UI", 9),
                bg="#2b2b2b",
                fg="#888888"
            ).pack(pady=5)

        def save_tags():
            tags_str = tags_entry.get().strip()
            if tags_str:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                session_id = self.session_data["session_id"]
                success = self.session_manager.add_tags_to_session(session_id, tags)
                if success:
                    messagebox.showinfo("Tags Added", "Tags saved successfully")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save tags")

        btn_frame = tk.Frame(dialog, bg="#2b2b2b")
        btn_frame.pack(pady=20)

        tk.Button(
            btn_frame,
            text="Save",
            command=save_tags,
            bg="#3c3c3c",
            fg="#ffffff",
            padx=20
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            bg="#3c3c3c",
            fg="#ffffff",
            padx=20
        ).pack(side=tk.LEFT, padx=5)

    def _export_session(self):
        """Export session (placeholder)"""

        messagebox.showinfo(
            "Export",
            "Export functionality is available in the main session browser"
        )
