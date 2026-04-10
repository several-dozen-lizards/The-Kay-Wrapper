"""
Curation UI Integration for the entity

Integrates the memory curation system with the main UI.
Provides a tab-based interface for content-type-aware memory curation.

Now includes Purge Reserve integration for safe soft-delete workflow.
"""

import customtkinter as ctk
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from curation_ui import CurationDashboard, CurationSessionPanel, CurationResultsPanel
from engines.memory_curation import (
    MemoryCurator,
    ContentTypeClassifier,
    CurationLearningTracker,
    ContentType,
    CurationSession,
    AutonomousCurationProcessor
)
from engines.purge_reserve import PurgeReserve, DeletionSeverity
from purge_reserve_ui import (
    PurgeReserveDashboard,
    PurgeReserveListView,
    AuditLogView,
    DeletionWarningDialog,
    MemoryDetailView
)


class CurationUIIntegration:
    """
    Integrates memory curation UI with the main CompanionApp.

    Provides:
    - Curation dashboard with content type breakdown
    - Session-based curation workflow
    - Learning progress tracking
    - Purge reserve for safe deletions
    """

    def __init__(self, companion_ui):
        """
        Initialize curation UI integration.

        Args:
            companion_ui: The main CompanionApp instance
        """
        self.companion_ui = companion_ui
        self.palette = companion_ui.palette

        # Get panel font sizes from companion_ui (with defaults if not available)
        self.font_sizes = getattr(companion_ui, 'panel_font_sizes', {
            'tiny': 10,
            'small': 12,
            'normal': 13,
            'medium': 14,
            'large': 16,
            'header': 18,
        })

        # Get memory engine from companion_ui
        # Note: In CompanionApp, memory engine is stored as 'memory', not 'memory_engine'
        self.memory_engine = getattr(companion_ui, 'memory', None) or getattr(companion_ui, 'memory_engine', None)

        if self.memory_engine:
            mem_count = len(self.memory_engine.memories) if hasattr(self.memory_engine, 'memories') else 0
            print(f"[CURATION] Connected to memory engine with {mem_count} memories")
        else:
            print("[CURATION] WARNING: No memory engine available")

        # Initialize curation components
        self.curator = MemoryCurator(memory_engine=self.memory_engine)
        self.learning_tracker = CurationLearningTracker()

        # Initialize purge reserve for soft deletes
        self.purge_reserve = PurgeReserve()

        # Session state
        self.current_session_panel: Optional[CurationSessionPanel] = None
        self.current_batch_analysis: Optional[Dict] = None

        # Track active panel and view state
        self.active_panel: Optional[ctk.CTkFrame] = None
        self.current_view: str = "dashboard"  # 'dashboard', 'curation', 'purge_reserve', 'flagged', 'audit'

        # Option to display curation updates in main chat window
        self.display_in_main_window = True  # When True, also outputs to main chat

    def _output_to_main_window(self, message: str, tag: str = "system"):
        """
        Output a message to the main chat window.

        Args:
            message: Text to display
            tag: Message tag ('system', 'entity', 'user')
        """
        if not self.display_in_main_window:
            return

        # Check if companion_ui has the add_message method
        if hasattr(self.companion_ui, 'add_message'):
            self.companion_ui.add_message(tag, message)
        elif hasattr(self.companion_ui, 'chat_log'):
            # Fallback: write directly to chat_log
            try:
                self.companion_ui.chat_log.configure(state="normal")
                prefix = "entity" if tag == "entity" else "System"
                self.companion_ui.chat_log.insert("end", f"[{prefix}]: {message}\n\n", tag)
                self.companion_ui.chat_log.see("end")
                self.companion_ui.chat_log.configure(state="disabled")
            except Exception as e:
                print(f"[CURATION] Main window output error: {e}")

    def create_panel_content(self, parent) -> ctk.CTkFrame:
        """
        Create the main curation panel content.
        Called when curation tab is clicked.

        Args:
            parent: Parent widget

        Returns:
            The curation panel frame
        """
        # Main container with scrolling
        container = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B"),
            scrollbar_button_hover_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        container.pack(fill="both", expand=True)

        self.active_panel = container

        # Create dashboard view by default
        self._show_dashboard(container)

        return container

    def _show_dashboard(self, parent):
        """Show the curation dashboard view."""
        self.current_view = "dashboard"

        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        # Create dashboard with memory retrieval callback
        dashboard = CurationDashboard(
            parent,
            self.palette,
            curator=self.curator,
            memory_engine=self.memory_engine,
            memory_retrieval_func=lambda: self._get_memories_for_curation(limit=1000)  # Get more for dashboard stats
        )
        dashboard.pack(fill="both", expand=True, padx=5, pady=5)

        # Set callback for starting session
        dashboard.on_start_session = lambda: self._start_curation_session(parent)

        # Add purge reserve section
        self._add_purge_reserve_section(parent)

        # Add learning progress section
        self._add_learning_section(parent)

    def _add_purge_reserve_section(self, parent):
        """Add purge reserve dashboard to the main view."""
        # Separator
        ctk.CTkLabel(
            parent,
            text="",
            height=5
        ).pack()

        # Purge reserve dashboard
        purge_dashboard = PurgeReserveDashboard(
            parent,
            self.palette,
            purge_reserve=self.purge_reserve
        )
        purge_dashboard.pack(fill="x", padx=5, pady=5)

        # Set callbacks
        purge_dashboard.on_view_reserve = lambda: self._show_purge_reserve_list(parent)
        purge_dashboard.on_view_flagged = lambda: self._show_flagged_deletions(parent)
        purge_dashboard.on_view_audit = lambda: self._show_audit_log(parent)

    def _show_purge_reserve_list(self, parent):
        """Show the purge reserve list view."""
        self.current_view = "purge_reserve"

        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        # Create list view
        list_view = PurgeReserveListView(
            parent,
            self.palette,
            purge_reserve=self.purge_reserve,
            show_only_flagged=False
        )
        list_view.pack(fill="both", expand=True)

        # Set callbacks
        list_view.on_restore = self._restore_memory
        list_view.on_permanent_delete = self._permanent_delete_memory
        list_view.on_view_full = lambda m: MemoryDetailView(self.companion_ui, self.palette, m)
        list_view.on_back = lambda: self._show_dashboard(parent)

    def _show_flagged_deletions(self, parent):
        """Show only flagged deletions for review."""
        self.current_view = "flagged"

        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        # Create list view showing only flagged
        list_view = PurgeReserveListView(
            parent,
            self.palette,
            purge_reserve=self.purge_reserve,
            show_only_flagged=True
        )
        list_view.pack(fill="both", expand=True)

        # Set callbacks
        list_view.on_restore = self._restore_memory
        list_view.on_permanent_delete = self._permanent_delete_memory
        list_view.on_view_full = lambda m: MemoryDetailView(self.companion_ui, self.palette, m)
        list_view.on_back = lambda: self._show_dashboard(parent)

    def _show_audit_log(self, parent):
        """Show the audit log view."""
        self.current_view = "audit"

        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        # Create audit log view
        audit_view = AuditLogView(
            parent,
            self.palette,
            purge_reserve=self.purge_reserve,
            font_sizes=self.font_sizes
        )
        audit_view.pack(fill="both", expand=True)

        # Set callbacks
        audit_view.on_back = lambda: self._show_dashboard(parent)

    def _restore_memory(self, memory_id: str):
        """Restore a memory from purge reserve."""
        original = self.purge_reserve.restore(memory_id, restored_by="re")

        if original and self.memory_engine:
            # Add back to memory engine
            if hasattr(self.memory_engine, 'memories'):
                self.memory_engine.memories.append(original)

                # Save to disk
                if hasattr(self.memory_engine, '_save_to_disk'):
                    try:
                        self.memory_engine._save_to_disk()
                        print(f"[CURATION] Restored memory and saved to disk")
                    except Exception as e:
                        print(f"[CURATION] Error saving after restore: {e}")

    def _permanent_delete_memory(self, memory_id: str):
        """Permanently delete a memory from purge reserve."""
        self.purge_reserve.permanent_delete(memory_id, deleted_by="re", reason="User confirmed deletion")

    def _add_learning_section(self, parent):
        """Add learning progress section to dashboard."""
        learning_frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        learning_frame.pack(fill="x", padx=5, pady=10)

        ctk.CTkLabel(
            learning_frame,
            text="━" * 15 + "\n📈 LEARNING PROGRESS\n" + "━" * 15,
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        ).pack(pady=10)

        # Get learning summary
        summary = self.learning_tracker.get_learning_summary()

        if summary["total_classifications"] == 0:
            ctk.CTkLabel(
                learning_frame,
                text="No curation sessions completed yet.\nStart curating to see learning progress.",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("muted", "#9B7D54"),
                justify="center"
            ).pack(pady=10)
        else:
            # Show learning stats
            trend_colors = {
                "improving": self.palette.get("accent", "#4A9B9B"),
                "stable": self.palette.get("text", "#E8DCC4"),
                "needs_attention": self.palette.get("user", "#D499B9"),
                "insufficient_data": self.palette.get("muted", "#9B7D54")
            }

            trend_text = summary["accuracy_trend"].replace("_", " ").title()

            stats_text = (
                f"Total classifications: {summary['total_classifications']}\n"
                f"Sessions analyzed: {summary['sessions_analyzed']}\n"
                f"Accuracy trend: {trend_text}"
            )

            if summary["latest_accuracy"]:
                stats_text += f"\nLatest accuracy: {summary['latest_accuracy']:.0%}"

            ctk.CTkLabel(
                learning_frame,
                text=stats_text,
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=trend_colors.get(summary["accuracy_trend"], self.palette.get("text", "#E8DCC4")),
                justify="left"
            ).pack(anchor="w", padx=15, pady=5)

            # Show common misclassifications
            if summary["common_misclassifications"]:
                ctk.CTkLabel(
                    learning_frame,
                    text="Common misclassifications:",
                    font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                    text_color=self.palette.get("text", "#E8DCC4")
                ).pack(anchor="w", padx=15, pady=(10, 2))

                for misclass, count in summary["common_misclassifications"][:3]:
                    ctk.CTkLabel(
                        learning_frame,
                        text=f"  • {misclass}: {count}x",
                        font=ctk.CTkFont(family="Courier", size=8),
                        text_color=self.palette.get("muted", "#9B7D54")
                    ).pack(anchor="w", padx=15)

        ctk.CTkLabel(learning_frame, text="").pack(pady=5)

    def _start_curation_session(self, parent):
        """Start an AUTONOMOUS curation session where the entity actually reviews memories.

        IMPORTANT: This now displays in the MAIN WINDOW (large, readable)
        instead of the sidebar (tiny, unreadable).
        """
        print(f"[CURATION SESSION] ========================================")
        print(f"[CURATION SESSION] Starting AUTONOMOUS curation session...")
        print(f"[CURATION SESSION] memory_engine: {self.memory_engine}")
        print(f"[CURATION SESSION] memory_engine.memories count: {len(self.memory_engine.memories) if self.memory_engine and hasattr(self.memory_engine, 'memories') else 'N/A'}")

        # Get memories to curate
        memories = self._get_memories_for_curation()
        print(f"[CURATION SESSION] Got {len(memories) if memories else 0} memories")

        if not memories:
            print("[CURATION SESSION] No memories - showing no memories message")
            self._show_no_memories_message(parent)
            return

        print(f"[CURATION SESSION] Proceeding with {len(memories)} memories...")

        # Store sidebar parent for later control updates
        self.sidebar_parent = parent

        # Display curation in the MAIN WINDOW (large, readable)
        # This uses companion_ui's show_curation_in_main_area() to replace chat_log
        if hasattr(self.companion_ui, 'show_curation_in_main_area'):
            print("[CURATION SESSION] Displaying in MAIN WINDOW (large format)")
            self.companion_ui.show_curation_in_main_area(
                lambda frame: self._create_curation_main_view(frame, memories)
            )
            # Update sidebar to show minimal controls
            self._show_sidebar_controls_only(parent)
        else:
            # Fallback: display in sidebar panel (old behavior)
            print("[CURATION SESSION] Fallback: displaying in sidebar panel")
            self._display_curation_in_main_panel(memories, parent)

    def _show_sidebar_controls_only(self, parent):
        """
        Show minimal controls in the sidebar while curation runs in main window.
        Sidebar shows: progress stats, stop button, status indicator.
        """
        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        # Minimal sidebar controls frame
        controls_frame = ctk.CTkFrame(parent, fg_color="transparent")
        controls_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Header
        ctk.CTkLabel(
            controls_frame,
            text="━" * 15 + "\n📋 CURATION ACTIVE\n" + "━" * 15,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes.get('medium', 14), weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        ).pack(pady=10)

        # Status indicator
        ctk.CTkLabel(
            controls_frame,
            text="the entity is reviewing memories\nin the main window →",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes.get('normal', 13)),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="center"
        ).pack(pady=10)

        # Stats frame (updated by progress callback)
        self.sidebar_stats_frame = ctk.CTkFrame(
            controls_frame,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        self.sidebar_stats_frame.pack(fill="x", padx=5, pady=10)

        ctk.CTkLabel(
            self.sidebar_stats_frame,
            text="Progress:",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes.get('small', 12), weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.sidebar_progress_label = ctk.CTkLabel(
            self.sidebar_stats_frame,
            text="Starting...",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes.get('small', 12)),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        self.sidebar_progress_label.pack(anchor="w", padx=15, pady=(0, 10))

        # Back to chat button (cancel/finish)
        ctk.CTkButton(
            controls_frame,
            text="◀ Back to Chat",
            command=self._finish_curation_and_restore_chat,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes.get('normal', 13)),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=35
        ).pack(fill="x", padx=5, pady=20)

    def _create_curation_main_view(self, parent, memories: List[Dict]):
        """
        Create the curation session view in the MAIN WINDOW.
        This displays with LARGE, readable fonts in the central area.
        """
        self.current_view = "curation"
        self.curation_main_parent = parent

        # Create the progress panel with LARGE fonts
        self._create_main_window_progress(parent, len(memories))

        # Create autonomous processor with progress callback
        def update_progress(progress_data):
            self._update_main_window_progress(progress_data)
            # Also update sidebar stats
            self._update_sidebar_stats(progress_data)

        processor = AutonomousCurationProcessor(
            curator=self.curator,
            memory_engine=self.memory_engine,
            purge_reserve=self.purge_reserve,
            progress_callback=update_progress
        )

        # Run curation in background thread
        import threading

        def run_curation():
            try:
                summary = processor.run_curation_session(memories, cluster_size=5)

                # Update UI on main thread
                self.companion_ui.after(0, lambda: self._show_results_in_main_window(parent, summary))

                # Save memory engine changes
                if self.memory_engine and hasattr(self.memory_engine, '_save_to_disk'):
                    self.memory_engine._save_to_disk()
                    print("[CURATION] Memory changes saved to disk")

            except Exception as e:
                print(f"[CURATION] Error in session: {e}")
                import traceback
                traceback.print_exc()
                self.companion_ui.after(0, lambda: self._show_error_in_main_window(parent, str(e)))

        thread = threading.Thread(target=run_curation, daemon=True)
        thread.start()

    def _create_main_window_progress(self, parent, total_memories: int):
        """
        Create the curation progress view in the MAIN WINDOW with LARGE fonts.
        """
        # LARGE font sizes for main window readability
        FONT_HUGE = 28
        FONT_LARGE = 22
        FONT_MEDIUM = 18
        FONT_NORMAL = 16

        # Scrollable container
        scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B"),
            scrollbar_button_hover_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        scroll.pack(fill="both", expand=True)

        self.main_window_scroll = scroll

        # Header - HUGE
        header = ctk.CTkLabel(
            scroll,
            text="=" * 40 + "\n🧠 KAY'S MEMORY CURATION SESSION\n" + "=" * 40,
            font=ctk.CTkFont(family="Courier", size=FONT_HUGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=20)

        # Status label - LARGE
        self.main_window_status = ctk.CTkLabel(
            scroll,
            text=f"Reviewing {total_memories} memories...",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        self.main_window_status.pack(pady=10)

        # Progress bar - LARGE
        self.main_window_progress_bar = ctk.CTkProgressBar(
            scroll,
            width=600,
            height=35,
            progress_color=self.palette.get("accent", "#4A9B9B"),
            fg_color=self.palette.get("input", "#4A2B5C")
        )
        self.main_window_progress_bar.pack(pady=15)
        self.main_window_progress_bar.set(0)

        # Cluster info - LARGE
        self.main_window_cluster = ctk.CTkLabel(
            scroll,
            text="Clustering memories...",
            font=ctk.CTkFont(family="Courier", size=FONT_MEDIUM),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.main_window_cluster.pack(pady=5)

        # Stats row - LARGE
        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=15)

        self.main_window_stats = {}
        for action, color in [
            ("KEPT", self.palette.get("user", "#D499B9")),
            ("SUMMARIZED", self.palette.get("accent", "#4A9B9B")),
            ("ARCHIVED", self.palette.get("muted", "#9B7D54")),
            ("DELETED", self.palette.get("system", "#C4A574"))
        ]:
            frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            frame.pack(side="left", expand=True)

            self.main_window_stats[action] = ctk.CTkLabel(
                frame,
                text=f"{action}: 0",
                font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
                text_color=color
            )
            self.main_window_stats[action].pack()

        # Decision log frame - LARGE
        log_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=3,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        log_frame.pack(fill="both", expand=True, padx=10, pady=15)

        ctk.CTkLabel(
            log_frame,
            text="💭 the entity's Reasoning (Live):",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Scrollable decision log with LARGE font
        self.main_window_log = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("input", "#4A2B5C"),
            text_color=self.palette.get("text", "#E8DCC4"),
            height=400,
            wrap="word"
        )
        self.main_window_log.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.main_window_log.insert("end", "Waiting for the entity to start reviewing...\n\n")

    def _update_main_window_progress(self, progress_data: Dict):
        """Update the main window progress UI with the entity's full reasoning."""
        try:
            current = progress_data.get("current", 0)
            total = progress_data.get("total", 1)
            stats = progress_data.get("stats", {})
            latest_decisions = progress_data.get("latest_decisions", [])

            # Update progress bar
            progress = current / max(total, 1)
            self.main_window_progress_bar.set(progress)

            # Update cluster label
            self.main_window_cluster.configure(
                text=f"Cluster {current}/{total} - the entity is reviewing..."
            )

            # Update stats
            self.main_window_stats["KEPT"].configure(text=f"KEPT: {stats.get('kept', 0)}")
            self.main_window_stats["SUMMARIZED"].configure(text=f"SUMMARIZED: {stats.get('summarized', 0)}")
            self.main_window_stats["ARCHIVED"].configure(text=f"ARCHIVED: {stats.get('archived', 0)}")
            self.main_window_stats["DELETED"].configure(text=f"DELETED: {stats.get('deleted', 0)}")

            # Add cluster header
            if latest_decisions:
                cluster_header = f"\n{'='*60}\nCLUSTER {current}/{total} ({len(latest_decisions)} memories)\n{'='*60}\n\n"
                self.main_window_log.insert("end", cluster_header)

            # Add decisions with FULL reasoning
            for decision in latest_decisions:
                action = decision.get("action", "unknown").upper()
                preview = decision.get("memory", {}).get("content", "")[:120]
                reasoning = decision.get("reasoning", "")
                summary = decision.get("summary", "")
                kay_override = decision.get("kay_override", False)

                # Action indicator
                if action == "KEEP":
                    action_icon = "✓ [KEEP]"
                elif action == "SUMMARIZE":
                    action_icon = "📝 [SUMMARIZE]"
                elif action == "ARCHIVE":
                    action_icon = "📦 [ARCHIVE]"
                elif action == "DELETE":
                    action_icon = "🗑 [DELETE]"
                else:
                    action_icon = f"[{action}]"

                # Build detailed log entry
                log_entry = f"{action_icon}\n"
                log_entry += f"  Memory: \"{preview}...\"\n"

                # Show the entity's full reasoning
                if reasoning:
                    wrapped_reasoning = self._wrap_text(reasoning, 80)
                    log_entry += f"\n  the entity's reasoning:\n"
                    for line in wrapped_reasoning.split('\n'):
                        log_entry += f"    {line}\n"

                # Show the entity's summary if action was SUMMARIZE
                if action == "SUMMARIZE" and summary:
                    wrapped_summary = self._wrap_text(summary, 80)
                    log_entry += f"\n  the entity's summary:\n"
                    for line in wrapped_summary.split('\n'):
                        log_entry += f"    >> {line}\n"

                if kay_override:
                    log_entry += f"  [the entity overrode classifier suggestion]\n"

                log_entry += "\n" + "-"*60 + "\n"

                self.main_window_log.insert("end", log_entry)
                self.main_window_log.see("end")

            # Update status
            if current < total:
                self.main_window_status.configure(
                    text=f"the entity reviewed cluster {current}/{total}..."
                )
            else:
                self.main_window_status.configure(
                    text=f"the entity has reviewed all {total} clusters. Applying decisions..."
                )

            # Force UI update
            if hasattr(self, 'main_window_scroll'):
                self.main_window_scroll.update_idletasks()

        except Exception as e:
            print(f"[CURATION UI] Main window progress update error: {e}")

    def _update_sidebar_stats(self, progress_data: Dict):
        """Update the minimal sidebar stats during curation."""
        try:
            if hasattr(self, 'sidebar_progress_label'):
                current = progress_data.get("current", 0)
                total = progress_data.get("total", 1)
                stats = progress_data.get("stats", {})

                stats_text = (
                    f"Cluster {current}/{total}\n"
                    f"Kept: {stats.get('kept', 0)}\n"
                    f"Summarized: {stats.get('summarized', 0)}\n"
                    f"Archived: {stats.get('archived', 0)}\n"
                    f"Deleted: {stats.get('deleted', 0)}"
                )
                self.sidebar_progress_label.configure(text=stats_text)
        except Exception as e:
            pass  # Sidebar stats are optional

    def _show_results_in_main_window(self, parent, summary: Dict):
        """Show curation results in the MAIN WINDOW with large fonts."""
        FONT_HUGE = 28
        FONT_LARGE = 22
        FONT_MEDIUM = 18
        FONT_NORMAL = 16
        FONT_SMALL = 14

        # Clear the progress view
        for widget in parent.winfo_children():
            widget.destroy()

        # Scrollable results
        scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True)

        # Success header - HUGE
        header = ctk.CTkLabel(
            scroll,
            text="=" * 40 + "\n✓ CURATION COMPLETE\n" + "=" * 40,
            font=ctk.CTkFont(family="Courier", size=FONT_HUGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=20)

        # Duration and stats - LARGE
        duration = summary.get("duration_seconds", 0)
        duration_text = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"
        clusters = summary.get("clusters_processed", 0)

        ctk.CTkLabel(
            scroll,
            text=f"Time: {duration_text} | Memories: {summary.get('total_memories', 0)} | Clusters: {clusters}",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=10)

        # Actions summary - LARGE with visual stats
        actions_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=3,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        actions_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            actions_frame,
            text="📊 Session Results:",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        actions = summary.get("actions", {})
        kept = actions.get('kept', 0)
        summarized = actions.get('summarized', 0)
        archived = actions.get('archived', 0)
        deleted = actions.get('deleted', 0)
        total = kept + summarized + archived + deleted

        stats_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=10)

        for action, count, color, icon in [
            ("KEPT", kept, self.palette.get("user", "#D499B9"), "✓"),
            ("SUMMARIZED", summarized, self.palette.get("accent", "#4A9B9B"), "📝"),
            ("ARCHIVED", archived, self.palette.get("muted", "#9B7D54"), "📦"),
            ("DELETED", deleted, self.palette.get("system", "#C4A574"), "🗑")
        ]:
            frame = ctk.CTkFrame(stats_row, fg_color="transparent")
            frame.pack(side="left", expand=True)

            pct = round(count / max(total, 1) * 100)
            ctk.CTkLabel(
                frame,
                text=f"{icon} {action}\n{count} ({pct}%)",
                font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
                text_color=color,
                justify="center"
            ).pack()

        # Compression stats
        session_data = summary.get("session", {})
        if session_data.get("words_before", 0) > 0:
            compression = session_data.get("compression_ratio", 0)
            words_saved = session_data.get("words_before", 0) - session_data.get("words_after", 0)

            ctk.CTkLabel(
                actions_frame,
                text=f"Storage freed: {compression:.1f}% ({words_saved:,} words)",
                font=ctk.CTkFont(family="Courier", size=FONT_MEDIUM),
                text_color=self.palette.get("accent", "#4A9B9B")
            ).pack(pady=(10, 15))

        # the entity's patterns analysis
        patterns_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=3,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        patterns_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            patterns_frame,
            text="🎯 the entity's Curation Patterns:",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        examples = summary.get("examples", {})
        patterns_text = self._analyze_curation_patterns(examples)

        ctk.CTkLabel(
            patterns_frame,
            text=patterns_text,
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # Example decisions with full reasoning
        if any(examples.values()):
            examples_frame = ctk.CTkFrame(
                scroll,
                fg_color=self.palette.get("panel", "#2D1B3D"),
                corner_radius=0,
                border_width=2,
                border_color=self.palette.get("muted", "#9B7D54")
            )
            examples_frame.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(
                examples_frame,
                text="💭 Example Decisions (with the entity's reasoning):",
                font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            ).pack(anchor="w", padx=20, pady=(15, 10))

            for action_type, action_examples in examples.items():
                if not action_examples:
                    continue

                for i, ex in enumerate(action_examples[:3]):
                    preview = ex.get("preview", ex.get("original_preview", ""))[:100]
                    reasoning = ex.get("reasoning", "")
                    summary_text = ex.get("summary", "")

                    if action_type == "kept":
                        action_color = self.palette.get("user", "#D499B9")
                        action_icon = "✓"
                    elif action_type == "summarized":
                        action_color = self.palette.get("accent", "#4A9B9B")
                        action_icon = "📝"
                    elif action_type == "deleted":
                        action_color = self.palette.get("system", "#C4A574")
                        action_icon = "🗑"
                    else:
                        action_color = self.palette.get("muted", "#9B7D54")
                        action_icon = "📦"

                    ctk.CTkLabel(
                        examples_frame,
                        text=f"{action_icon} [{action_type.upper()}] \"{preview}...\"",
                        font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
                        text_color=action_color
                    ).pack(anchor="w", padx=25, pady=(10, 0))

                    if reasoning:
                        wrapped = self._wrap_text(reasoning, 75)
                        ctk.CTkLabel(
                            examples_frame,
                            text=f"  Entity: \"{wrapped}\"",
                            font=ctk.CTkFont(family="Courier", size=FONT_SMALL),
                            text_color=self.palette.get("text", "#E8DCC4"),
                            justify="left"
                        ).pack(anchor="w", padx=30, pady=(5, 0))

                    if action_type == "summarized" and summary_text:
                        ctk.CTkLabel(
                            examples_frame,
                            text="  the entity's summary:",
                            font=ctk.CTkFont(family="Courier", size=FONT_SMALL, weight="bold"),
                            text_color=self.palette.get("accent", "#4A9B9B")
                        ).pack(anchor="w", padx=30, pady=(8, 0))

                        wrapped_summary = self._wrap_text(summary_text, 70)
                        ctk.CTkLabel(
                            examples_frame,
                            text=f"  >> {wrapped_summary}",
                            font=ctk.CTkFont(family="Courier", size=FONT_SMALL),
                            text_color=self.palette.get("accent_hi", "#6BB6B6"),
                            justify="left"
                        ).pack(anchor="w", padx=35, pady=(3, 0))

                    ctk.CTkLabel(
                        examples_frame,
                        text="-" * 60,
                        font=ctk.CTkFont(family="Courier", size=10),
                        text_color=self.palette.get("muted", "#9B7D54")
                    ).pack(anchor="w", padx=25, pady=5)

            ctk.CTkLabel(examples_frame, text="").pack(pady=5)

        # Buttons - LARGE
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="◀ Back to Chat",
            command=self._finish_curation_and_restore_chat,
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=50
        ).pack(fill="x", pady=5)

    def _show_error_in_main_window(self, parent, error_message: str):
        """Show error in the main window."""
        FONT_LARGE = 22
        FONT_NORMAL = 16

        for widget in parent.winfo_children():
            widget.destroy()

        error_frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette.get("panel", "#2D1B3D")
        )
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            error_frame,
            text="⚠ Curation Error",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=30)

        ctk.CTkLabel(
            error_frame,
            text=error_message[:500],
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=700
        ).pack(pady=15)

        ctk.CTkButton(
            error_frame,
            text="◀ Back to Chat",
            command=self._finish_curation_and_restore_chat,
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=50
        ).pack(pady=30)

    def _finish_curation_and_restore_chat(self):
        """Finish curation and restore the chat view in main window."""
        # Restore chat in main area
        if hasattr(self.companion_ui, 'restore_chat_in_main_area'):
            self.companion_ui.restore_chat_in_main_area()

        # Restore sidebar to dashboard
        if hasattr(self, 'sidebar_parent'):
            self._show_dashboard(self.sidebar_parent)

        self.current_view = "dashboard"

    def _display_curation_in_main_panel(self, memories: List[Dict], parent):
        """
        Display curation session directly in the main panel (NOT in a modal/popup).

        This replaces the sidebar content with the curation session UI,
        displaying the entity's reasoning with large, readable fonts.
        """
        self.current_view = "curation"

        # Clear existing content in the parent panel
        for widget in parent.winfo_children():
            widget.destroy()

        # Store parent reference for later use
        self.curation_parent = parent

        # Create the progress panel directly in the main panel
        self._create_main_panel_progress(parent, len(memories))

        # Announce in main chat
        self._output_to_main_window(
            f"🧠 Starting curation session...\nReviewing {len(memories)} memories.",
            "system"
        )

        # Create autonomous processor with progress callback
        def update_progress(progress_data):
            self._update_main_panel_progress(progress_data)

        processor = AutonomousCurationProcessor(
            curator=self.curator,
            memory_engine=self.memory_engine,
            purge_reserve=self.purge_reserve,
            progress_callback=update_progress
        )

        # Run curation in background thread to keep UI responsive
        import threading

        def run_curation():
            try:
                summary = processor.run_curation_session(memories, cluster_size=5)

                # Update UI on main thread
                self.companion_ui.after(0, lambda: self._show_curation_results_in_main_panel(parent, summary))

                # Save memory engine changes
                if self.memory_engine and hasattr(self.memory_engine, '_save_to_disk'):
                    self.memory_engine._save_to_disk()
                    print("[CURATION] Memory changes saved to disk")

            except Exception as e:
                print(f"[CURATION] Error in autonomous session: {e}")
                import traceback
                traceback.print_exc()
                self.companion_ui.after(0, lambda: self._show_curation_error_in_main_panel(parent, str(e)))

        thread = threading.Thread(target=run_curation, daemon=True)
        thread.start()

    def _create_main_panel_progress(self, parent, total_memories: int):
        """
        Create the progress panel for curation with LARGE fonts.
        Displays directly in the main panel, not a popup.
        """
        # Large font sizes for readability
        FONT_HUGE = 24
        FONT_LARGE = 20
        FONT_MEDIUM = 18
        FONT_NORMAL = 16
        FONT_SMALL = 14

        # Store reference for updates
        self.main_progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.main_progress_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header - HUGE and prominent
        header = ctk.CTkLabel(
            self.main_progress_frame,
            text="=" * 30 + "\n🧠 KAY'S MEMORY CURATION\n" + "=" * 30,
            font=ctk.CTkFont(family="Courier", size=FONT_HUGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=15)

        # Status label - large
        self.main_status_label = ctk.CTkLabel(
            self.main_progress_frame,
            text=f"Reviewing {total_memories} memories...",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        self.main_status_label.pack(pady=10)

        # Progress bar - large
        self.main_progress_bar = ctk.CTkProgressBar(
            self.main_progress_frame,
            width=500,
            height=30,
            progress_color=self.palette.get("accent", "#4A9B9B"),
            fg_color=self.palette.get("input", "#4A2B5C")
        )
        self.main_progress_bar.pack(pady=15)
        self.main_progress_bar.set(0)

        # Cluster info - large
        self.main_cluster_label = ctk.CTkLabel(
            self.main_progress_frame,
            text="Clustering memories...",
            font=ctk.CTkFont(family="Courier", size=FONT_MEDIUM),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.main_cluster_label.pack(pady=5)

        # Decision log frame (scrollable) - LARGE for full reasoning display
        log_frame = ctk.CTkFrame(
            self.main_progress_frame,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=3,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        log_frame.pack(fill="both", expand=True, padx=5, pady=15)

        ctk.CTkLabel(
            log_frame,
            text="💭 the entity's Reasoning (Live):",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Scrollable decision log with LARGE font
        self.main_decision_log = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("input", "#4A2B5C"),
            text_color=self.palette.get("text", "#E8DCC4"),
            height=350,
            wrap="word"
        )
        self.main_decision_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Initial message
        self.main_decision_log.insert("end", "Waiting for the entity to start reviewing...\n\n")

        # Stats row - large
        stats_frame = ctk.CTkFrame(self.main_progress_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=5, pady=10)

        self.main_stats_labels = {}
        for action, color in [
            ("KEPT", self.palette.get("user", "#D499B9")),
            ("SUMMARIZED", self.palette.get("accent", "#4A9B9B")),
            ("ARCHIVED", self.palette.get("muted", "#9B7D54")),
            ("DELETED", self.palette.get("system", "#C4A574"))
        ]:
            frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            frame.pack(side="left", expand=True)

            self.main_stats_labels[action] = ctk.CTkLabel(
                frame,
                text=f"{action}: 0",
                font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
                text_color=color
            )
            self.main_stats_labels[action].pack()

    def _update_main_panel_progress(self, progress_data: Dict):
        """Update the main panel progress UI with the entity's full reasoning."""
        try:
            current = progress_data.get("current", 0)
            total = progress_data.get("total", 1)
            stats = progress_data.get("stats", {})
            latest_decisions = progress_data.get("latest_decisions", [])

            # Update progress bar
            progress = current / max(total, 1)
            self.main_progress_bar.set(progress)

            # Update cluster label
            self.main_cluster_label.configure(
                text=f"Cluster {current}/{total} - the entity is reviewing..."
            )

            # Update stats
            self.main_stats_labels["KEPT"].configure(text=f"KEPT: {stats.get('kept', 0)}")
            self.main_stats_labels["SUMMARIZED"].configure(text=f"SUMMARIZED: {stats.get('summarized', 0)}")
            self.main_stats_labels["ARCHIVED"].configure(text=f"ARCHIVED: {stats.get('archived', 0)}")
            self.main_stats_labels["DELETED"].configure(text=f"DELETED: {stats.get('deleted', 0)}")

            # Add cluster header to log
            if latest_decisions:
                cluster_header = f"\n{'='*50}\nCLUSTER {current}/{total} ({len(latest_decisions)} memories)\n{'='*50}\n\n"
                self.main_decision_log.insert("end", cluster_header)

            # Add decisions to log with FULL reasoning
            for decision in latest_decisions:
                action = decision.get("action", "unknown").upper()
                preview = decision.get("memory", {}).get("content", "")[:100]
                reasoning = decision.get("reasoning", "")
                summary = decision.get("summary", "")
                kay_override = decision.get("kay_override", False)

                # Action indicator
                if action == "KEEP":
                    action_icon = "✓ [KEEP]"
                elif action == "SUMMARIZE":
                    action_icon = "📝 [SUMMARIZE]"
                elif action == "ARCHIVE":
                    action_icon = "📦 [ARCHIVE]"
                elif action == "DELETE":
                    action_icon = "🗑 [DELETE]"
                else:
                    action_icon = f"[{action}]"

                # Build detailed log entry
                log_entry = f"{action_icon}\n"
                log_entry += f"  Memory: \"{preview}...\"\n"

                # Show the entity's full reasoning
                if reasoning:
                    wrapped_reasoning = self._wrap_text(reasoning, 70)
                    log_entry += f"\n  the entity's reasoning:\n"
                    for line in wrapped_reasoning.split('\n'):
                        log_entry += f"    {line}\n"

                # Show the entity's summary if action was SUMMARIZE
                if action == "SUMMARIZE" and summary:
                    wrapped_summary = self._wrap_text(summary, 70)
                    log_entry += f"\n  the entity's summary:\n"
                    for line in wrapped_summary.split('\n'):
                        log_entry += f"    >> {line}\n"

                # Note if the entity overrode the classifier
                if kay_override:
                    log_entry += f"  [the entity overrode classifier suggestion]\n"

                log_entry += "\n" + "-"*50 + "\n"

                self.main_decision_log.insert("end", log_entry)
                self.main_decision_log.see("end")

            # Update status
            if current < total:
                self.main_status_label.configure(
                    text=f"the entity reviewed cluster {current}/{total}... waiting for next cluster"
                )
            else:
                self.main_status_label.configure(
                    text=f"the entity has reviewed all {total} clusters. Applying decisions..."
                )

            # Force UI update
            self.main_progress_frame.update_idletasks()

        except Exception as e:
            print(f"[CURATION UI] Progress update error: {e}")
            import traceback
            traceback.print_exc()

    def _show_curation_results_in_main_panel(self, parent, summary: Dict):
        """Show curation results directly in the main panel with large fonts."""
        # Large font sizes
        FONT_HUGE = 24
        FONT_LARGE = 20
        FONT_MEDIUM = 18
        FONT_NORMAL = 16
        FONT_SMALL = 14

        # Clear the progress panel
        for widget in parent.winfo_children():
            widget.destroy()

        # Create scrollable results - ALL IN ONE VIEW
        results_scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B"),
            scrollbar_button_hover_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        results_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ========================================
        # SUCCESS HEADER - HUGE
        # ========================================
        header = ctk.CTkLabel(
            results_scroll,
            text="=" * 30 + "\n✓ CURATION COMPLETE\n" + "=" * 30,
            font=ctk.CTkFont(family="Courier", size=FONT_HUGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=15)

        # Duration and stats - large
        duration = summary.get("duration_seconds", 0)
        duration_text = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"
        clusters = summary.get("clusters_processed", 0)

        ctk.CTkLabel(
            results_scroll,
            text=f"Time: {duration_text} | Memories: {summary.get('total_memories', 0)} | Clusters: {clusters}",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=10)

        # ========================================
        # ACTIONS SUMMARY with visual stats
        # ========================================
        actions_frame = ctk.CTkFrame(
            results_scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=3,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        actions_frame.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            actions_frame,
            text="📊 Session Results:",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        actions = summary.get("actions", {})
        kept = actions.get('kept', 0)
        summarized = actions.get('summarized', 0)
        archived = actions.get('archived', 0)
        deleted = actions.get('deleted', 0)
        total = kept + summarized + archived + deleted

        # Stats row - LARGE
        stats_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=15, pady=10)

        for action, count, color, icon in [
            ("KEPT", kept, self.palette.get("user", "#D499B9"), "✓"),
            ("SUMMARIZED", summarized, self.palette.get("accent", "#4A9B9B"), "📝"),
            ("ARCHIVED", archived, self.palette.get("muted", "#9B7D54"), "📦"),
            ("DELETED", deleted, self.palette.get("system", "#C4A574"), "🗑")
        ]:
            frame = ctk.CTkFrame(stats_row, fg_color="transparent")
            frame.pack(side="left", expand=True)

            pct = round(count / max(total, 1) * 100)
            ctk.CTkLabel(
                frame,
                text=f"{icon} {action}\n{count} ({pct}%)",
                font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
                text_color=color,
                justify="center"
            ).pack()

        # Compression stats - large
        session_data = summary.get("session", {})
        if session_data.get("words_before", 0) > 0:
            compression = session_data.get("compression_ratio", 0)
            words_saved = session_data.get("words_before", 0) - session_data.get("words_after", 0)

            ctk.CTkLabel(
                actions_frame,
                text=f"Storage freed: {compression:.1f}% ({words_saved:,} words)",
                font=ctk.CTkFont(family="Courier", size=FONT_MEDIUM),
                text_color=self.palette.get("accent", "#4A9B9B")
            ).pack(pady=(10, 15))

        # ========================================
        # KAY'S PATTERNS ANALYSIS
        # ========================================
        patterns_frame = ctk.CTkFrame(
            results_scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=3,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        patterns_frame.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            patterns_frame,
            text="🎯 the entity's Curation Patterns:",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Analyze patterns from examples
        examples = summary.get("examples", {})
        patterns_text = self._analyze_curation_patterns(examples)

        ctk.CTkLabel(
            patterns_frame,
            text=patterns_text,
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # ========================================
        # DETAILED EXAMPLES with full reasoning - ALL EXPANDED
        # ========================================
        if any(examples.values()):
            examples_frame = ctk.CTkFrame(
                results_scroll,
                fg_color=self.palette.get("panel", "#2D1B3D"),
                corner_radius=0,
                border_width=2,
                border_color=self.palette.get("muted", "#9B7D54")
            )
            examples_frame.pack(fill="x", padx=10, pady=15)

            ctk.CTkLabel(
                examples_frame,
                text="💭 Example Decisions (with the entity's reasoning):",
                font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            ).pack(anchor="w", padx=15, pady=(15, 10))

            # Show ALL examples with FULL reasoning - not hidden in expanders
            for action_type, action_examples in examples.items():
                if not action_examples:
                    continue

                for i, ex in enumerate(action_examples[:3]):  # Show up to 3 per type
                    preview = ex.get("preview", ex.get("original_preview", ""))[:80]
                    reasoning = ex.get("reasoning", "")
                    summary_text = ex.get("summary", "")

                    # Action header with color
                    if action_type == "kept":
                        action_color = self.palette.get("user", "#D499B9")
                        action_icon = "✓"
                    elif action_type == "summarized":
                        action_color = self.palette.get("accent", "#4A9B9B")
                        action_icon = "📝"
                    elif action_type == "deleted":
                        action_color = self.palette.get("system", "#C4A574")
                        action_icon = "🗑"
                    else:
                        action_color = self.palette.get("muted", "#9B7D54")
                        action_icon = "📦"

                    # Memory preview - LARGE
                    ctk.CTkLabel(
                        examples_frame,
                        text=f"{action_icon} [{action_type.upper()}] \"{preview}...\"",
                        font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
                        text_color=action_color
                    ).pack(anchor="w", padx=20, pady=(10, 0))

                    # Full reasoning - LARGE and visible
                    if reasoning:
                        wrapped = self._wrap_text(reasoning, 65)
                        ctk.CTkLabel(
                            examples_frame,
                            text=f"  Entity: \"{wrapped}\"",
                            font=ctk.CTkFont(family="Courier", size=FONT_SMALL),
                            text_color=self.palette.get("text", "#E8DCC4"),
                            justify="left"
                        ).pack(anchor="w", padx=25, pady=(5, 0))

                    # Show summary if action was summarize
                    if action_type == "summarized" and summary_text:
                        ctk.CTkLabel(
                            examples_frame,
                            text="  the entity's summary:",
                            font=ctk.CTkFont(family="Courier", size=FONT_SMALL, weight="bold"),
                            text_color=self.palette.get("accent", "#4A9B9B")
                        ).pack(anchor="w", padx=25, pady=(8, 0))

                        wrapped_summary = self._wrap_text(summary_text, 60)
                        ctk.CTkLabel(
                            examples_frame,
                            text=f"  >> {wrapped_summary}",
                            font=ctk.CTkFont(family="Courier", size=FONT_SMALL),
                            text_color=self.palette.get("accent_hi", "#6BB6B6"),
                            justify="left"
                        ).pack(anchor="w", padx=30, pady=(3, 0))

                    # Separator between examples
                    ctk.CTkLabel(
                        examples_frame,
                        text="-" * 50,
                        font=ctk.CTkFont(family="Courier", size=10),
                        text_color=self.palette.get("muted", "#9B7D54")
                    ).pack(anchor="w", padx=20, pady=5)

            ctk.CTkLabel(examples_frame, text="").pack(pady=5)

        # ========================================
        # BUTTONS - LARGE
        # ========================================
        btn_frame = ctk.CTkFrame(results_scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="🗑 View Purge Reserve",
            command=lambda: self._show_purge_reserve_list(parent),
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("system", "#C4A574"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=45
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            btn_frame,
            text="◀ Back to Dashboard",
            command=lambda: self._show_dashboard(parent),
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=50
        ).pack(fill="x", pady=5)

        # Output completion to main chat
        completion_msg = (
            f"✓ Curation complete! ({duration_text})\n"
            f"📊 Results: {kept} kept, {summarized} summarized, {archived} archived, {deleted} deleted"
        )
        self._output_to_main_window(completion_msg, "system")

    def _show_curation_error_in_main_panel(self, parent, error_message: str):
        """Show error in the main panel (not a popup)."""
        FONT_LARGE = 20
        FONT_NORMAL = 16

        # Clear existing content
        for widget in parent.winfo_children():
            widget.destroy()

        error_frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette.get("panel", "#2D1B3D")
        )
        error_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            error_frame,
            text="⚠ Curation Error",
            font=ctk.CTkFont(family="Courier", size=FONT_LARGE, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=30)

        ctk.CTkLabel(
            error_frame,
            text=error_message[:400],
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=700
        ).pack(pady=15)

        ctk.CTkButton(
            error_frame,
            text="◀ Back to Dashboard",
            command=lambda: self._show_dashboard(parent),
            font=ctk.CTkFont(family="Courier", size=FONT_NORMAL),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=45
        ).pack(pady=30)

        self._output_to_main_window(f"⚠ Curation error: {error_message[:100]}...", "system")

    def _open_curation_main_window(self, memories: List[Dict], sidebar_parent):
        """
        DEPRECATED: This method opens a modal popup.
        Use _display_curation_in_main_panel instead.

        Kept for backwards compatibility but no longer called.
        """
        # Create toplevel window
        self.curation_window = ctk.CTkToplevel(self.companion_ui)
        self.curation_window.title("🧠 the entity's Memory Curation Session")
        self.curation_window.geometry("900x700")
        self.curation_window.transient(self.companion_ui)  # Keep on top of main window

        # Center on screen
        self.curation_window.update_idletasks()
        x = (self.curation_window.winfo_screenwidth() - 900) // 2
        y = (self.curation_window.winfo_screenheight() - 700) // 2
        self.curation_window.geometry(f"900x700+{x}+{y}")

        # Apply palette
        self.curation_window.configure(fg_color=self.palette.get("bg", "#1A0F24"))

        # Create main container
        main_container = ctk.CTkFrame(
            self.curation_window,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0
        )
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Create the progress panel inside the main window
        self._create_progress_panel(main_container, len(memories))

        # Announce in main chat
        self._output_to_main_window(
            f"🧠 Opening curation session window...\nReviewing {len(memories)} memories.",
            "system"
        )

        # Create autonomous processor with progress callback
        def update_progress(progress_data):
            self._update_progress_ui(progress_data)

        processor = AutonomousCurationProcessor(
            curator=self.curator,
            memory_engine=self.memory_engine,
            purge_reserve=self.purge_reserve,
            progress_callback=update_progress
        )

        # Run curation in background thread to keep UI responsive
        import threading

        def run_curation():
            try:
                summary = processor.run_curation_session(memories, cluster_size=5)

                # Update UI on main thread
                self.companion_ui.after(0, lambda: self._show_curation_results_in_main_window(summary))

                # Save memory engine changes
                if self.memory_engine and hasattr(self.memory_engine, '_save_to_disk'):
                    self.memory_engine._save_to_disk()
                    print("[CURATION] Memory changes saved to disk")

            except Exception as e:
                print(f"[CURATION] Error in autonomous session: {e}")
                import traceback
                traceback.print_exc()
                self.companion_ui.after(0, lambda: self._show_curation_error_in_main_window(str(e)))

        thread = threading.Thread(target=run_curation, daemon=True)
        thread.start()

    def _show_curation_results_in_main_window(self, summary: Dict):
        """Show curation results in the main curation window."""
        if not hasattr(self, 'curation_window') or not self.curation_window.winfo_exists():
            return

        # Clear the progress panel
        for widget in self.curation_window.winfo_children():
            widget.destroy()

        # Create scrollable results
        results_scroll = ctk.CTkScrollableFrame(
            self.curation_window,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        results_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Use the existing results display logic
        self._show_curation_results(results_scroll, summary)

        # Add close button at the bottom
        close_btn = ctk.CTkButton(
            self.curation_window,
            text="✓ Close Curation Window",
            command=self.curation_window.destroy,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium']),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            corner_radius=0,
            height=40
        )
        close_btn.pack(fill="x", padx=10, pady=(0, 10))

        # Output completion to main chat
        actions = summary.get("actions", {})
        kept = actions.get('kept', 0)
        summarized = actions.get('summarized', 0)
        archived = actions.get('archived', 0)
        deleted = actions.get('deleted', 0)
        duration = summary.get("duration_seconds", 0)
        duration_text = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"

        completion_msg = (
            f"✓ Curation complete! ({duration_text})\n"
            f"📊 Results: {kept} kept, {summarized} summarized, {archived} archived, {deleted} deleted"
        )
        self._output_to_main_window(completion_msg, "system")

    def _show_curation_error_in_main_window(self, error_message: str):
        """Show error in the main curation window."""
        if not hasattr(self, 'curation_window') or not self.curation_window.winfo_exists():
            return

        # Clear the progress panel
        for widget in self.curation_window.winfo_children():
            widget.destroy()

        error_frame = ctk.CTkFrame(
            self.curation_window,
            fg_color=self.palette.get("panel", "#2D1B3D")
        )
        error_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            error_frame,
            text="⚠ Curation Error",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['header'], weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=20)

        ctk.CTkLabel(
            error_frame,
            text=error_message[:300],
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=600
        ).pack(pady=10)

        ctk.CTkButton(
            error_frame,
            text="Close",
            command=self.curation_window.destroy,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=35
        ).pack(pady=20)

        self._output_to_main_window(f"⚠ Curation error: {error_message[:100]}...", "system")

    def _create_progress_panel(self, parent, total_memories: int):
        """Create the progress panel for autonomous curation with larger fonts."""
        # Store reference for updates
        self.progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.progress_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Header - LARGE and prominent
        header = ctk.CTkLabel(
            self.progress_frame,
            text="=" * 25 + "\n🧠 KAY IS CURATING\n" + "=" * 25,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['header'], weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Status label - larger
        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text=f"Reviewing {total_memories} memories...",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium']),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        self.status_label.pack(pady=5)

        # Progress bar - larger
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=400,
            height=25,
            progress_color=self.palette.get("accent", "#4A9B9B"),
            fg_color=self.palette.get("input", "#4A2B5C")
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # Cluster info - larger
        self.cluster_label = ctk.CTkLabel(
            self.progress_frame,
            text="Clustering memories...",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.cluster_label.pack(pady=5)

        # Decision log frame (scrollable) - LARGE for full reasoning display
        log_frame = ctk.CTkFrame(
            self.progress_frame,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=2,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        log_frame.pack(fill="both", expand=True, padx=5, pady=10)

        ctk.CTkLabel(
            log_frame,
            text="💭 the entity's Reasoning (Live):",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium'], weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Larger scrollable decision log for full reasoning - MUCH LARGER FONT
        self.decision_log = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            fg_color=self.palette.get("input", "#4A2B5C"),
            text_color=self.palette.get("text", "#E8DCC4"),
            height=400,  # Much larger to show full reasoning
            wrap="word"
        )
        self.decision_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Initial message
        self.decision_log.insert("end", "Waiting for the entity to start reviewing...\n\n")

        # Stats row - larger
        stats_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=5, pady=5)

        self.stats_labels = {}
        for action, color in [
            ("KEPT", self.palette.get("user", "#D499B9")),
            ("SUMMARIZED", self.palette.get("accent", "#4A9B9B")),
            ("ARCHIVED", self.palette.get("muted", "#9B7D54")),
            ("DELETED", self.palette.get("system", "#C4A574"))
        ]:
            frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            frame.pack(side="left", expand=True)

            self.stats_labels[action] = ctk.CTkLabel(
                frame,
                text=f"{action}: 0",
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium'], weight="bold"),
                text_color=color
            )
            self.stats_labels[action].pack()

    def _update_progress_ui(self, progress_data: Dict):
        """Update the progress UI with latest curation data including the entity's full reasoning."""
        try:
            current = progress_data.get("current", 0)
            total = progress_data.get("total", 1)
            stats = progress_data.get("stats", {})
            latest_decisions = progress_data.get("latest_decisions", [])

            # Also output key decisions to main window (summarized)
            if self.display_in_main_window and latest_decisions:
                for decision in latest_decisions[:2]:  # Show first 2 decisions per cluster
                    action = decision.get("action", "unknown").upper()
                    preview = decision.get("memory", {}).get("content", "")[:50]
                    reasoning = decision.get("reasoning", "")[:100]

                    # Only output if there's meaningful reasoning
                    if reasoning:
                        summary_msg = f"[{action}] \"{preview}...\"\n→ {reasoning}..."
                        self._output_to_main_window(summary_msg, "entity")

            # Update progress bar
            progress = current / max(total, 1)
            self.progress_bar.set(progress)

            # Update cluster label with more detail
            self.cluster_label.configure(
                text=f"Cluster {current}/{total} - the entity is reviewing..."
            )

            # Update stats
            self.stats_labels["KEPT"].configure(text=f"KEPT: {stats.get('kept', 0)}")
            self.stats_labels["SUMMARIZED"].configure(text=f"SUMMARIZED: {stats.get('summarized', 0)}")
            self.stats_labels["ARCHIVED"].configure(text=f"ARCHIVED: {stats.get('archived', 0)}")
            self.stats_labels["DELETED"].configure(text=f"DELETED: {stats.get('deleted', 0)}")

            # Add cluster header to log
            if latest_decisions:
                cluster_header = f"\n{'='*40}\nCLUSTER {current}/{total} ({len(latest_decisions)} memories)\n{'='*40}\n\n"
                self.decision_log.insert("end", cluster_header)

            # Add decisions to log with FULL reasoning
            for decision in latest_decisions:
                action = decision.get("action", "unknown").upper()
                preview = decision.get("memory", {}).get("content", "")[:80]
                reasoning = decision.get("reasoning", "")  # FULL reasoning, not truncated
                summary = decision.get("summary", "")
                kay_override = decision.get("kay_override", False)

                # Action indicator with visual distinction
                if action == "KEEP":
                    action_display = "[KEEP]    "
                    action_icon = "+"
                elif action == "SUMMARIZE":
                    action_display = "[SUMMARIZE]"
                    action_icon = "~"
                elif action == "ARCHIVE":
                    action_display = "[ARCHIVE] "
                    action_icon = ">"
                elif action == "DELETE":
                    action_display = "[DELETE]  "
                    action_icon = "x"
                else:
                    action_display = f"[{action}]"
                    action_icon = "?"

                # Build detailed log entry
                log_entry = f"{action_icon} {action_display}\n"
                log_entry += f"  Memory: \"{preview}...\"\n"

                # Show the entity's full reasoning
                if reasoning:
                    # Word wrap reasoning for readability
                    wrapped_reasoning = self._wrap_text(reasoning, 60)
                    log_entry += f"  \n  the entity's reasoning:\n"
                    for line in wrapped_reasoning.split('\n'):
                        log_entry += f"    {line}\n"

                # Show the entity's summary if action was SUMMARIZE
                if action == "SUMMARIZE" and summary:
                    wrapped_summary = self._wrap_text(summary, 60)
                    log_entry += f"  \n  the entity's summary:\n"
                    for line in wrapped_summary.split('\n'):
                        log_entry += f"    >> {line}\n"

                # Note if the entity overrode the classifier
                if kay_override:
                    log_entry += f"  [the entity overrode classifier suggestion]\n"

                log_entry += "\n" + "-"*40 + "\n"

                self.decision_log.insert("end", log_entry)
                self.decision_log.see("end")

            # Update status to show we're waiting for the entity
            if current < total:
                self.status_label.configure(
                    text=f"the entity reviewed cluster {current}/{total}... waiting for next cluster"
                )
            else:
                self.status_label.configure(
                    text=f"the entity has reviewed all {total} clusters. Applying decisions..."
                )

            # Force UI update
            self.progress_frame.update_idletasks()

        except Exception as e:
            print(f"[CURATION UI] Progress update error: {e}")
            import traceback
            traceback.print_exc()

    def _wrap_text(self, text: str, width: int) -> str:
        """Wrap text to specified width for display."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def _show_curation_results(self, parent, summary: Dict):
        """Show the curation session results with the entity's patterns and full reasoning."""
        # Output summary to main window
        actions = summary.get("actions", {})
        kept = actions.get('kept', 0)
        summarized = actions.get('summarized', 0)
        archived = actions.get('archived', 0)
        deleted = actions.get('deleted', 0)
        duration = summary.get("duration_seconds", 0)
        duration_text = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"

        completion_msg = (
            f"✓ Curation complete! ({duration_text})\n"
            f"📊 Results: {kept} kept, {summarized} summarized, {archived} archived, {deleted} deleted\n"
            f"See sidebar for detailed patterns and examples."
        )
        self._output_to_main_window(completion_msg, "system")

        # Clear progress panel
        for widget in parent.winfo_children():
            widget.destroy()

        # Scrollable results panel
        results_scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        results_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Success header - LARGER
        header = ctk.CTkLabel(
            results_scroll,
            text="=" * 25 + "\n✓ CURATION COMPLETE\n" + "=" * 25,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['header'], weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Duration and stats - larger
        duration = summary.get("duration_seconds", 0)
        duration_text = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"
        clusters = summary.get("clusters_processed", 0)

        ctk.CTkLabel(
            results_scroll,
            text=f"Time: {duration_text} | Memories: {summary.get('total_memories', 0)} | Clusters: {clusters}",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium']),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=5)

        # ========================================
        # ACTIONS SUMMARY with visual stats
        # ========================================
        actions_frame = ctk.CTkFrame(
            results_scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=2,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        actions_frame.pack(fill="x", padx=5, pady=10)

        ctk.CTkLabel(
            actions_frame,
            text="📊 Session Results:",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium'], weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        actions = summary.get("actions", {})
        kept = actions.get('kept', 0)
        summarized = actions.get('summarized', 0)
        archived = actions.get('archived', 0)
        deleted = actions.get('deleted', 0)
        total = kept + summarized + archived + deleted

        # Stats row - LARGER
        stats_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=10, pady=5)

        for action, count, color, icon in [
            ("KEPT", kept, self.palette.get("user", "#D499B9"), "✓"),
            ("SUMMARIZED", summarized, self.palette.get("accent", "#4A9B9B"), "📝"),
            ("ARCHIVED", archived, self.palette.get("muted", "#9B7D54"), "📦"),
            ("DELETED", deleted, self.palette.get("system", "#C4A574"), "🗑")
        ]:
            frame = ctk.CTkFrame(stats_row, fg_color="transparent")
            frame.pack(side="left", expand=True)

            pct = round(count / max(total, 1) * 100)
            ctk.CTkLabel(
                frame,
                text=f"{icon} {action}\n{count} ({pct}%)",
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium'], weight="bold"),
                text_color=color,
                justify="center"
            ).pack()

        # Compression stats - larger
        session_data = summary.get("session", {})
        if session_data.get("words_before", 0) > 0:
            compression = session_data.get("compression_ratio", 0)
            words_saved = session_data.get("words_before", 0) - session_data.get("words_after", 0)

            ctk.CTkLabel(
                actions_frame,
                text=f"Storage freed: {compression:.1f}% ({words_saved:,} words)",
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
                text_color=self.palette.get("accent", "#4A9B9B")
            ).pack(pady=(5, 10))

        # ========================================
        # KAY'S PATTERNS ANALYSIS
        # ========================================
        patterns_frame = ctk.CTkFrame(
            results_scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=2,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        patterns_frame.pack(fill="x", padx=5, pady=10)

        ctk.CTkLabel(
            patterns_frame,
            text="🎯 the entity's Curation Patterns:",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium'], weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Analyze patterns from examples
        examples = summary.get("examples", {})
        patterns_text = self._analyze_curation_patterns(examples)

        ctk.CTkLabel(
            patterns_frame,
            text=patterns_text,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # ========================================
        # DETAILED EXAMPLES with full reasoning
        # ========================================
        if any(examples.values()):
            examples_frame = ctk.CTkFrame(
                results_scroll,
                fg_color=self.palette.get("panel", "#2D1B3D"),
                corner_radius=0,
                border_width=1,
                border_color=self.palette.get("muted", "#9B7D54")
            )
            examples_frame.pack(fill="x", padx=5, pady=10)

            ctk.CTkLabel(
                examples_frame,
                text="💭 Example Decisions (with the entity's reasoning):",
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['medium'], weight="bold"),
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            ).pack(anchor="w", padx=10, pady=(10, 5))

            # Show examples with FULL reasoning
            for action_type, action_examples in examples.items():
                if not action_examples:
                    continue

                for i, ex in enumerate(action_examples[:2]):  # Show up to 2 per type
                    preview = ex.get("preview", ex.get("original_preview", ""))[:60]
                    reasoning = ex.get("reasoning", "")
                    summary_text = ex.get("summary", "")

                    # Action header with color
                    if action_type == "kept":
                        action_color = self.palette.get("user", "#D499B9")
                        action_icon = "✓"
                    elif action_type == "summarized":
                        action_color = self.palette.get("accent", "#4A9B9B")
                        action_icon = "📝"
                    elif action_type == "deleted":
                        action_color = self.palette.get("system", "#C4A574")
                        action_icon = "🗑"
                    else:
                        action_color = self.palette.get("muted", "#9B7D54")
                        action_icon = "📦"

                    # Memory preview - larger
                    ctk.CTkLabel(
                        examples_frame,
                        text=f"{action_icon} [{action_type.upper()}] \"{preview}...\"",
                        font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
                        text_color=action_color
                    ).pack(anchor="w", padx=15, pady=(5, 0))

                    # Full reasoning - larger
                    if reasoning:
                        wrapped = self._wrap_text(reasoning, 55)
                        ctk.CTkLabel(
                            examples_frame,
                            text=f"  Entity: \"{wrapped}\"",
                            font=ctk.CTkFont(family="Courier", size=self.font_sizes['small']),
                            text_color=self.palette.get("text", "#E8DCC4"),
                            justify="left"
                        ).pack(anchor="w", padx=20, pady=(2, 0))

                    # Show summary if action was summarize
                    if action_type == "summarized" and summary_text:
                        ctk.CTkLabel(
                            examples_frame,
                            text="  the entity's summary:",
                            font=ctk.CTkFont(family="Courier", size=self.font_sizes['small'], weight="bold"),
                            text_color=self.palette.get("accent", "#4A9B9B")
                        ).pack(anchor="w", padx=20, pady=(5, 0))

                        wrapped_summary = self._wrap_text(summary_text, 50)
                        ctk.CTkLabel(
                            examples_frame,
                            text=f"  >> {wrapped_summary}",
                            font=ctk.CTkFont(family="Courier", size=self.font_sizes['small']),
                            text_color=self.palette.get("accent_hi", "#6BB6B6"),
                            justify="left"
                        ).pack(anchor="w", padx=25, pady=(2, 5))

                    # Separator between examples
                    ctk.CTkLabel(
                        examples_frame,
                        text="-" * 40,
                        font=ctk.CTkFont(family="Courier", size=self.font_sizes['tiny']),
                        text_color=self.palette.get("muted", "#9B7D54")
                    ).pack(anchor="w", padx=15, pady=2)

            ctk.CTkLabel(examples_frame, text="").pack(pady=3)

        # ========================================
        # BUTTONS - larger
        # ========================================
        btn_frame = ctk.CTkFrame(results_scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="🗑 View Purge Reserve",
            command=lambda: self._show_purge_reserve_list(parent),
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            fg_color=self.palette.get("system", "#C4A574"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=35
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            btn_frame,
            text="◀ Back to Dashboard",
            command=lambda: self._show_dashboard(parent),
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=38
        ).pack(fill="x", pady=2)

    def _analyze_curation_patterns(self, examples: Dict) -> str:
        """Analyze the entity's curation patterns from the examples."""
        patterns = []

        # Analyze what the entity kept
        kept = examples.get("kept", [])
        if kept:
            kept_reasons = [e.get("reasoning", "").lower() for e in kept]
            patterns.append("the entity tends to KEEP:")
            if any("yurt" in r or "wizard" in r or "creative" in r for r in kept_reasons):
                patterns.append("  + Creative/Yurt Wizards content")
            if any("relationship" in r or "identity" in r for r in kept_reasons):
                patterns.append("  + Relationship-defining moments")
            if any("mythology" in r or "story" in r for r in kept_reasons):
                patterns.append("  + Mythology and worldbuilding")
            if any("sacred" in r or "important" in r for r in kept_reasons):
                patterns.append("  + Sacred text markers")

        # Analyze what the entity summarized
        summarized = examples.get("summarized", [])
        if summarized:
            patterns.append("\nthe entity tends to SUMMARIZE:")
            summ_reasons = [e.get("reasoning", "").lower() for e in summarized]
            if any("technical" in r or "architecture" in r for r in summ_reasons):
                patterns.append("  ~ Technical discussions")
            if any("debug" in r or "fix" in r for r in summ_reasons):
                patterns.append("  ~ Debugging sessions (keeps resolution)")
            if any("process" in r or "verbose" in r for r in summ_reasons):
                patterns.append("  ~ Process details (keeps outcomes)")

        # Analyze what the entity deleted
        deleted = examples.get("deleted", [])
        if deleted:
            patterns.append("\nthe entity tends to DELETE:")
            del_reasons = [e.get("reasoning", "").lower() for e in deleted]
            if any("continue reading" in r or "prompt" in r for r in del_reasons):
                patterns.append("  x Standalone prompts without context")
            if any("ephemeral" in r or "one-off" in r for r in del_reasons):
                patterns.append("  x Ephemeral utility queries")
            if any("duplicate" in r or "redundant" in r for r in del_reasons):
                patterns.append("  x Redundant information")
            if any("noise" in r or "no lasting" in r for r in del_reasons):
                patterns.append("  x Noise without substance")

        if not patterns:
            return "Analyzing the entity's patterns..."

        return "\n".join(patterns)

    def _show_curation_error(self, parent, error_message: str):
        """Show error message if curation fails."""
        for widget in parent.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            parent,
            text="Curation Error",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=20)

        ctk.CTkLabel(
            parent,
            text=error_message[:200],
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=300
        ).pack(pady=10)

        ctk.CTkButton(
            parent,
            text="<- Back to Dashboard",
            command=lambda: self._show_dashboard(parent),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        ).pack(pady=20)

    def _get_memories_for_curation(self, limit: int = 75):
        """
        Get memories that need curation, formatted for the curation system.

        The memory engine stores memories with various fields (user_input, response,
        fact, etc.) but the curation system expects a 'content' field. This method
        normalizes the memory format and filters to uncurated memories.

        Args:
            limit: Maximum number of memories to return (oldest first)

        Returns:
            List of memory dicts with normalized 'content' and 'id' fields
        """
        if not self.memory_engine:
            print("[CURATION] No memory engine available")
            return []

        raw_memories = []

        # Get from memory engine
        if hasattr(self.memory_engine, 'memories'):
            raw_memories = list(self.memory_engine.memories)

        print(f"[CURATION DEBUG] Raw memories from engine: {len(raw_memories)}")

        if not raw_memories:
            return []

        # Normalize memories for curation format
        normalized = []
        for mem in raw_memories:
            # Skip already curated memories
            if mem.get('curated'):
                continue

            # Skip corrupted memories
            if mem.get('corrupted'):
                continue

            # Determine content based on memory type
            content = None
            mem_type = mem.get('type', 'unknown')

            if mem_type == 'full_turn':
                # Full conversation turns - combine user input and response
                user_input = mem.get('user_input', '')
                response = mem.get('response', '')
                if user_input or response:
                    content = f"User: {user_input}\nEntity: {response}" if response else user_input
            elif mem_type == 'extracted_fact':
                # Extracted facts - use the fact field
                content = mem.get('fact', '')
            elif mem_type == 'emotional_narrative':
                # Emotional narratives
                content = mem.get('fact', '') or mem.get('user_input', '')
            elif mem_type == 'glyph_summary':
                # Glyph summaries
                content = mem.get('fact', '')
            else:
                # Fallback: try various content fields
                content = (
                    mem.get('content') or
                    mem.get('fact') or
                    mem.get('user_input') or
                    mem.get('response') or
                    ''
                )

            # Skip empty content
            if not content or not content.strip():
                continue

            # Create normalized memory dict
            normalized_mem = {
                'id': mem.get('memory_id') or mem.get('id') or str(hash(content[:100])),
                'content': content.strip(),
                'type': mem_type,
                'metadata': {
                    'perspective': mem.get('perspective'),
                    'importance_score': mem.get('importance_score'),
                    'entities': mem.get('entities', []),
                    'emotion_tags': mem.get('emotion_tags', []),
                    'timestamp': mem.get('timestamp') or mem.get('added_timestamp'),
                    'turn_number': mem.get('turn_number') or mem.get('parent_turn'),
                    'source': mem.get('source_file') or mem_type,
                },
                # Preserve original for later operations
                '_original': mem
            }

            normalized.append(normalized_mem)

        print(f"[CURATION DEBUG] Normalized memories: {len(normalized)}")

        # Sort by timestamp/turn (oldest first for curation)
        def get_sort_key(m):
            ts = m['metadata'].get('timestamp') or m['metadata'].get('turn_number') or 0
            if isinstance(ts, str):
                return ts
            return str(ts)

        normalized.sort(key=get_sort_key)

        # Limit results
        result = normalized[:limit]
        print(f"[CURATION DEBUG] Returning {len(result)} memories for curation (limit={limit})")

        return result

    def _show_no_memories_message(self, parent):
        """Show message when no memories available for curation."""
        for widget in parent.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            parent,
            text="No Memories to Curate",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=20)

        ctk.CTkLabel(
            parent,
            text="Have some conversations first\nto build up memories for curation.",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54"),
            justify="center"
        ).pack(pady=10)

        ctk.CTkButton(
            parent,
            text="← Back to Dashboard",
            command=lambda: self._show_dashboard(parent),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        ).pack(pady=20)

    def _handle_decision(self, decision: Dict):
        """Handle a curation decision from the session panel."""
        memory = decision["memory"]
        classification = decision["classification"]
        action = decision["action"]
        compressed_content = decision.get("compressed_content")
        kay_override = decision.get("kay_override", False)

        # Apply the decision
        self.curator.apply_decision(
            memory=memory,
            classification=classification,
            action=action,
            compressed_content=compressed_content,
            kay_override=kay_override
        )

        # Record for learning if it was an override
        if kay_override:
            # Determine what the entity classified it as based on action
            if action == "keep_verbatim":
                kay_type = ContentType.SACRED_TEXT
            elif action == "delete":
                kay_type = ContentType.EPHEMERAL_UTILITY
            else:
                kay_type = ContentType.FUNCTIONAL_KNOWLEDGE

            self.learning_tracker.record_classification_result(
                original_type=classification.content_type,
                kay_type=kay_type,
                content_preview=memory.get("content", "")[:100],
                was_correct=False  # Override means classifier was wrong
            )
        else:
            # Classifier was correct
            self.learning_tracker.record_classification_result(
                original_type=classification.content_type,
                kay_type=classification.content_type,
                content_preview=memory.get("content", "")[:100],
                was_correct=True
            )

        # Apply to actual memory system
        self._apply_to_memory_system(memory, action, compressed_content)

    def _apply_to_memory_system(
        self,
        memory: Dict,
        action: str,
        compressed_content: Optional[str]
    ):
        """
        Apply the curation decision to the actual memory system.

        The memory dict passed in is the normalized format with:
        - 'id': normalized ID
        - '_original': reference to the original memory dict (if available)

        We need to find and modify the original memory in memory_engine.memories.
        """
        if not self.memory_engine:
            return

        # Get normalized ID and try to find original
        memory_id = memory.get("id", "")
        original_mem = memory.get("_original")  # Direct reference if available

        def find_original_memory():
            """Find the original memory by ID (checking both 'id' and 'memory_id' fields)."""
            if not hasattr(self.memory_engine, 'memories'):
                return None

            for m in self.memory_engine.memories:
                if m.get("memory_id") == memory_id or m.get("id") == memory_id:
                    return m
            return None

        if action == "delete":
            # SOFT DELETE - Move to purge reserve instead of actual deletion
            target = original_mem or find_original_memory()

            if target:
                # Get content for red flag detection
                content = memory.get("content", "")

                # Get deletion reason
                reason = memory.get("_deletion_reason", "the entity chose to delete during curation")
                entity_note = memory.get("_entity_note")

                # Soft delete to purge reserve
                purged, red_flags = self.purge_reserve.soft_delete(
                    memory=target,
                    memory_id=memory_id,
                    content=content,
                    reason=reason,
                    entity_note=entity_note,
                    deleted_by="entity"
                )

                # Log red flags if any
                if red_flags:
                    flag_messages = [rf.message for rf in red_flags]
                    print(f"[CURATION] ⚠ Red flags detected: {', '.join(flag_messages)}")

                # Remove from active memory engine
                if hasattr(self.memory_engine, 'memories'):
                    original_count = len(self.memory_engine.memories)
                    self.memory_engine.memories = [
                        m for m in self.memory_engine.memories
                        if m.get("memory_id") != memory_id and m.get("id") != memory_id
                    ]
                    deleted_count = original_count - len(self.memory_engine.memories)
                    print(f"[CURATION] Soft deleted {deleted_count} memory/memories with ID: {memory_id[:30]}...")

                # Also remove from multi-layer system if present
                if hasattr(self.memory_engine, 'memory_layers'):
                    layer_mgr = self.memory_engine.memory_layers
                    for layer_name in ['working_memories', 'episodic_memories', 'semantic_memories']:
                        layer_dict = getattr(layer_mgr, layer_name, {})
                        if memory_id in layer_dict:
                            del layer_dict[memory_id]
                            print(f"[CURATION] Removed from {layer_name}")
            else:
                print(f"[CURATION] Warning: Could not find memory to delete: {memory_id[:30]}...")

        elif action == "compress" or action == "single_line_note":
            # Update memory content with compressed version
            target = original_mem or find_original_memory()

            if target:
                # Store original content for reference
                mem_type = target.get('type', 'unknown')
                if mem_type == 'full_turn':
                    target["original_user_input"] = target.get("user_input", "")
                    target["original_response"] = target.get("response", "")
                    # Replace with compressed summary
                    target["user_input"] = compressed_content
                    target["response"] = ""  # Clear response, summary is in user_input
                elif mem_type in ('extracted_fact', 'emotional_narrative', 'glyph_summary'):
                    target["original_fact"] = target.get("fact", "")
                    target["fact"] = compressed_content

                target["curated"] = True
                target["curation_action"] = action
                target["curation_timestamp"] = datetime.now().isoformat()
                print(f"[CURATION] Compressed memory: {memory_id[:30]}...")
            else:
                print(f"[CURATION] Warning: Could not find memory to compress: {memory_id[:30]}...")

        elif action == "keep_verbatim":
            # Mark as curated but don't modify content
            target = original_mem or find_original_memory()

            if target:
                target["curated"] = True
                target["curation_action"] = "keep_verbatim"
                target["curation_timestamp"] = datetime.now().isoformat()
                print(f"[CURATION] Marked as sacred (keep verbatim): {memory_id[:30]}...")
            else:
                print(f"[CURATION] Warning: Could not find memory to mark: {memory_id[:30]}...")

        # Save memories
        if hasattr(self.memory_engine, '_save_to_disk'):
            try:
                self.memory_engine._save_to_disk()
                print("[CURATION] Saved memory changes to disk")
            except Exception as e:
                print(f"[CURATION] Error saving memories: {e}")

    def _complete_session(self, parent, decisions: list):
        """Complete the curation session and show results."""
        # End session
        session = self.curator.end_session()

        if not session:
            self._show_dashboard(parent)
            return

        # Record session for learning
        self.learning_tracker.record_session_confidence(session)

        # Clear and show results
        for widget in parent.winfo_children():
            widget.destroy()

        # Show results panel
        results_panel = CurationResultsPanel(
            parent,
            self.palette,
            session
        )
        results_panel.pack(fill="x", padx=5, pady=5)

        # Add navigation button
        ctk.CTkButton(
            parent,
            text="← Back to Dashboard",
            command=lambda: self._show_dashboard(parent),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        ).pack(pady=20)

        # Update stats display if available
        if hasattr(self.companion_ui, '_update_memory_layer_display'):
            try:
                self.companion_ui._update_memory_layer_display()
            except:
                pass


def setup_curation_ui(companion_ui) -> CurationUIIntegration:
    """
    Setup curation UI integration.

    Args:
        companion_ui: The main CompanionApp instance

    Returns:
        CurationUIIntegration instance
    """
    return CurationUIIntegration(companion_ui)
