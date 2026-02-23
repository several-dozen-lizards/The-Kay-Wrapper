"""
Session Browser UI
Tkinter-based session browser with search, filter, and navigation
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import threading


class SessionBrowserUI(tk.Frame):
    """
    Main session browser UI component

    Displays sessions in collapsible monthly groups with search/filter
    """

    def __init__(
        self,
        parent,
        session_manager,
        on_view_session: Optional[Callable] = None,
        on_resume_session: Optional[Callable] = None,
        on_load_for_review: Optional[Callable] = None,
        current_session_id: Optional[str] = None
    ):
        """
        Args:
            parent: Parent tk widget
            session_manager: SessionManager instance
            on_view_session: Callback(session_id) when user clicks View
            on_resume_session: Callback(session_id) when user clicks Resume
            on_load_for_review: Callback(session_id) when user clicks Load for Review
            current_session_id: ID of currently active session (for highlighting)
        """

        super().__init__(parent)
        self.session_manager = session_manager
        self.on_view_session = on_view_session
        self.on_resume_session = on_resume_session
        self.on_load_for_review = on_load_for_review
        self.current_session_id = current_session_id

        self.sessions_by_month = {}
        self.filtered_sessions = []
        self.search_results = []

        # Checkbox tracking for bulk delete
        self.session_checkboxes = {}  # {session_id: BooleanVar}
        self.select_all_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._load_sessions()

    def _build_ui(self):
        """Build the UI layout"""

        self.configure(bg="#2b2b2b")

        # Header
        header_frame = tk.Frame(self, bg="#1e1e1e", height=50)
        header_frame.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="📚 Session Browser",
            font=("Segoe UI", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        )
        title_label.pack(side=tk.LEFT, padx=15, pady=10)

        # Refresh button
        refresh_btn = tk.Button(
            header_frame,
            text="🔄 Refresh",
            command=self._refresh_sessions,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        refresh_btn.pack(side=tk.RIGHT, padx=15, pady=10)

        # Search/Filter Frame
        search_frame = tk.Frame(self, bg="#2b2b2b")
        search_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Search box
        search_label = tk.Label(
            search_frame,
            text="🔍",
            font=("Segoe UI", 12),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        search_label.pack(side=tk.LEFT, padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_changed)

        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            bg="#3c3c3c",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            width=30
        )
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Clear search button
        clear_btn = tk.Button(
            search_frame,
            text="✕",
            command=self._clear_search,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            width=3
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        # Filter button
        filter_btn = tk.Button(
            search_frame,
            text="⚙ Filter",
            command=self._show_filter_dialog,
            bg="#3c3c3c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10
        )
        filter_btn.pack(side=tk.LEFT, padx=5)

        # Bulk actions toolbar
        bulk_frame = tk.Frame(self, bg="#2b2b2b")
        bulk_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

        # Select All checkbox
        select_all_cb = tk.Checkbutton(
            bulk_frame,
            text="Select All",
            variable=self.select_all_var,
            command=self._toggle_select_all,
            bg="#2b2b2b",
            fg="#ffffff",
            selectcolor="#3c3c3c",
            font=("Segoe UI", 10)
        )
        select_all_cb.pack(side=tk.LEFT, padx=5)

        # Delete Selected button (initially disabled)
        self.delete_selected_btn = tk.Button(
            bulk_frame,
            text="🗑 Delete Selected",
            command=self._delete_selected,
            bg="#5c3030",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=15,
            pady=5,
            font=("Segoe UI", 10),
            state=tk.DISABLED
        )
        self.delete_selected_btn.pack(side=tk.LEFT, padx=5)

        # Selected count label
        self.selected_count_label = tk.Label(
            bulk_frame,
            text="0 selected",
            bg="#2b2b2b",
            fg="#888888",
            font=("Segoe UI", 9)
        )
        self.selected_count_label.pack(side=tk.LEFT, padx=10)

        # Session list (scrollable)
        list_frame = tk.Frame(self, bg="#2b2b2b")
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas for scrolling
        self.canvas = tk.Canvas(
            list_frame,
            bg="#2b2b2b",
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.canvas.yview)

        # Frame inside canvas
        self.sessions_frame = tk.Frame(self.canvas, bg="#2b2b2b")
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.sessions_frame,
            anchor="nw"
        )

        # Configure canvas scrolling
        self.sessions_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Status bar
        status_frame = tk.Frame(self, bg="#1e1e1e", height=30)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame,
            text="Ready",
            font=("Segoe UI", 9),
            bg="#1e1e1e",
            fg="#888888",
            anchor="w"
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)

    def _load_sessions(self):
        """Load sessions from session manager"""

        self._update_status("Loading sessions...")

        # Load in background thread
        def load_thread():
            try:
                self.sessions_by_month = self.session_manager.get_sessions_by_month()
                self.after(0, self._render_sessions)
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Error: {e}"))

        threading.Thread(target=load_thread, daemon=True).start()

    def _render_sessions(self):
        """Render session list UI"""

        # Clear existing
        for widget in self.sessions_frame.winfo_children():
            widget.destroy()

        # Get all current session IDs
        all_session_ids = set()
        for sessions in self.sessions_by_month.values():
            for session_info in sessions:
                all_session_ids.add(session_info["session_id"])

        # Clean up checkbox references for deleted sessions
        stale_ids = set(self.session_checkboxes.keys()) - all_session_ids
        for stale_id in stale_ids:
            del self.session_checkboxes[stale_id]

        # Determine what to show
        if self.search_var.get().strip():
            self._render_search_results()
        else:
            self._render_monthly_groups()

        total_sessions = sum(len(sessions) for sessions in self.sessions_by_month.values())
        self._update_status(f"{total_sessions} sessions loaded")

        # Update selected count after render
        self._update_selected_count()

    def _render_monthly_groups(self):
        """Render sessions grouped by month with collapsible sections"""

        # Sort months (most recent first)
        sorted_months = sorted(
            self.sessions_by_month.keys(),
            reverse=True
        )

        for month_key in sorted_months:
            sessions = self.sessions_by_month[month_key]

            if not sessions:
                continue

            # Month header (collapsible)
            month_frame = self._create_month_header(month_key, len(sessions))
            month_frame.pack(fill=tk.X, padx=5, pady=5)

            # Sessions container (initially expanded)
            sessions_container = tk.Frame(month_frame, bg="#2b2b2b")
            sessions_container.pack(fill=tk.X, padx=20, pady=5)

            for session_info in sessions:
                session_widget = self._create_session_widget(session_info)
                session_widget.pack(fill=tk.X, pady=3)

    def _create_month_header(self, month_key: str, count: int) -> tk.Frame:
        """Create collapsible month header"""

        frame = tk.Frame(self.sessions_frame, bg="#2b2b2b")

        # Format month label
        if month_key != "Unknown":
            try:
                dt = datetime.strptime(month_key, "%Y-%m")
                month_label = dt.strftime("%B %Y")
            except ValueError:
                month_label = month_key
        else:
            month_label = "Unknown Date"

        header = tk.Label(
            frame,
            text=f"▼ {month_label} ({count})",
            font=("Segoe UI", 11, "bold"),
            bg="#3c3c3c",
            fg="#ffffff",
            anchor="w",
            padx=10,
            pady=8
        )
        header.pack(fill=tk.X)

        # TODO: Add click handler for collapse/expand

        return frame

    def _create_session_widget(self, session_info: Dict[str, Any]) -> tk.Frame:
        """Create widget for individual session"""

        is_current = (session_info["session_id"] == self.current_session_id)
        session_id = session_info["session_id"]

        # Main frame
        frame = tk.Frame(
            self.sessions_frame,
            bg="#4c4c4c" if is_current else "#3c3c3c",
            relief=tk.RAISED if is_current else tk.FLAT,
            borderwidth=2 if is_current else 1
        )

        # Content frame
        content_frame = tk.Frame(frame, bg=frame.cget("bg"))
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Title row
        title_row = tk.Frame(content_frame, bg=frame.cget("bg"))
        title_row.pack(fill=tk.X)

        # Checkbox for bulk delete (prevent deleting current session)
        if not is_current:
            # Create checkbox var if not exists
            if session_id not in self.session_checkboxes:
                self.session_checkboxes[session_id] = tk.BooleanVar(value=False)

            checkbox = tk.Checkbutton(
                title_row,
                variable=self.session_checkboxes[session_id],
                command=self._update_selected_count,
                bg=frame.cget("bg"),
                selectcolor="#3c3c3c"
            )
            checkbox.pack(side=tk.LEFT, padx=(0, 5))

        # Current session indicator
        if is_current:
            indicator = tk.Label(
                title_row,
                text="●",
                font=("Segoe UI", 14),
                bg=frame.cget("bg"),
                fg="#00ff00"
            )
            indicator.pack(side=tk.LEFT, padx=(0, 5))

        # Title
        title = session_info.get("title", "Untitled Session")
        title_label = tk.Label(
            title_row,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=frame.cget("bg"),
            fg="#ffffff",
            anchor="w"
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Date/time
        start_time = session_info.get("start_time", "")
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time)
                date_str = dt.strftime("%b %d, %I:%M %p")
            except ValueError:
                date_str = start_time
        else:
            date_str = "Unknown"

        date_label = tk.Label(
            title_row,
            text=date_str,
            font=("Segoe UI", 9),
            bg=frame.cget("bg"),
            fg="#888888"
        )
        date_label.pack(side=tk.RIGHT, padx=5)

        # Summary (if available)
        summary = session_info.get("summary", "")
        if summary:
            summary_label = tk.Label(
                content_frame,
                text=summary[:120] + ("..." if len(summary) > 120 else ""),
                font=("Segoe UI", 9),
                bg=frame.cget("bg"),
                fg="#cccccc",
                anchor="w",
                wraplength=500,
                justify=tk.LEFT
            )
            summary_label.pack(fill=tk.X, pady=(5, 0))

        # Metadata row
        meta_row = tk.Frame(content_frame, bg=frame.cget("bg"))
        meta_row.pack(fill=tk.X, pady=(5, 0))

        # Turn count
        turn_count = session_info.get("turn_count", 0)
        turns_label = tk.Label(
            meta_row,
            text=f"💬 {turn_count} turns",
            font=("Segoe UI", 9),
            bg=frame.cget("bg"),
            fg="#888888"
        )
        turns_label.pack(side=tk.LEFT, padx=(0, 15))

        # Duration
        duration = session_info.get("duration_minutes", 0)
        if duration > 0:
            duration_label = tk.Label(
                meta_row,
                text=f"⏱ {duration:.0f} min",
                font=("Segoe UI", 9),
                bg=frame.cget("bg"),
                fg="#888888"
            )
            duration_label.pack(side=tk.LEFT, padx=(0, 15))

        # Tags
        tags = session_info.get("tags", [])
        if tags:
            tags_str = ", ".join(tags[:3])
            if len(tags) > 3:
                tags_str += "..."

            tags_label = tk.Label(
                meta_row,
                text=f"🏷 {tags_str}",
                font=("Segoe UI", 9),
                bg=frame.cget("bg"),
                fg="#888888"
            )
            tags_label.pack(side=tk.LEFT)

        # Actions row
        actions_row = tk.Frame(content_frame, bg=frame.cget("bg"))
        actions_row.pack(fill=tk.X, pady=(8, 0))

        session_id = session_info["session_id"]

        # View button
        view_btn = tk.Button(
            actions_row,
            text="👁 View",
            command=lambda: self._handle_view(session_id),
            bg="#5c5c5c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            font=("Segoe UI", 9)
        )
        view_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Resume button
        if not is_current:
            resume_btn = tk.Button(
                actions_row,
                text="▶ Resume",
                command=lambda: self._handle_resume(session_id),
                bg="#5c5c5c",
                fg="#ffffff",
                relief=tk.FLAT,
                padx=8,
                pady=3,
                font=("Segoe UI", 9)
            )
            resume_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Load for review button
        review_btn = tk.Button(
            actions_row,
            text="📖 Load for Review",
            command=lambda: self._handle_load_review(session_id),
            bg="#5c5c5c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            font=("Segoe UI", 9)
        )
        review_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Export button
        export_btn = tk.Button(
            actions_row,
            text="💾 Export",
            command=lambda: self._handle_export(session_id),
            bg="#5c5c5c",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            font=("Segoe UI", 9)
        )
        export_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Delete button
        delete_btn = tk.Button(
            actions_row,
            text="🗑 Delete",
            command=lambda: self._handle_delete(session_id),
            bg="#5c5c5c",
            fg="#ff6666",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            font=("Segoe UI", 9)
        )
        delete_btn.pack(side=tk.RIGHT)

        return frame

    def _render_search_results(self):
        """Render search results"""

        query = self.search_var.get().strip()

        if not query:
            self._render_monthly_groups()
            return

        # Perform search in background
        def search_thread():
            try:
                results = self.session_manager.search_sessions(query)
                self.search_results = results
                self.after(0, self._display_search_results)
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Search error: {e}"))

        threading.Thread(target=search_thread, daemon=True).start()

    def _display_search_results(self):
        """Display search results in UI"""

        # Clear existing
        for widget in self.sessions_frame.winfo_children():
            widget.destroy()

        if not self.search_results:
            no_results = tk.Label(
                self.sessions_frame,
                text="No sessions found matching your search",
                font=("Segoe UI", 11),
                bg="#2b2b2b",
                fg="#888888",
                pady=50
            )
            no_results.pack()
            self._update_status(f"No results for '{self.search_var.get()}'")
            return

        # Render each result
        for session_info, context_snippets in self.search_results:
            result_frame = self._create_search_result_widget(session_info, context_snippets)
            result_frame.pack(fill=tk.X, padx=5, pady=5)

        self._update_status(f"{len(self.search_results)} sessions found")

    def _create_search_result_widget(
        self,
        session_info: Dict[str, Any],
        context_snippets: List[str]
    ) -> tk.Frame:
        """Create widget for search result"""

        frame = self._create_session_widget(session_info)

        # Add context snippets below
        if context_snippets:
            snippets_frame = tk.Frame(frame, bg=frame.cget("bg"))
            snippets_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

            snippets_label = tk.Label(
                snippets_frame,
                text="Matches:",
                font=("Segoe UI", 9, "bold"),
                bg=frame.cget("bg"),
                fg="#888888",
                anchor="w"
            )
            snippets_label.pack(anchor="w")

            for snippet in context_snippets[:3]:  # Max 3 snippets
                snippet_text = tk.Label(
                    snippets_frame,
                    text=f"  • {snippet}",
                    font=("Segoe UI", 8),
                    bg=frame.cget("bg"),
                    fg="#aaaaaa",
                    anchor="w",
                    wraplength=450,
                    justify=tk.LEFT
                )
                snippet_text.pack(anchor="w", pady=1)

        return frame

    def _handle_view(self, session_id: str):
        """Handle view button click"""
        if self.on_view_session:
            self.on_view_session(session_id)

    def _handle_resume(self, session_id: str):
        """Handle resume button click"""
        if self.on_resume_session:
            if messagebox.askyesno(
                "Resume Session",
                "This will end your current session and resume the selected session. Continue?"
            ):
                self.on_resume_session(session_id)

    def _handle_load_review(self, session_id: str):
        """Handle load for review button click"""
        if self.on_load_for_review:
            self.on_load_for_review(session_id)

    def _handle_export(self, session_id: str):
        """Handle export button click"""

        # Ask for format
        format_choice = messagebox.askquestion(
            "Export Format",
            "Export as Markdown? (No = Plain Text)",
            icon='question'
        )

        format_type = "md" if format_choice == "yes" else "txt"
        extension = "md" if format_type == "md" else "txt"

        # Ask for save location
        filepath = filedialog.asksaveasfilename(
            defaultextension=f".{extension}",
            filetypes=[(f"{extension.upper()} files", f"*.{extension}"), ("All files", "*.*")],
            initialfile=f"session_{session_id}.{extension}"
        )

        if filepath:
            try:
                success = self.session_manager.export_session_file(
                    session_id,
                    filepath,
                    format=format_type
                )

                if success:
                    messagebox.showinfo("Export Successful", f"Session exported to:\n{filepath}")
                else:
                    messagebox.showerror("Export Failed", "Failed to export session")
            except Exception as e:
                messagebox.showerror("Export Error", f"Error exporting session:\n{e}")

    def _handle_delete(self, session_id: str):
        """Handle delete button click"""

        if messagebox.askyesno(
            "Delete Session",
            "Are you sure you want to delete this session? This cannot be undone.",
            icon='warning'
        ):
            try:
                success = self.session_manager.delete_session(session_id)

                if success:
                    self._refresh_sessions()
                    messagebox.showinfo("Deleted", "Session deleted successfully")
                else:
                    messagebox.showerror("Delete Failed", "Failed to delete session")
            except Exception as e:
                messagebox.showerror("Delete Error", f"Error deleting session:\n{e}")

    def _show_filter_dialog(self):
        """Show filter options dialog"""

        dialog = tk.Toplevel(self)
        dialog.title("Filter Sessions")
        dialog.geometry("400x300")
        dialog.configure(bg="#2b2b2b")

        # TODO: Implement filter UI
        tk.Label(
            dialog,
            text="Filter options coming soon...",
            bg="#2b2b2b",
            fg="#ffffff",
            font=("Segoe UI", 11)
        ).pack(pady=50)

        close_btn = tk.Button(
            dialog,
            text="Close",
            command=dialog.destroy,
            bg="#3c3c3c",
            fg="#ffffff"
        )
        close_btn.pack(pady=20)

    def _on_search_changed(self, *args):
        """Handle search text change"""
        # Debounce search
        if hasattr(self, "_search_timer"):
            self.after_cancel(self._search_timer)

        self._search_timer = self.after(500, self._render_sessions)

    def _clear_search(self):
        """Clear search field"""
        self.search_var.set("")

    def _refresh_sessions(self):
        """Refresh session list"""
        self._load_sessions()

    def _update_status(self, message: str):
        """Update status bar"""
        self.status_label.config(text=message)

    def _on_frame_configure(self, event=None):
        """Update scroll region when frame size changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Update frame width when canvas is resized"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def set_current_session(self, session_id: str):
        """Update current session indicator"""
        self.current_session_id = session_id
        self._render_sessions()

    def _toggle_select_all(self):
        """Toggle all session checkboxes"""
        select_state = self.select_all_var.get()

        # Update all visible session checkboxes
        for session_id, checkbox_var in self.session_checkboxes.items():
            # Only toggle if session is not current (current session can't be deleted)
            if session_id != self.current_session_id:
                checkbox_var.set(select_state)

        self._update_selected_count()

    def _delete_selected(self):
        """Delete all selected sessions"""
        # Get list of selected session IDs
        selected_ids = [
            session_id
            for session_id, checkbox_var in self.session_checkboxes.items()
            if checkbox_var.get()
        ]

        if not selected_ids:
            messagebox.showwarning("No Selection", "No sessions selected for deletion")
            return

        # Confirm deletion
        count = len(selected_ids)
        if not messagebox.askyesno(
            "Delete Multiple Sessions",
            f"Are you sure you want to delete {count} session{'s' if count > 1 else ''}?\n\n"
            "This cannot be undone.",
            icon='warning'
        ):
            return

        # Delete sessions
        successful = 0
        failed = 0

        for session_id in selected_ids:
            try:
                if self.session_manager.delete_session(session_id):
                    successful += 1
                    # Remove from checkbox tracking
                    if session_id in self.session_checkboxes:
                        del self.session_checkboxes[session_id]
                else:
                    failed += 1
            except Exception as e:
                print(f"Error deleting session {session_id}: {e}")
                failed += 1

        # Show result
        if failed == 0:
            messagebox.showinfo("Deletion Complete", f"Successfully deleted {successful} session{'s' if successful > 1 else ''}")
        else:
            messagebox.showwarning(
                "Deletion Incomplete",
                f"Deleted {successful} session{'s' if successful > 1 else ''}\n"
                f"Failed to delete {failed} session{'s' if failed > 1 else ''}"
            )

        # Refresh list and reset select all
        self.select_all_var.set(False)
        self._refresh_sessions()

    def _update_selected_count(self):
        """Update the selected count label"""
        count = sum(
            1
            for checkbox_var in self.session_checkboxes.values()
            if checkbox_var.get()
        )

        self.selected_count_label.config(
            text=f"{count} selected",
            fg="#00ff00" if count > 0 else "#888888"
        )

        # Update delete button state
        if count > 0:
            self.delete_selected_btn.config(state=tk.NORMAL)
        else:
            self.delete_selected_btn.config(state=tk.DISABLED)
