"""
Purge Reserve UI Components for Reed

CustomTkinter-based UI for managing soft-deleted memories:
- Dashboard showing purge reserve status
- Detail view for reviewing deleted memories
- Restoration and permanent deletion controls
- Red flag warnings and audit log display
"""

import customtkinter as ctk
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime


class PurgeReserveDashboard(ctk.CTkFrame):
    """
    Dashboard showing purge reserve status and controls.

    Displays:
    - Count of memories in reserve
    - Oldest/newest deletion dates
    - Calibration status
    - Auto-purge configuration
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        purge_reserve: Any = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.purge_reserve = purge_reserve

        # Callbacks
        self.on_view_reserve: Optional[Callable] = None
        self.on_view_flagged: Optional[Callable] = None
        self.on_view_audit: Optional[Callable] = None

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        """Build the dashboard UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n🗑 PURGE RESERVE\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Stats frame
        stats_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        stats_frame.pack(fill="x", padx=5, pady=5)

        # Count label
        self.count_label = ctk.CTkLabel(
            stats_frame,
            text="Currently holding: 0 deleted memories",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        self.count_label.pack(anchor="w", padx=10, pady=(10, 5))

        # Date range labels
        self.oldest_label = ctk.CTkLabel(
            stats_frame,
            text="Oldest deletion: N/A",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.oldest_label.pack(anchor="w", padx=10, pady=2)

        self.newest_label = ctk.CTkLabel(
            stats_frame,
            text="Newest deletion: N/A",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.newest_label.pack(anchor="w", padx=10, pady=2)

        # Red flags count
        self.flags_label = ctk.CTkLabel(
            stats_frame,
            text="⚠ With red flags: 0",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("user", "#D499B9")
        )
        self.flags_label.pack(anchor="w", padx=10, pady=(5, 10))

        # Configuration frame
        config_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        config_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            config_frame,
            text="Configuration:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Auto-purge status
        self.autopurge_label = ctk.CTkLabel(
            config_frame,
            text="Auto-purge: DISABLED (calibration mode)",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("accent", "#4A9B9B")
        )
        self.autopurge_label.pack(anchor="w", padx=10, pady=2)

        # Recovery window
        self.window_label = ctk.CTkLabel(
            config_frame,
            text="Recovery window: Indefinite",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.window_label.pack(anchor="w", padx=10, pady=(2, 10))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=10)

        self.view_reserve_btn = ctk.CTkButton(
            btn_frame,
            text="📋 View Purge Reserve",
            command=self._view_reserve,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        )
        self.view_reserve_btn.pack(fill="x", pady=2)

        self.view_flagged_btn = ctk.CTkButton(
            btn_frame,
            text="⚠ Review Flagged Deletions",
            command=self._view_flagged,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("user", "#D499B9"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=28
        )
        self.view_flagged_btn.pack(fill="x", pady=2)

        self.view_audit_btn = ctk.CTkButton(
            btn_frame,
            text="📊 View Audit Log",
            command=self._view_audit,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        )
        self.view_audit_btn.pack(fill="x", pady=2)

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="↻ Refresh",
            command=self.refresh_stats,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=24
        )
        self.refresh_btn.pack(fill="x", pady=2)

    def refresh_stats(self):
        """Refresh the dashboard statistics."""
        if not self.purge_reserve:
            return

        try:
            stats = self.purge_reserve.get_reserve_stats()

            # Update count
            self.count_label.configure(
                text=f"Currently holding: {stats['count']} deleted memories"
            )

            # Update dates
            if stats['oldest_deletion']:
                self.oldest_label.configure(
                    text=f"Oldest deletion: {stats['oldest_days_ago']} days ago"
                )
            else:
                self.oldest_label.configure(text="Oldest deletion: N/A")

            if stats['newest_deletion']:
                newest_text = "just now" if stats['newest_days_ago'] == 0 else f"{stats['newest_days_ago']} days ago"
                self.newest_label.configure(
                    text=f"Newest deletion: {newest_text}"
                )
            else:
                self.newest_label.configure(text="Newest deletion: N/A")

            # Update flags count
            self.flags_label.configure(
                text=f"⚠ With red flags: {stats['with_red_flags']}"
            )

            # Update auto-purge status
            if stats['calibration_complete']:
                if stats['auto_purge_enabled']:
                    self.autopurge_label.configure(
                        text=f"Auto-purge: ENABLED ({stats['recovery_window_days']} day window)",
                        text_color=self.palette.get("accent", "#4A9B9B")
                    )
                    self.window_label.configure(
                        text=f"Recovery window: {stats['recovery_window_days']} days"
                    )
                else:
                    self.autopurge_label.configure(
                        text="Auto-purge: DISABLED (calibrated)",
                        text_color=self.palette.get("muted", "#9B7D54")
                    )
                    self.window_label.configure(text="Recovery window: Indefinite")
            else:
                self.autopurge_label.configure(
                    text="Auto-purge: DISABLED (calibration mode)",
                    text_color=self.palette.get("user", "#D499B9")
                )
                self.window_label.configure(text="Recovery window: Indefinite")

        except Exception as e:
            print(f"[PURGE UI] Error refreshing stats: {e}")

    def _view_reserve(self):
        if self.on_view_reserve:
            self.on_view_reserve()

    def _view_flagged(self):
        if self.on_view_flagged:
            self.on_view_flagged()

    def _view_audit(self):
        if self.on_view_audit:
            self.on_view_audit()


class PurgeReserveListView(ctk.CTkFrame):
    """
    List view showing purged memories with restore/delete actions.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        purge_reserve: Any = None,
        show_only_flagged: bool = False
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.purge_reserve = purge_reserve
        self.show_only_flagged = show_only_flagged

        # Callbacks
        self.on_restore: Optional[Callable] = None
        self.on_permanent_delete: Optional[Callable] = None
        self.on_view_full: Optional[Callable] = None
        self.on_back: Optional[Callable] = None

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        """Build the list view UI."""
        # Header
        title = "⚠ FLAGGED DELETIONS" if self.show_only_flagged else "DELETED MEMORIES"
        header = ctk.CTkLabel(
            self,
            text=f"━" * 20 + f"\n{title}\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Back button
        back_btn = ctk.CTkButton(
            self,
            text="← Back to Dashboard",
            command=self._go_back,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28,
            width=150
        )
        back_btn.pack(anchor="w", padx=5, pady=5)

        # Scrollable list container
        self.list_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B"),
            scrollbar_button_hover_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        self.list_container.pack(fill="both", expand=True, padx=5, pady=5)

    def refresh_list(self):
        """Refresh the list of purged memories."""
        # Clear existing items
        for widget in self.list_container.winfo_children():
            widget.destroy()

        if not self.purge_reserve:
            return

        try:
            if self.show_only_flagged:
                memories = self.purge_reserve.get_flagged_deletions()
            else:
                memories = self.purge_reserve.get_purged_memories()

            if not memories:
                ctk.CTkLabel(
                    self.list_container,
                    text="No deleted memories in reserve",
                    font=ctk.CTkFont(family="Courier", size=10),
                    text_color=self.palette.get("muted", "#9B7D54")
                ).pack(pady=20)
                return

            # Create item for each memory
            for purged in memories:
                self._create_memory_item(purged)

        except Exception as e:
            print(f"[PURGE UI] Error refreshing list: {e}")

    def _create_memory_item(self, purged):
        """Create a UI item for a purged memory."""
        # Item frame
        item_frame = ctk.CTkFrame(
            self.list_container,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        item_frame.pack(fill="x", pady=3)

        # Content preview
        preview_text = purged.content_preview
        if len(preview_text) > 100:
            preview_text = preview_text[:100] + "..."

        ctk.CTkLabel(
            item_frame,
            text=f'"{preview_text}"',
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=350,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Metadata
        days_ago = self._days_since(purged.deleted_date)
        ctk.CTkLabel(
            item_frame,
            text=f"Deleted: {days_ago} days ago | Type: {purged.memory_type}",
            font=ctk.CTkFont(family="Courier", size=8),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(anchor="w", padx=10, pady=2)

        # Reason
        ctk.CTkLabel(
            item_frame,
            text=f"Reason: {purged.deletion_reason}",
            font=ctk.CTkFont(family="Courier", size=8),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(anchor="w", padx=10, pady=2)

        # Reed's note if present
        if purged.kay_note:
            ctk.CTkLabel(
                item_frame,
                text=f"Kay's note: \"{purged.kay_note}\"",
                font=ctk.CTkFont(family="Courier", size=8),
                text_color=self.palette.get("system", "#C4A574")
            ).pack(anchor="w", padx=10, pady=2)

        # Red flags warning
        if purged.red_flags:
            flags_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            flags_frame.pack(fill="x", padx=10, pady=2)

            ctk.CTkLabel(
                flags_frame,
                text="⚠ WARNING:",
                font=ctk.CTkFont(family="Courier", size=8, weight="bold"),
                text_color=self.palette.get("user", "#D499B9")
            ).pack(anchor="w")

            for flag in purged.red_flags[:3]:  # Show first 3 flags
                ctk.CTkLabel(
                    flags_frame,
                    text=f"  • {flag.get('message', '')}",
                    font=ctk.CTkFont(family="Courier", size=8),
                    text_color=self.palette.get("user", "#D499B9")
                ).pack(anchor="w")

        # Action buttons
        btn_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 8))

        # Restore button - make it prominent for flagged items
        restore_color = self.palette.get("accent", "#4A9B9B")
        if purged.red_flags:
            restore_color = self.palette.get("user", "#D499B9")  # More prominent for flagged

        ctk.CTkButton(
            btn_frame,
            text="↩ Restore",
            command=lambda m=purged: self._restore_memory(m),
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=restore_color,
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            width=80,
            height=24
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="🗑 Delete Forever",
            command=lambda m=purged: self._permanent_delete(m),
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("user", "#D499B9"),
            corner_radius=0,
            width=100,
            height=24
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="View Full",
            command=lambda m=purged: self._view_full(m),
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            width=70,
            height=24
        ).pack(side="left", padx=2)

    def _restore_memory(self, purged):
        """Handle restore button click."""
        if self.on_restore:
            self.on_restore(purged.memory_id)
        self.refresh_list()

    def _permanent_delete(self, purged):
        """Handle permanent delete button click."""
        if self.on_permanent_delete:
            self.on_permanent_delete(purged.memory_id)
        self.refresh_list()

    def _view_full(self, purged):
        """Handle view full button click."""
        if self.on_view_full:
            self.on_view_full(purged)

    def _go_back(self):
        """Handle back button click."""
        if self.on_back:
            self.on_back()

    def _days_since(self, date_str: str) -> int:
        """Calculate days since a date string."""
        try:
            date = datetime.fromisoformat(date_str)
            return (datetime.now() - date).days
        except:
            return 0


class AuditLogView(ctk.CTkFrame):
    """
    View showing the curation audit log.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        purge_reserve: Any = None,
        font_sizes: Dict[str, int] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.purge_reserve = purge_reserve

        # Font sizes (with defaults for larger readability)
        self.font_sizes = font_sizes or {
            'tiny': 10,
            'small': 12,
            'normal': 13,
            'medium': 14,
            'large': 16,
            'header': 18,
        }

        self.on_back: Optional[Callable] = None

        self._build_ui()
        self.refresh_log()

    def _build_ui(self):
        """Build the audit log UI with larger, more readable fonts."""
        # Header - LARGER
        header = ctk.CTkLabel(
            self,
            text="━" * 25 + "\n📊 CURATION AUDIT LOG\n" + "━" * 25,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['header'], weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Back button - larger
        back_btn = ctk.CTkButton(
            self,
            text="◀ Back to Dashboard",
            command=self._go_back,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal']),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=35,
            width=180
        )
        back_btn.pack(anchor="w", padx=5, pady=5)

        # Filter buttons - larger
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            filter_frame,
            text="Filter:",
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal'], weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(side="left", padx=(0, 10))

        self.filter_var = ctk.StringVar(value="all")

        for text, value in [("All", "all"), ("Deletions", "delete"),
                           ("Restorations", "restore"), ("Permanent", "permanent_delete")]:
            ctk.CTkRadioButton(
                filter_frame,
                text=text,
                variable=self.filter_var,
                value=value,
                command=self.refresh_log,
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['small']),
                text_color=self.palette.get("text", "#E8DCC4"),
                fg_color=self.palette.get("accent", "#4A9B9B")
            ).pack(side="left", padx=8)

        # Log container
        self.log_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B"),
            scrollbar_button_hover_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        self.log_container.pack(fill="both", expand=True, padx=5, pady=5)

    def refresh_log(self):
        """Refresh the audit log display."""
        # Clear existing entries
        for widget in self.log_container.winfo_children():
            widget.destroy()

        if not self.purge_reserve:
            print("[AUDIT LOG] No purge_reserve available!")
            ctk.CTkLabel(
                self.log_container,
                text="⚠ Purge reserve not available",
                font=ctk.CTkFont(family="Courier", size=10),
                text_color=self.palette.get("user", "#D499B9")
            ).pack(pady=20)
            return

        try:
            filter_val = self.filter_var.get()
            action_filter = None if filter_val == "all" else filter_val

            print(f"[AUDIT LOG] Getting audit log with filter: {action_filter}")
            entries = self.purge_reserve.get_audit_log(limit=100, action_filter=action_filter)
            print(f"[AUDIT LOG] Got {len(entries)} entries")

            if not entries:
                ctk.CTkLabel(
                    self.log_container,
                    text="No audit entries found.\nRun a curation session to generate entries.",
                    font=ctk.CTkFont(family="Courier", size=10),
                    text_color=self.palette.get("muted", "#9B7D54"),
                    justify="center"
                ).pack(pady=20)
                return

            # Show count header
            ctk.CTkLabel(
                self.log_container,
                text=f"Showing {len(entries)} audit entries:",
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color=self.palette.get("text", "#E8DCC4")
            ).pack(anchor="w", pady=(5, 10))

            for entry in entries:
                self._create_log_entry(entry)

        except Exception as e:
            print(f"[PURGE UI] Error refreshing audit log: {e}")
            import traceback
            traceback.print_exc()
            # Show error in UI
            ctk.CTkLabel(
                self.log_container,
                text=f"⚠ Error loading audit log:\n{str(e)[:100]}",
                font=ctk.CTkFont(family="Courier", size=10),
                text_color=self.palette.get("user", "#D499B9"),
                justify="center"
            ).pack(pady=20)

    def _create_log_entry(self, entry):
        """Create a UI item for an audit entry with larger, readable fonts."""
        # Determine color based on action
        action_colors = {
            "delete": self.palette.get("system", "#C4A574"),
            "restore": self.palette.get("accent", "#4A9B9B"),
            "permanent_delete": self.palette.get("user", "#D499B9"),
            "config_change": self.palette.get("muted", "#9B7D54"),
            "flag_detected": self.palette.get("user", "#D499B9"),
        }

        color = action_colors.get(entry.action, self.palette.get("text", "#E8DCC4"))

        # Format timestamp
        try:
            ts = datetime.fromisoformat(entry.timestamp)
            time_str = ts.strftime("%Y-%m-%d %H:%M")
        except:
            time_str = entry.timestamp[:16]

        # Entry frame with background for visibility
        entry_frame = ctk.CTkFrame(
            self.log_container,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        entry_frame.pack(fill="x", pady=3, padx=2)

        # Action icon
        icons = {
            "delete": "🗑",
            "restore": "↩",
            "permanent_delete": "💀",
            "config_change": "⚙",
            "flag_detected": "⚠",
        }
        icon = icons.get(entry.action, "•")

        # Entry header - LARGER
        entry_text = f"{time_str}: {icon} {entry.actor.upper()} - {entry.action.replace('_', ' ').upper()}"
        ctk.CTkLabel(
            entry_frame,
            text=entry_text,
            font=ctk.CTkFont(family="Courier", size=self.font_sizes['normal'], weight="bold"),
            text_color=color
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Memory ID
        if entry.memory_id and entry.memory_id != "system":
            ctk.CTkLabel(
                entry_frame,
                text=f"Memory: {entry.memory_id[:40]}...",
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['small']),
                text_color=self.palette.get("text", "#E8DCC4")
            ).pack(anchor="w", padx=10, pady=1)

        # Details - LARGER
        if entry.details:
            ctk.CTkLabel(
                entry_frame,
                text=f"→ {entry.details[:120]}{'...' if len(entry.details) > 120 else ''}",
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['small']),
                text_color=self.palette.get("muted", "#9B7D54"),
                wraplength=500,
                justify="left"
            ).pack(anchor="w", padx=10, pady=2)

        # Red flags if present - LARGER
        if entry.red_flags:
            flags_text = f"⚠ Flags: {', '.join(entry.red_flags[:3])}"
            ctk.CTkLabel(
                entry_frame,
                text=flags_text,
                font=ctk.CTkFont(family="Courier", size=self.font_sizes['small']),
                text_color=self.palette.get("user", "#D499B9")
            ).pack(anchor="w", padx=10, pady=(2, 8))

    def _go_back(self):
        if self.on_back:
            self.on_back()


class DeletionWarningDialog(ctk.CTkToplevel):
    """
    Warning dialog shown when attempting to delete a memory with red flags.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        memory_preview: str,
        red_flags: List[Dict],
        on_cancel: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        on_keep: Optional[Callable] = None
    ):
        super().__init__(parent)

        self.palette = palette
        self.on_cancel = on_cancel
        self.on_delete = on_delete
        self.on_keep = on_keep

        self.title("⚠ Deletion Warning")
        self.geometry("500x400")
        self.configure(fg_color=palette.get("bg", "#1A0F24"))

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._build_ui(memory_preview, red_flags)

    def _build_ui(self, memory_preview: str, red_flags: List[Dict]):
        """Build the warning dialog UI."""
        # Header
        ctk.CTkLabel(
            self,
            text="⚠ DELETION WARNING",
            font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=15)

        ctk.CTkLabel(
            self,
            text="━" * 40,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack()

        # Memory preview
        ctk.CTkLabel(
            self,
            text="You're about to delete:",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(anchor="w", padx=20, pady=(15, 5))

        preview_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0
        )
        preview_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            preview_frame,
            text=f'"{memory_preview[:150]}..."' if len(memory_preview) > 150 else f'"{memory_preview}"',
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=440,
            justify="left"
        ).pack(padx=10, pady=10)

        # Red flags
        ctk.CTkLabel(
            self,
            text="Red flags detected:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(anchor="w", padx=20, pady=(15, 5))

        for flag in red_flags:
            severity_colors = {
                "critical": self.palette.get("user", "#D499B9"),
                "high": self.palette.get("user", "#D499B9"),
                "moderate": self.palette.get("system", "#C4A574"),
                "low": self.palette.get("muted", "#9B7D54"),
            }
            color = severity_colors.get(flag.get("severity", "low"), self.palette.get("muted", "#9B7D54"))

            ctk.CTkLabel(
                self,
                text=f"  • {flag.get('message', 'Unknown flag')}",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=color
            ).pack(anchor="w", padx=20)

        # Suggestion
        ctk.CTkLabel(
            self,
            text="\nConsider: KEEP (verbatim) or SUMMARIZE instead",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("system", "#C4A574")
        ).pack(anchor="w", padx=20, pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self._cancel,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            width=100,
            height=32
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Keep Instead",
            command=self._keep,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            width=100,
            height=32
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Delete Anyway",
            command=self._delete,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("user", "#D499B9"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            width=100,
            height=32
        ).pack(side="left", padx=5)

    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()

    def _keep(self):
        if self.on_keep:
            self.on_keep()
        self.destroy()

    def _delete(self):
        if self.on_delete:
            self.on_delete()
        self.destroy()


class MemoryDetailView(ctk.CTkToplevel):
    """
    Full detail view for a purged memory.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        purged_memory
    ):
        super().__init__(parent)

        self.palette = palette

        self.title("Memory Details")
        self.geometry("600x500")
        self.configure(fg_color=palette.get("bg", "#1A0F24"))

        self._build_ui(purged_memory)

    def _build_ui(self, purged):
        """Build the detail view UI."""
        # Header
        ctk.CTkLabel(
            self,
            text="━" * 25 + "\n📄 MEMORY DETAILS\n" + "━" * 25,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        ).pack(pady=10)

        # Metadata
        meta_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0
        )
        meta_frame.pack(fill="x", padx=10, pady=5)

        meta_text = (
            f"ID: {purged.memory_id}\n"
            f"Type: {purged.memory_type}\n"
            f"Deleted: {purged.deleted_date}\n"
            f"By: {purged.deleted_by}\n"
            f"Reason: {purged.deletion_reason}"
        )
        if purged.kay_note:
            meta_text += f"\nKay's note: {purged.kay_note}"

        ctk.CTkLabel(
            meta_frame,
            text=meta_text,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        ).pack(anchor="w", padx=10, pady=10)

        # Red flags
        if purged.red_flags:
            flags_frame = ctk.CTkFrame(
                self,
                fg_color=self.palette.get("input", "#4A2B5C"),
                corner_radius=0
            )
            flags_frame.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(
                flags_frame,
                text="⚠ Red Flags:",
                font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                text_color=self.palette.get("user", "#D499B9")
            ).pack(anchor="w", padx=10, pady=(10, 5))

            for flag in purged.red_flags:
                ctk.CTkLabel(
                    flags_frame,
                    text=f"  • [{flag.get('severity', 'low')}] {flag.get('message', '')}",
                    font=ctk.CTkFont(family="Courier", size=8),
                    text_color=self.palette.get("user", "#D499B9")
                ).pack(anchor="w", padx=10)

            ctk.CTkLabel(flags_frame, text="").pack(pady=5)

        # Full content
        ctk.CTkLabel(
            self,
            text="Full Content:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        content_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=self.palette.get("input", "#4A2B5C"),
            text_color=self.palette.get("text", "#E8DCC4"),
            wrap="word",
            height=200
        )
        content_box.pack(fill="both", expand=True, padx=10, pady=5)

        # Get full content from original memory
        original = purged.original_memory
        if original.get("type") == "full_turn":
            content = f"User: {original.get('user_input', '')}\n\nKay: {original.get('response', '')}"
        else:
            content = original.get("fact", "") or original.get("content", "") or str(original)

        content_box.insert("1.0", content)
        content_box.configure(state="disabled")

        # Close button
        ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        ).pack(pady=10)
