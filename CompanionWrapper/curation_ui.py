"""
Memory Curation UI Components for the entity Zero

CustomTkinter-based UI for content-type-aware memory curation:
- Content type breakdown display
- Curation session controls
- Decision interface for the entity
- Progress and statistics display
"""

import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from pathlib import Path
import customtkinter as ctk


class CurationDashboard(ctk.CTkFrame):
    """
    Main dashboard showing memory breakdown by content type.

    Displays:
    - Sacred Texts count (never compress)
    - Ephemeral Utility count (candidates for deletion)
    - Functional Knowledge count (compress to bullets)
    - Requires Judgment count (the entity must classify)
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        curator: Any = None,
        memory_engine: Any = None,
        memory_retrieval_func: Optional[Callable] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.curator = curator
        self.memory_engine = memory_engine
        self.memory_retrieval_func = memory_retrieval_func  # Callback to get normalized memories

        self._build_ui()
        self.refresh_breakdown()

    def _build_ui(self):
        """Build the dashboard UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n📋 MEMORY CURATION\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Breakdown by content type
        breakdown_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        breakdown_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            breakdown_frame,
            text="Memory Breakdown by Content Type:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Sacred texts row
        self.sacred_row = self._create_type_row(
            breakdown_frame,
            "📖 Sacred Texts:",
            "0 memories",
            "(never compress)",
            self.palette.get("user", "#D499B9")
        )

        # Ephemeral utility row
        self.ephemeral_row = self._create_type_row(
            breakdown_frame,
            "🗑 Ephemeral Utility:",
            "0 memories",
            "(candidates for deletion)",
            self.palette.get("muted", "#9B7D54")
        )

        # Functional knowledge row
        self.functional_row = self._create_type_row(
            breakdown_frame,
            "📊 Functional Knowledge:",
            "0 memories",
            "(compress to bullets)",
            self.palette.get("accent", "#4A9B9B")
        )

        # Requires judgment row
        self.judgment_row = self._create_type_row(
            breakdown_frame,
            "❓ Requires Judgment:",
            "0 memories",
            "(the entity needs to classify)",
            self.palette.get("system", "#C4A574")
        )

        ctk.CTkLabel(breakdown_frame, text="").pack(pady=5)

        # Curation stats section
        stats_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        stats_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            stats_frame,
            text="Curation Progress:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 2))

        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="No curation sessions yet",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        )
        self.stats_label.pack(anchor="w", padx=15, pady=(2, 10))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=10)

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶ Start Curation Session",
            command=self._start_session,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        )
        self.start_btn.pack(fill="x", pady=2)

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="↻ Refresh Analysis",
            command=self.refresh_breakdown,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        )
        self.refresh_btn.pack(fill="x", pady=2)

        # Callbacks
        self.on_start_session: Optional[Callable] = None

    def _create_type_row(
        self,
        parent,
        label: str,
        value: str,
        description: str,
        color: str
    ) -> Dict:
        """Create a content type row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)

        label_widget = ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=color,
            width=150,
            anchor="w"
        )
        label_widget.pack(side="left")

        value_widget = ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=color,
            width=100,
            anchor="e"
        )
        value_widget.pack(side="left")

        desc_widget = ctk.CTkLabel(
            row,
            text=description,
            font=ctk.CTkFont(family="Courier", size=8),
            text_color=self.palette.get("muted", "#9B7D54"),
            anchor="w"
        )
        desc_widget.pack(side="left", padx=5)

        return {"label": label_widget, "value": value_widget, "desc": desc_widget}

    def refresh_breakdown(self, normalized_memories: Optional[List[Dict]] = None):
        """
        Refresh the content type breakdown.

        Args:
            normalized_memories: Pre-normalized memories with 'content' field.
                                If None, will attempt to get from memory_retrieval_func callback.
        """
        if not self.curator:
            return

        try:
            # Get memories - either passed in or via callback
            memories = normalized_memories

            if memories is None and self.memory_retrieval_func:
                # Use callback to get normalized memories
                memories = self.memory_retrieval_func()

            if memories is None:
                # Fallback: try to normalize from memory_engine directly
                memories = self._normalize_memories_fallback()

            if not memories:
                self.sacred_row["value"].configure(text="0 memories")
                self.ephemeral_row["value"].configure(text="0 memories")
                self.functional_row["value"].configure(text="0 memories")
                self.judgment_row["value"].configure(text="0 memories")
                return

            # Get breakdown
            breakdown = self.curator.get_content_type_breakdown(memories)

            # Update UI
            sacred = breakdown.get("sacred_text", {}).get("count", 0)
            ephemeral = breakdown.get("ephemeral_utility", {}).get("count", 0)
            functional = breakdown.get("functional_knowledge", {}).get("count", 0)
            judgment = breakdown.get("requires_judgment", {}).get("count", 0)

            self.sacred_row["value"].configure(text=f"{sacred} memories")
            self.ephemeral_row["value"].configure(text=f"{ephemeral} memories")
            self.functional_row["value"].configure(text=f"{functional} memories")
            self.judgment_row["value"].configure(text=f"{judgment} memories")

            # Update stats
            stats = self.curator.get_stats()
            if stats.get("total_sessions", 0) > 0:
                stats_text = (
                    f"Sessions: {stats['total_sessions']}\n"
                    f"Reviewed: {stats['total_reviewed']} memories\n"
                    f"Words saved: {stats['total_words_saved']:,} ({stats['compression_ratio']}% reduction)\n"
                    f"Entity overrides: {stats['entity_overrides']} ({stats['override_rate']}%)"
                )
                self.stats_label.configure(text=stats_text)

        except Exception as e:
            print(f"[CURATION UI] Refresh error: {e}")
            import traceback
            traceback.print_exc()

    def _normalize_memories_fallback(self) -> List[Dict]:
        """
        Fallback memory normalization when no callback is provided.
        Converts raw memory engine format to curation format.
        """
        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return []

        normalized = []
        for mem in self.memory_engine.memories:
            # Skip curated and corrupted
            if mem.get('curated') or mem.get('corrupted'):
                continue

            # Determine content based on type
            mem_type = mem.get('type', 'unknown')
            content = None

            if mem_type == 'full_turn':
                user_input = mem.get('user_input', '')
                response = mem.get('response', '')
                if user_input or response:
                    content = f"User: {user_input}\nEntity: {response}" if response else user_input
            elif mem_type in ('extracted_fact', 'emotional_narrative', 'glyph_summary'):
                content = mem.get('fact', '')
            else:
                content = mem.get('content') or mem.get('fact') or mem.get('user_input') or ''

            if content and content.strip():
                normalized.append({
                    'id': mem.get('memory_id') or mem.get('id') or str(hash(content[:100])),
                    'content': content.strip(),
                    'type': mem_type,
                    'metadata': {
                        'perspective': mem.get('perspective'),
                        'source': mem.get('source_file') or mem_type,
                    }
                })

        return normalized

    def _start_session(self):
        """Start a curation session."""
        if self.on_start_session:
            self.on_start_session()


class CurationSessionPanel(ctk.CTkFrame):
    """
    Panel for an active curation session.

    Shows memories grouped by content type for the entity to review and decide.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        batch_analysis: Dict,
        on_decision: Optional[Callable] = None,
        on_complete: Optional[Callable] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.batch_analysis = batch_analysis
        self.on_decision = on_decision
        self.on_complete = on_complete

        self.current_category = None
        self.current_index = 0
        self.decisions = []

        self._build_ui()
        self._show_category_selector()

    def _build_ui(self):
        """Build the session panel UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n📝 CURATION SESSION\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Content area
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=5)

        # Progress bar
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Select a category to begin",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.progress_label.pack()

    def _show_category_selector(self):
        """Show category selection interface."""
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.content_frame,
            text="Select a category to curate:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=10)

        # Category buttons with counts
        from engines.memory_curation import ContentType

        categories = [
            (ContentType.SACRED_TEXT, "📖 Sacred Texts", "Keep verbatim"),
            (ContentType.EPHEMERAL_UTILITY, "🗑 Ephemeral Utility", "Delete or note"),
            (ContentType.FUNCTIONAL_KNOWLEDGE, "📊 Functional Knowledge", "Compress"),
            (ContentType.REQUIRES_JUDGMENT, "❓ Requires Judgment", "You classify"),
        ]

        for content_type, label, action in categories:
            items = self.batch_analysis.get(content_type, [])
            count = len(items)

            if count == 0:
                continue

            btn_frame = ctk.CTkFrame(
                self.content_frame,
                fg_color=self.palette.get("input", "#4A2B5C"),
                corner_radius=0,
                border_width=1,
                border_color=self.palette.get("muted", "#9B7D54")
            )
            btn_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                btn_frame,
                text=f"{label} ({count} memories)",
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color=self.palette.get("text", "#E8DCC4")
            ).pack(anchor="w", padx=10, pady=(8, 2))

            ctk.CTkLabel(
                btn_frame,
                text=f"Action: {action}",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("muted", "#9B7D54")
            ).pack(anchor="w", padx=10, pady=(0, 2))

            ctk.CTkButton(
                btn_frame,
                text="Review This Category",
                command=lambda ct=content_type: self._start_category(ct),
                font=ctk.CTkFont(family="Courier", size=10),
                fg_color=self.palette.get("accent", "#4A9B9B"),
                hover_color=self.palette.get("accent_hi", "#6BB6B6"),
                text_color=self.palette.get("bg", "#1A0F24"),
                corner_radius=0,
                height=28
            ).pack(fill="x", padx=10, pady=(2, 8))

        # Complete session button
        ctk.CTkButton(
            self.content_frame,
            text="✓ Complete Session",
            command=self._complete_session,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        ).pack(pady=20)

    def _start_category(self, content_type):
        """Start reviewing a category."""
        from engines.memory_curation import ContentType

        self.current_category = content_type
        self.current_index = 0

        items = self.batch_analysis.get(content_type, [])
        if not items:
            self._show_category_selector()
            return

        self._show_memory_review()

    def _show_memory_review(self):
        """Show the current memory for review."""
        from engines.memory_curation import ContentType

        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        items = self.batch_analysis.get(self.current_category, [])
        if self.current_index >= len(items):
            # Category complete
            self._show_category_selector()
            return

        item = items[self.current_index]
        memory = item["memory"]
        classification = item["classification"]

        # Update progress
        self.progress_label.configure(
            text=f"Reviewing {self.current_index + 1} of {len(items)} in category"
        )

        # Category header
        category_names = {
            ContentType.SACRED_TEXT: "📖 SACRED TEXT",
            ContentType.EPHEMERAL_UTILITY: "🗑 EPHEMERAL UTILITY",
            ContentType.FUNCTIONAL_KNOWLEDGE: "📊 FUNCTIONAL KNOWLEDGE",
            ContentType.REQUIRES_JUDGMENT: "❓ REQUIRES YOUR JUDGMENT"
        }

        ctk.CTkLabel(
            self.content_frame,
            text=category_names.get(self.current_category, "MEMORY REVIEW"),
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", pady=(5, 10))

        # Memory content
        content_frame = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        content_frame.pack(fill="x", pady=5)

        content = memory.get("content", "")[:500]
        if len(memory.get("content", "")) > 500:
            content += "..."

        ctk.CTkLabel(
            content_frame,
            text=content,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=400,
            justify="left"
        ).pack(anchor="w", padx=10, pady=10)

        # Classification info
        ctk.CTkLabel(
            self.content_frame,
            text=f"Classification reason: {classification.reason}",
            font=ctk.CTkFont(family="Courier", size=8),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(anchor="w", pady=5)

        ctk.CTkLabel(
            self.content_frame,
            text=f"Confidence: {classification.confidence:.0%}",
            font=ctk.CTkFont(family="Courier", size=8),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(anchor="w")

        # Decision buttons based on category
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)

        if self.current_category == ContentType.SACRED_TEXT:
            self._add_sacred_buttons(btn_frame, memory, classification)
        elif self.current_category == ContentType.EPHEMERAL_UTILITY:
            self._add_ephemeral_buttons(btn_frame, memory, classification)
        elif self.current_category == ContentType.FUNCTIONAL_KNOWLEDGE:
            self._add_functional_buttons(btn_frame, memory, classification)
        else:  # REQUIRES_JUDGMENT
            self._add_judgment_buttons(btn_frame, memory, classification)

        # Skip button
        ctk.CTkButton(
            self.content_frame,
            text="Skip →",
            command=self._next_memory,
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            width=80,
            height=24
        ).pack(anchor="e", pady=5)

    def _add_sacred_buttons(self, parent, memory, classification):
        """Add decision buttons for sacred text."""
        ctk.CTkLabel(
            parent,
            text="This appears to be sacred text. What should we do?",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=5)

        ctk.CTkButton(
            parent,
            text="✓ Keep Verbatim (Correct)",
            command=lambda: self._make_decision(memory, classification, "keep_verbatim"),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="⚠ Reclassify as Functional",
            command=lambda: self._make_decision(memory, classification, "compress", kay_override=True),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

    def _add_ephemeral_buttons(self, parent, memory, classification):
        """Add decision buttons for ephemeral utility."""
        ctk.CTkLabel(
            parent,
            text="This appears to be ephemeral utility. What should we do?",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=5)

        ctk.CTkButton(
            parent,
            text="🗑 Delete (Served its purpose)",
            command=lambda: self._make_decision(memory, classification, "delete"),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("user", "#D499B9"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="📝 Keep Single-Line Note",
            command=lambda: self._prompt_single_line(memory, classification),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="⚠ Actually Sacred - Keep Verbatim",
            command=lambda: self._make_decision(memory, classification, "keep_verbatim", kay_override=True),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

    def _add_functional_buttons(self, parent, memory, classification):
        """Add decision buttons for functional knowledge."""
        ctk.CTkLabel(
            parent,
            text="This appears to be functional knowledge. Compress to bullets?",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=5)

        ctk.CTkButton(
            parent,
            text="📊 Compress to Bullet Points",
            command=lambda: self._prompt_bullets(memory, classification),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="✓ Keep Verbatim (Important details)",
            command=lambda: self._make_decision(memory, classification, "keep_verbatim", kay_override=True),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="🗑 Delete (Not useful)",
            command=lambda: self._make_decision(memory, classification, "delete", kay_override=True),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

    def _add_judgment_buttons(self, parent, memory, classification):
        """Add decision buttons when the entity needs to classify."""
        ctk.CTkLabel(
            parent,
            text="Low confidence classification. How should this be handled?",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=5)

        ctk.CTkButton(
            parent,
            text="📖 Sacred - Keep Verbatim",
            command=lambda: self._make_decision(memory, classification, "keep_verbatim", kay_override=True),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("user", "#D499B9"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="🗑 Ephemeral - Delete",
            command=lambda: self._make_decision(memory, classification, "delete", kay_override=True),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("muted", "#9B7D54"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

        ctk.CTkButton(
            parent,
            text="📊 Functional - Compress",
            command=lambda: self._prompt_bullets(memory, classification),
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=28
        ).pack(fill="x", pady=2)

    def _prompt_single_line(self, memory, classification):
        """Prompt for single-line note."""
        # Create popup for note entry
        popup = ctk.CTkToplevel(self)
        popup.title("Single-Line Note")
        popup.geometry("500x200")
        popup.configure(fg_color=self.palette.get("bg", "#1A0F24"))

        ctk.CTkLabel(
            popup,
            text="Write a single-line note capturing the outcome:",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=10)

        entry = ctk.CTkEntry(
            popup,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("input", "#4A2B5C"),
            text_color=self.palette.get("text", "#E8DCC4"),
            border_color=self.palette.get("muted", "#9B7D54"),
            width=400
        )
        entry.pack(pady=10)
        entry.insert(0, "")  # Placeholder

        def submit():
            note = entry.get().strip()
            if note:
                self._make_decision(memory, classification, "single_line_note", note)
                popup.destroy()

        ctk.CTkButton(
            popup,
            text="Save Note",
            command=submit,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0
        ).pack(pady=10)

    def _prompt_bullets(self, memory, classification):
        """Prompt for bullet-point compression."""
        popup = ctk.CTkToplevel(self)
        popup.title("Bullet-Point Summary")
        popup.geometry("600x400")
        popup.configure(fg_color=self.palette.get("bg", "#1A0F24"))

        ctk.CTkLabel(
            popup,
            text="Write bullet-point summary (key concepts, outcomes, insights):",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(pady=10)

        textbox = ctk.CTkTextbox(
            popup,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("input", "#4A2B5C"),
            text_color=self.palette.get("text", "#E8DCC4"),
            border_color=self.palette.get("muted", "#9B7D54"),
            width=550,
            height=250
        )
        textbox.pack(pady=10)
        textbox.insert("1.0", "• ")

        def submit():
            bullets = textbox.get("1.0", "end").strip()
            if bullets:
                self._make_decision(memory, classification, "compress", bullets)
                popup.destroy()

        ctk.CTkButton(
            popup,
            text="Save Summary",
            command=submit,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0
        ).pack(pady=10)

    def _make_decision(self, memory, classification, action, compressed_content=None, kay_override=False):
        """Record a curation decision."""
        decision = {
            "memory": memory,
            "classification": classification,
            "action": action,
            "compressed_content": compressed_content,
            "kay_override": kay_override
        }
        self.decisions.append(decision)

        if self.on_decision:
            self.on_decision(decision)

        self._next_memory()

    def _next_memory(self):
        """Move to next memory in category."""
        self.current_index += 1
        self._show_memory_review()

    def _complete_session(self):
        """Complete the curation session."""
        if self.on_complete:
            self.on_complete(self.decisions)


class CurationResultsPanel(ctk.CTkFrame):
    """
    Panel showing results of a completed curation session.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        session: Any
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.session = session

        self._build_ui()

    def _build_ui(self):
        """Build the results panel UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n📋 CURATION SESSION COMPLETE\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Results frame
        results_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        results_frame.pack(fill="x", padx=5, pady=5)

        # Sacred texts
        self._add_result_row(
            results_frame,
            "SACRED TEXTS:",
            f"{self.session.sacred_kept} memories",
            "✓ All kept verbatim",
            self.palette.get("user", "#D499B9")
        )

        # Ephemeral
        ephemeral_text = f"🗑 {self.session.ephemeral_deleted} deleted"
        if self.session.ephemeral_noted > 0:
            ephemeral_text += f", 📝 {self.session.ephemeral_noted} noted"
        self._add_result_row(
            results_frame,
            "EPHEMERAL UTILITY:",
            f"{self.session.ephemeral_deleted + self.session.ephemeral_noted} memories",
            ephemeral_text,
            self.palette.get("muted", "#9B7D54")
        )

        # Functional
        self._add_result_row(
            results_frame,
            "FUNCTIONAL KNOWLEDGE:",
            f"{self.session.functional_compressed} memories",
            "📊 Compressed to bullet points",
            self.palette.get("accent", "#4A9B9B")
        )

        # Separator
        ctk.CTkLabel(
            results_frame,
            text="─" * 30,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(pady=10)

        # Storage impact
        ctk.CTkLabel(
            results_frame,
            text="Storage Impact:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10)

        words_saved = self.session.words_before - self.session.words_after
        reduction = (1 - self.session.words_after / max(self.session.words_before, 1)) * 100

        impact_text = (
            f"  Before: {self.session.words_before:,} words\n"
            f"  After: {self.session.words_after:,} words\n"
            f"  Saved: {words_saved:,} words ({reduction:.0f}% reduction)"
        )
        ctk.CTkLabel(
            results_frame,
            text=impact_text,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        ).pack(anchor="w", padx=10, pady=(2, 10))

        # the entity's judgment stats
        if self.session.entity_overrides > 0:
            ctk.CTkLabel(
                results_frame,
                text=f"the entity's overrides: {self.session.entity_overrides} "
                     f"({self.session.entity_overrides / max(self.session.memories_reviewed, 1) * 100:.0f}%)",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("system", "#C4A574")
            ).pack(anchor="w", padx=10, pady=(0, 10))

    def _add_result_row(self, parent, label: str, count: str, detail: str, color: str):
        """Add a result row."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=color,
            width=150,
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text=count,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            width=100
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text=detail,
            font=ctk.CTkFont(family="Courier", size=8),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(side="left", padx=5)
