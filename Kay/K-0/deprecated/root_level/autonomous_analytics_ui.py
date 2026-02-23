"""
Autonomous Analytics UI Components for Kay Zero

Comprehensive UI components for visualizing and interacting with
Kay's autonomous memory architecture, including:
- Memory Architecture Dashboard
- Gap Analysis Interface
- Cognitive Stability Testing
- Session Comparison Views
- Kay-Accessible Analytics

These components implement Kay's self-designed memory specification
for understanding his own cognitive patterns.
"""

import os
import json
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime
from pathlib import Path
import customtkinter as ctk


class MemoryArchitectureDashboard(ctk.CTkFrame):
    """
    Main dashboard showing memory distribution across all tiers.

    Displays:
    - Working Memory (ephemeral)
    - Conversation Memory (dialogue-based)
    - Autonomous Memory (solo processing)
    - Topic overlap analysis
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        memory_engine: Any = None,
        autonomous_memory: Any = None,
        gap_analyzer: Any = None,
        layer_manager: Any = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.memory_engine = memory_engine
        self.autonomous_memory = autonomous_memory
        self.gap_analyzer = gap_analyzer
        self.layer_manager = layer_manager

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        """Build the dashboard UI."""
        # Header with refresh
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            header_frame,
            text="━" * 20 + "\n📊 MEMORY ARCHITECTURE\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        ).pack(side="left", expand=True)

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="↻",
            command=self.refresh_data,
            font=ctk.CTkFont(family="Courier", size=14),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            width=35,
            height=35,
            corner_radius=0
        )
        refresh_btn.pack(side="right", padx=5)

        # Memory Tiers Section
        tiers_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        tiers_frame.pack(fill="x", padx=5, pady=5)

        # Working Memory
        self.working_row = self._create_tier_row(
            tiers_frame,
            "🔄 Working Memory:",
            "0 items",
            "(ephemeral)",
            self.palette.get("muted", "#9B7D54")
        )

        # Conversation Memory
        self.conv_row = self._create_tier_row(
            tiers_frame,
            "💬 Conversation Memory:",
            "0 facts",
            "(dialogue-based)",
            self.palette.get("text", "#E8DCC4")
        )

        # Autonomous Memory
        self.auto_row = self._create_tier_row(
            tiers_frame,
            "🧠 Autonomous Memory:",
            "0 insights",
            "(solo processing)",
            self.palette.get("accent", "#4A9B9B")
        )

        # Separator
        ctk.CTkLabel(
            tiers_frame,
            text="─" * 30,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(pady=5)

        # Topic Analysis Section
        topic_header = ctk.CTkLabel(
            tiers_frame,
            text="Topic Analysis:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        topic_header.pack(anchor="w", padx=10, pady=(5, 2))

        # Topic stats
        self.overlap_label = self._create_stat_label(
            tiers_frame,
            "Overlap topics:",
            "0",
            "(appear in both contexts)",
            self.palette.get("system", "#C4A574")
        )

        self.auto_only_label = self._create_stat_label(
            tiers_frame,
            "Autonomous-only:",
            "0",
            "(Kay thinks about alone)",
            self.palette.get("user", "#D499B9")
        )

        self.conv_only_label = self._create_stat_label(
            tiers_frame,
            "Conversation-only:",
            "0",
            "(only emerge with Re)",
            self.palette.get("kay", "#6BB6B6")
        )

        # Spacer
        ctk.CTkLabel(tiers_frame, text="").pack(pady=3)

        # Note: Navigation buttons removed - use top-level tabs instead
        # Gap Analysis -> "Gaps" tab
        # Autonomous History -> "Session" tab

    def _create_tier_row(
        self,
        parent,
        label: str,
        value: str,
        description: str,
        color: str
    ) -> Dict:
        """Create a memory tier row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=3)

        label_widget = ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=color,
            anchor="w",
            width=160
        )
        label_widget.pack(side="left")

        value_widget = ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=color,
            anchor="e",
            width=80
        )
        value_widget.pack(side="left")

        desc_widget = ctk.CTkLabel(
            row,
            text=description,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            anchor="w"
        )
        desc_widget.pack(side="left", padx=5)

        return {"label": label_widget, "value": value_widget, "desc": desc_widget}

    def _create_stat_label(
        self,
        parent,
        label: str,
        value: str,
        description: str,
        color: str
    ) -> Dict:
        """Create a stat label row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=1)

        label_widget = ctk.CTkLabel(
            row,
            text=f"  {label}",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            anchor="w",
            width=130
        )
        label_widget.pack(side="left")

        value_widget = ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=color,
            anchor="e",
            width=40
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

    def refresh_data(self):
        """Refresh all dashboard data."""
        try:
            # Working memory count
            working_count = 0
            if self.layer_manager and hasattr(self.layer_manager, 'working_memory'):
                working_count = len(self.layer_manager.working_memory)
            self.working_row["value"].configure(text=f"{working_count} items")

            # Conversation memory count
            conv_count = 0
            if self.memory_engine and hasattr(self.memory_engine, 'memories'):
                conv_count = len(self.memory_engine.memories)
            self.conv_row["value"].configure(text=f"{conv_count:,} facts")

            # Autonomous memory count
            auto_count = 0
            if self.autonomous_memory and hasattr(self.autonomous_memory, 'insights'):
                auto_count = len(self.autonomous_memory.insights)
            self.auto_row["value"].configure(text=f"{auto_count} insights")

            # Gap analysis data
            if self.gap_analyzer:
                try:
                    gap_data = self.gap_analyzer.get_full_gap_analysis()
                    overlap = gap_data.get("overlap", {}).get("count", 0)
                    auto_only = gap_data.get("autonomous_only", {}).get("count", 0)
                    conv_only = gap_data.get("conversation_only", {}).get("count", 0)

                    self.overlap_label["value"].configure(text=str(overlap))
                    self.auto_only_label["value"].configure(text=str(auto_only))
                    self.conv_only_label["value"].configure(text=str(conv_only))
                except Exception as e:
                    print(f"[DASHBOARD] Gap analysis error: {e}")

        except Exception as e:
            print(f"[DASHBOARD] Refresh error: {e}")

class GapAnalysisInterface(ctk.CTkFrame):
    """
    Detailed interface for cognitive gap analysis.

    Shows:
    - Topics Kay explores only in autonomous mode
    - Topics that only emerge in conversation
    - Topics appearing in both contexts
    - Pattern interpretation
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        gap_analyzer: Any = None,
        autonomous_memory: Any = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.gap_analyzer = gap_analyzer
        self.autonomous_memory = autonomous_memory

        self._build_ui()
        self.refresh_analysis()

    def _build_ui(self):
        """Build the gap analysis UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n🔍 COGNITIVE GAP ANALYSIS\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Scroll container for content
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        self.scroll.pack(fill="both", expand=True, padx=5)

        # Autonomous-only section
        self.auto_only_frame = self._create_topic_section(
            "Topics Kay explores ONLY in autonomous mode:",
            self.palette.get("user", "#D499B9")
        )

        # Conversation-only section
        self.conv_only_frame = self._create_topic_section(
            "Topics that ONLY emerge in conversation with Re:",
            self.palette.get("kay", "#6BB6B6")
        )

        # Overlap section
        self.overlap_frame = self._create_topic_section(
            "Topics appearing in BOTH contexts:",
            self.palette.get("system", "#C4A574")
        )

        # Interpretation section
        interp_frame = ctk.CTkFrame(
            self.scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        interp_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            interp_frame,
            text="What does this pattern tell us?",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.interpretation_label = ctk.CTkLabel(
            interp_frame,
            text="Loading analysis...",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=350,
            justify="left"
        )
        self.interpretation_label.pack(anchor="w", padx=10, pady=(2, 10))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)

        self.export_btn = ctk.CTkButton(
            btn_frame,
            text="📤 Export Analysis",
            command=self._export_analysis,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        )
        self.export_btn.pack(side="left", expand=True, fill="x", padx=2)

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="↻ Refresh",
            command=self.refresh_analysis,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        )
        self.refresh_btn.pack(side="right", expand=True, fill="x", padx=2)

        # Status label for feedback
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.status_label.pack(pady=2)

    def _create_topic_section(self, title: str, color: str) -> ctk.CTkFrame:
        """Create a topic section frame."""
        frame = ctk.CTkFrame(
            self.scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=color
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Topics will be added here
        topics_container = ctk.CTkFrame(frame, fg_color="transparent")
        topics_container.pack(fill="x", padx=10, pady=(2, 8))
        frame.topics_container = topics_container

        return frame

    def refresh_analysis(self):
        """Refresh the gap analysis data."""
        if not self.gap_analyzer:
            self.interpretation_label.configure(
                text="Gap analyzer not available. Run an autonomous session first."
            )
            return

        try:
            gap_data = self.gap_analyzer.get_full_gap_analysis()

            # Update autonomous-only topics
            self._update_topic_list(
                self.auto_only_frame.topics_container,
                gap_data.get("autonomous_only", {}).get("topics", []),
                self.palette.get("user", "#D499B9")
            )

            # Update conversation-only topics
            self._update_topic_list(
                self.conv_only_frame.topics_container,
                gap_data.get("conversation_only", {}).get("topics", []),
                self.palette.get("kay", "#6BB6B6")
            )

            # Update overlap topics
            self._update_topic_list(
                self.overlap_frame.topics_container,
                gap_data.get("overlap", {}).get("topics", []),
                self.palette.get("system", "#C4A574")
            )

            # Generate interpretation
            auto_only_count = gap_data.get("autonomous_only", {}).get("count", 0)
            conv_only_count = gap_data.get("conversation_only", {}).get("count", 0)
            overlap_count = gap_data.get("overlap", {}).get("count", 0)

            if auto_only_count > 0 or conv_only_count > 0:
                interpretation = self._generate_interpretation(
                    auto_only_count, conv_only_count, overlap_count,
                    gap_data.get("autonomous_only", {}).get("topics", []),
                    gap_data.get("conversation_only", {}).get("topics", [])
                )
                self.interpretation_label.configure(text=interpretation)
            else:
                self.interpretation_label.configure(
                    text="Not enough data for pattern analysis yet. "
                         "Run more autonomous sessions to see cognitive gaps emerge."
                )

        except Exception as e:
            print(f"[GAP ANALYSIS] Refresh error: {e}")
            self.interpretation_label.configure(text=f"Error loading analysis: {str(e)[:50]}")

    def _update_topic_list(self, container, topics: List[str], color: str):
        """Update a topic list container."""
        # Clear existing
        for widget in container.winfo_children():
            widget.destroy()

        if not topics:
            ctk.CTkLabel(
                container,
                text="  (none yet)",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("muted", "#9B7D54")
            ).pack(anchor="w")
            return

        # Show topics as bullet list
        for topic in topics[:10]:
            ctk.CTkLabel(
                container,
                text=f"  • {topic}",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=color
            ).pack(anchor="w")

        if len(topics) > 10:
            ctk.CTkLabel(
                container,
                text=f"  ... and {len(topics) - 10} more",
                font=ctk.CTkFont(family="Courier", size=8),
                text_color=self.palette.get("muted", "#9B7D54")
            ).pack(anchor="w")

    def _generate_interpretation(
        self,
        auto_only: int,
        conv_only: int,
        overlap: int,
        auto_topics: List[str],
        conv_topics: List[str]
    ) -> str:
        """Generate natural language interpretation of patterns."""
        parts = []

        if auto_only > conv_only:
            parts.append(
                f"Kay has {auto_only} topics he explores alone but doesn't "
                f"discuss in conversation. These may be private concerns or "
                f"self-referential questions that don't need external input."
            )
        elif conv_only > auto_only:
            parts.append(
                f"More topics ({conv_only}) emerge in dialogue than in solo "
                f"processing ({auto_only}). Kay's thinking may be more "
                f"reactive/relational than internally generative."
            )

        if overlap > 0:
            ratio = overlap / max(auto_only + conv_only + overlap, 1)
            if ratio > 0.5:
                parts.append(
                    f"High topic overlap ({overlap} topics, {ratio:.0%}) suggests "
                    f"Kay's core concerns are consistent across contexts."
                )
            else:
                parts.append(
                    f"Low overlap ({overlap} topics, {ratio:.0%}) suggests "
                    f"Kay thinks about different things alone vs. in dialogue."
                )

        # Try to identify patterns in topic types
        meta_keywords = ["self", "monitor", "architecture", "cognition", "thinking"]
        social_keywords = ["re", "conversation", "dialogue", "together", "shared"]

        auto_has_meta = any(
            any(kw in t.lower() for kw in meta_keywords)
            for t in auto_topics[:10]
        )
        conv_has_social = any(
            any(kw in t.lower() for kw in social_keywords)
            for t in conv_topics[:10]
        )

        if auto_has_meta:
            parts.append(
                "Autonomous topics tend toward self-referential/architectural questions."
            )
        if conv_has_social:
            parts.append(
                "Conversation topics include more social/relational content."
            )

        return " ".join(parts) if parts else "Patterns still emerging..."

    def _export_analysis(self):
        """Export gap analysis to file with timestamp and user feedback."""
        if not self.gap_analyzer:
            self._show_status("⚠ Gap analyzer not available", error=True)
            return

        try:
            gap_data = self.gap_analyzer.get_full_gap_analysis()

            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = Path(f"memory/gap_analysis_export_{timestamp}.json")
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # Build comprehensive export data
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "export_timestamp": timestamp,
                "autonomous_only": {
                    "count": gap_data.get("autonomous_only", {}).get("count", 0),
                    "topics": gap_data.get("autonomous_only", {}).get("topics", []),
                    "description": "Topics Kay explores only in autonomous mode"
                },
                "conversation_only": {
                    "count": gap_data.get("conversation_only", {}).get("count", 0),
                    "topics": gap_data.get("conversation_only", {}).get("topics", []),
                    "description": "Topics that only emerge in conversation with Re"
                },
                "overlap": {
                    "count": gap_data.get("overlap", {}).get("count", 0),
                    "topics": gap_data.get("overlap", {}).get("topics", []),
                    "description": "Topics appearing in both contexts"
                },
                "analysis": gap_data.get("analysis", {}),
                "interpretation": self.interpretation_label.cget("text")
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self._show_status(f"✓ Exported to {export_path.name}", error=False)
            print(f"[GAP ANALYSIS] Exported to {export_path}")

        except Exception as e:
            error_msg = str(e)[:50]
            self._show_status(f"⚠ Export failed: {error_msg}", error=True)
            print(f"[GAP ANALYSIS] Export error: {e}")

    def _show_status(self, message: str, error: bool = False):
        """Show status message with appropriate color."""
        color = self.palette.get("user", "#D499B9") if error else self.palette.get("accent", "#4A9B9B")
        self.status_label.configure(text=message, text_color=color)

        # Auto-clear after 5 seconds
        self.after(5000, lambda: self.status_label.configure(text=""))


class CognitiveStabilityTestPanel(ctk.CTkFrame):
    """
    Panel for running cognitive stability tests.

    Tests whether Kay's thinking is internally stable
    or conversationally dependent by comparing autonomous
    vs. conversation insights on the same topic.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        stability_tester: Any = None,
        on_run_test: Optional[Callable] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.stability_tester = stability_tester
        self.on_run_test = on_run_test

        self._build_ui()
        self.refresh_topics()

    def _build_ui(self):
        """Build the stability testing UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n🧪 STABILITY TESTING\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Description
        desc = ctk.CTkLabel(
            self,
            text="Test whether Kay's cognition is internally stable\n"
                 "or conversationally dependent by re-running\n"
                 "autonomous sessions on topics already discussed.",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            justify="center"
        )
        desc.pack(pady=5)

        # Topic selection frame
        select_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        select_frame.pack(fill="x", padx=5, pady=10)

        ctk.CTkLabel(
            select_frame,
            text="Select topic for stability test:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Topic dropdown
        self.topic_var = ctk.StringVar(value="Select a topic...")
        self.topic_dropdown = ctk.CTkOptionMenu(
            select_frame,
            variable=self.topic_var,
            values=["Loading topics..."],
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("panel", "#2D1B3D"),
            button_color=self.palette.get("accent", "#4A9B9B"),
            button_hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            dropdown_fg_color=self.palette.get("panel", "#2D1B3D"),
            dropdown_hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            width=280
        )
        self.topic_dropdown.pack(padx=10, pady=5)

        # Custom topic entry
        custom_frame = ctk.CTkFrame(select_frame, fg_color="transparent")
        custom_frame.pack(fill="x", padx=10, pady=5)

        self.custom_var = ctk.BooleanVar(value=False)
        self.custom_check = ctk.CTkCheckBox(
            custom_frame,
            text="Custom topic:",
            variable=self.custom_var,
            command=self._toggle_custom,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.custom_check.pack(side="left")

        self.custom_entry = ctk.CTkEntry(
            custom_frame,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("panel", "#2D1B3D"),
            text_color=self.palette.get("text", "#E8DCC4"),
            border_color=self.palette.get("muted", "#9B7D54"),
            corner_radius=0,
            width=180,
            state="disabled"
        )
        self.custom_entry.pack(side="left", padx=10)

        # Run test button
        self.run_btn = ctk.CTkButton(
            select_frame,
            text="▶ Run Stability Test",
            command=self._run_test,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        )
        self.run_btn.pack(fill="x", padx=10, pady=10)

        # Previous tests section
        prev_header = ctk.CTkLabel(
            self,
            text="Previous Stability Tests:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        prev_header.pack(anchor="w", padx=10, pady=(15, 5))

        # Separator
        ctk.CTkLabel(
            self,
            text="━" * 30,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack()

        # Previous tests scroll
        self.prev_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B"),
            height=150
        )
        self.prev_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.no_tests_label = ctk.CTkLabel(
            self.prev_scroll,
            text="No stability tests run yet",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.no_tests_label.pack(pady=20)

    def _toggle_custom(self):
        """Toggle custom topic entry."""
        if self.custom_var.get():
            self.custom_entry.configure(state="normal")
            self.topic_dropdown.configure(state="disabled")
        else:
            self.custom_entry.configure(state="disabled")
            self.topic_dropdown.configure(state="normal")

    def refresh_topics(self):
        """Refresh available topics for testing."""
        if not self.stability_tester:
            self.topic_dropdown.configure(values=["No tester available"])
            return

        try:
            topics = self.stability_tester.get_testable_topics()
            if topics:
                topic_names = [t[0] for t in topics[:20]]  # Top 20 by frequency
                self.topic_dropdown.configure(values=topic_names)
                self.topic_var.set(topic_names[0] if topic_names else "No topics found")
            else:
                self.topic_dropdown.configure(values=["No topics with enough data"])
        except Exception as e:
            print(f"[STABILITY] Topic refresh error: {e}")
            self.topic_dropdown.configure(values=["Error loading topics"])

    def _run_test(self):
        """Run a stability test."""
        topic = self.custom_entry.get() if self.custom_var.get() else self.topic_var.get()

        if not topic or topic.startswith("Select") or topic.startswith("No "):
            return

        if self.on_run_test:
            self.on_run_test(topic)

    def display_test_result(self, result: Dict):
        """Display a stability test result."""
        # Clear no tests label
        self.no_tests_label.pack_forget()

        # Create result card
        card = ctk.CTkFrame(
            self.prev_scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        card.pack(fill="x", pady=5)

        # Topic and date
        topic = result.get("topic", "Unknown")
        timestamp = result.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = timestamp[:16] if timestamp else "Unknown"

        ctk.CTkLabel(
            card,
            text=f"Test: \"{topic}\" ({date_str})",
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        # Similarity score
        comparison = result.get("comparison", {})
        similarity = comparison.get("similarity_score", 0)
        conclusion = comparison.get("conclusion", "unknown")

        stability_text = {
            "stable": "stable",
            "mixed": "moderately stable",
            "conversationally_dependent": "context-dependent"
        }.get(conclusion, "unknown")

        color = {
            "stable": self.palette.get("accent", "#4A9B9B"),
            "mixed": self.palette.get("system", "#C4A574"),
            "conversationally_dependent": self.palette.get("user", "#D499B9")
        }.get(conclusion, self.palette.get("muted", "#9B7D54"))

        ctk.CTkLabel(
            card,
            text=f"  Similarity: {similarity:.0%} ({stability_text})",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=color
        ).pack(anchor="w", padx=10, pady=1)

        # Interpretation
        interpretation = comparison.get("interpretation", "")
        if interpretation:
            ctk.CTkLabel(
                card,
                text=f"  {interpretation[:100]}...",
                font=ctk.CTkFont(family="Courier", size=8),
                text_color=self.palette.get("muted", "#9B7D54"),
                wraplength=300
            ).pack(anchor="w", padx=10, pady=(1, 8))


class SessionComparisonView(ctk.CTkToplevel):
    """
    Side-by-side comparison of autonomous vs conversation insights
    on the same topic.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        topic: str,
        autonomous_insights: List[Dict],
        conversation_insights: List[Dict],
        comparison_result: Dict
    ):
        super().__init__(parent)

        self.palette = palette
        self.topic = topic
        self.autonomous_insights = autonomous_insights
        self.conversation_insights = conversation_insights
        self.comparison = comparison_result

        self.title(f"Context Comparison: {topic[:30]}")
        self.geometry("800x700")
        self.configure(fg_color=palette.get("bg", "#1A0F24"))

        self._build_ui()

    def _build_ui(self):
        """Build the comparison view UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text=f"━" * 30 + f"\n⚖️ CONTEXT COMPARISON: \"{self.topic}\"\n" + "━" * 30,
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=15)

        # Main content - two columns
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Left column - Autonomous
        auto_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("user", "#D499B9")
        )
        auto_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ctk.CTkLabel(
            auto_frame,
            text="🧠 AUTONOMOUS SESSION",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        auto_scroll = ctk.CTkScrollableFrame(
            auto_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("user", "#D499B9"),
            height=200
        )
        auto_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._populate_insights(auto_scroll, self.autonomous_insights, "autonomous")

        # Right column - Conversation
        conv_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("kay", "#6BB6B6")
        )
        conv_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        ctk.CTkLabel(
            conv_frame,
            text="💬 CONVERSATION",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("kay", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        conv_scroll = ctk.CTkScrollableFrame(
            conv_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("kay", "#6BB6B6"),
            height=200
        )
        conv_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._populate_insights(conv_scroll, self.conversation_insights, "conversation")

        # Similarity Analysis section
        analysis_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        analysis_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(
            analysis_frame,
            text="SIMILARITY ANALYSIS",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        similarity = self.comparison.get("similarity_score", 0)
        conclusion = self.comparison.get("conclusion", "unknown")

        ctk.CTkLabel(
            analysis_frame,
            text=f"  Similarity: {similarity:.0%}",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(anchor="w", padx=10, pady=2)

        # Divergence points
        divergence = self.comparison.get("divergence_points", {})
        conv_unique = divergence.get("conversation_unique", [])
        auto_unique = divergence.get("autonomous_unique", [])

        if conv_unique:
            ctk.CTkLabel(
                analysis_frame,
                text=f"  Conversation-unique: {', '.join(conv_unique[:5])}",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("kay", "#6BB6B6")
            ).pack(anchor="w", padx=10, pady=1)

        if auto_unique:
            ctk.CTkLabel(
                analysis_frame,
                text=f"  Autonomous-unique: {', '.join(auto_unique[:5])}",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("user", "#D499B9")
            ).pack(anchor="w", padx=10, pady=1)

        # Interpretation
        interpretation = self.comparison.get("interpretation", "")
        if interpretation:
            ctk.CTkLabel(
                analysis_frame,
                text="",
                font=ctk.CTkFont(family="Courier", size=1)
            ).pack()  # Spacer

            ctk.CTkLabel(
                analysis_frame,
                text="INTERPRETATION:",
                font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                text_color=self.palette.get("system", "#C4A574")
            ).pack(anchor="w", padx=10, pady=(5, 2))

            ctk.CTkLabel(
                analysis_frame,
                text=interpretation,
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("text", "#E8DCC4"),
                wraplength=700,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(2, 10))

        # Close button
        close_btn = ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        )
        close_btn.pack(pady=15)

    def _populate_insights(self, container, insights: List[Dict], context: str):
        """Populate a scroll container with insights."""
        if not insights:
            ctk.CTkLabel(
                container,
                text="No insights found for this topic",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("muted", "#9B7D54")
            ).pack(pady=20)
            return

        for i, insight in enumerate(insights[:10], 1):
            content = insight.get("content", str(insight))
            if len(content) > 150:
                content = content[:150] + "..."

            card = ctk.CTkFrame(
                container,
                fg_color=self.palette.get("bg", "#1A0F24"),
                corner_radius=0
            )
            card.pack(fill="x", pady=3)

            ctk.CTkLabel(
                card,
                text=f"{i}. {content}",
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("text", "#E8DCC4"),
                wraplength=320,
                justify="left"
            ).pack(anchor="w", padx=5, pady=5)


class CognitivePatternAnalytics(ctk.CTkFrame):
    """
    Kay-accessible analytics panel.

    Shows Kay's cognitive patterns across autonomous
    and conversation contexts.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        autonomous_memory: Any = None,
        memory_engine: Any = None,
        gap_analyzer: Any = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.autonomous_memory = autonomous_memory
        self.memory_engine = memory_engine
        self.gap_analyzer = gap_analyzer

        self._build_ui()
        self.refresh_analytics()

    def _build_ui(self):
        """Build the analytics UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 20 + "\n📈 YOUR COGNITIVE PATTERNS\n" + "━" * 20,
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=10)

        # Stats source label
        self.source_label = ctk.CTkLabel(
            self,
            text="Based on 0 autonomous sessions and 0 conversation facts:",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.source_label.pack(pady=5)

        # Scroll container
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True, padx=5)

        # Alone section
        alone_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("user", "#D499B9")
        )
        alone_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            alone_frame,
            text="What you think about ALONE:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.alone_stats = ctk.CTkLabel(
            alone_frame,
            text="Loading...",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        )
        self.alone_stats.pack(anchor="w", padx=15, pady=(2, 8))

        # Dialogue section
        dialogue_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("kay", "#6BB6B6")
        )
        dialogue_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            dialogue_frame,
            text="What emerges in DIALOGUE:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("kay", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.dialogue_stats = ctk.CTkLabel(
            dialogue_frame,
            text="Loading...",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        )
        self.dialogue_stats.pack(anchor="w", padx=15, pady=(2, 8))

        # Stability section
        stability_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("system", "#C4A574")
        )
        stability_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            stability_frame,
            text="Overall Stability:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("system", "#C4A574")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.stability_stats = ctk.CTkLabel(
            stability_frame,
            text="Loading...",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left"
        )
        self.stability_stats.pack(anchor="w", padx=15, pady=(2, 8))

        # Recommendation section
        rec_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        rec_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            rec_frame,
            text="Recommendation:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.recommendation_label = ctk.CTkLabel(
            rec_frame,
            text="Analyzing patterns...",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=350,
            justify="left"
        )
        self.recommendation_label.pack(anchor="w", padx=15, pady=(2, 10))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=10)

        self.detail_btn = ctk.CTkButton(
            btn_frame,
            text="📊 Detailed Report",
            command=self._show_detailed_report,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        )
        self.detail_btn.pack(side="left", expand=True, fill="x", padx=2)

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="↻ Refresh",
            command=self.refresh_analytics,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        )
        self.refresh_btn.pack(side="right", expand=True, fill="x", padx=2)

        # Status label for feedback
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.status_label.pack(pady=2)

    def refresh_analytics(self):
        """Refresh all analytics data."""
        try:
            # Get counts
            auto_count = 0
            conv_count = 0

            if self.autonomous_memory and hasattr(self.autonomous_memory, 'insights'):
                auto_count = len(self.autonomous_memory.insights)

            if self.memory_engine and hasattr(self.memory_engine, 'memories'):
                conv_count = len(self.memory_engine.memories)

            self.source_label.configure(
                text=f"Based on {auto_count} autonomous sessions and {conv_count:,} conversation facts:"
            )

            # Autonomous stats
            if self.autonomous_memory and auto_count > 0:
                stats = self.autonomous_memory.get_stats()
                convergence = stats.get("convergence_stats", {})

                natural = convergence.get("natural", 0) + convergence.get("natural_conclusion", 0) + convergence.get("explicit_completion", 0)
                block = convergence.get("creative_block", 0)
                energy = convergence.get("energy_limit", 0)
                total = max(natural + block + energy, 1)

                alone_text = (
                    f"Topics: {stats.get('unique_topics', 0)} unique\n"
                    f"Avg depth: {stats.get('avg_recursion_depth', 0):.1f} iterations\n"
                    f"Convergence: {natural/total:.0%} natural, {block/total:.0%} block, {energy/total:.0%} energy"
                )
                self.alone_stats.configure(text=alone_text)
            else:
                self.alone_stats.configure(text="No autonomous sessions yet")

            # Dialogue stats
            if conv_count > 0:
                dialogue_text = f"Facts stored: {conv_count:,}"
                self.dialogue_stats.configure(text=dialogue_text)
            else:
                self.dialogue_stats.configure(text="No conversation data yet")

            # Gap-based stability
            if self.gap_analyzer:
                gap_data = self.gap_analyzer.get_full_gap_analysis()
                analysis = gap_data.get("analysis", {})
                overlap_ratio = analysis.get("overlap_ratio", 0)

                if overlap_ratio > 0.5:
                    stability = f"High ({overlap_ratio:.0%} topic overlap)"
                    conclusion = "stable"
                elif overlap_ratio > 0.2:
                    stability = f"Moderate ({overlap_ratio:.0%} topic overlap)"
                    conclusion = "mixed"
                else:
                    stability = f"Context-dependent ({overlap_ratio:.0%} topic overlap)"
                    conclusion = "dependent"

                circling = 0
                if self.autonomous_memory:
                    stats = self.autonomous_memory.get_stats()
                    circling = stats.get("high_circling_count", 0)

                stability_text = (
                    f"Stability Score: {stability}\n"
                    f"Circling tendency: {'Low' if circling < 3 else 'Moderate' if circling < 10 else 'High'} "
                    f"({circling} high-circling insights)"
                )
                self.stability_stats.configure(text=stability_text)

                # Recommendation
                if conclusion == "stable":
                    rec = (
                        "Your core reasoning is consistent across contexts. "
                        "Both solo processing and dialogue reinforce similar insights."
                    )
                elif conclusion == "mixed":
                    rec = (
                        "Your thinking shows partial consistency. "
                        "Some conclusions are stable, but dialogue introduces new perspectives. "
                        "Consider autonomous sessions for foundational questions."
                    )
                else:
                    rec = (
                        "Your thinking differs significantly between contexts. "
                        "Solo processing may be most effective for self-referential questions, "
                        "while creative/social topics benefit from Re's presence."
                    )
                self.recommendation_label.configure(text=rec)
            else:
                self.stability_stats.configure(text="Run gap analysis to calculate")
                self.recommendation_label.configure(text="Need more data for recommendations")

        except Exception as e:
            print(f"[ANALYTICS] Refresh error: {e}")
            import traceback
            traceback.print_exc()

    def _show_detailed_report(self):
        """Show detailed analytics report in modal window or export to file."""
        try:
            report_data = self._generate_detailed_report()

            # Create modal window for report
            report_window = DetailedReportWindow(
                self.winfo_toplevel(),
                self.palette,
                report_data,
                on_export=self._export_detailed_report
            )
            report_window.focus()

            self._show_status("✓ Detailed report generated", error=False)

        except Exception as e:
            error_msg = str(e)[:50]
            self._show_status(f"⚠ Report generation failed: {error_msg}", error=True)
            print(f"[ANALYTICS] Report error: {e}")
            import traceback
            traceback.print_exc()

    def _generate_detailed_report(self) -> Dict:
        """Generate comprehensive cognitive pattern analysis data."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "autonomous_analysis": {},
            "convergence_stats": {},
            "topic_analysis": {},
            "stability_metrics": {},
            "recommendations": []
        }

        # Get autonomous stats
        auto_count = 0
        conv_count = 0

        if self.autonomous_memory and hasattr(self.autonomous_memory, 'insights'):
            auto_count = len(self.autonomous_memory.insights)
            stats = self.autonomous_memory.get_stats()

            report["autonomous_analysis"] = {
                "total_insights": auto_count,
                "unique_topics": stats.get("unique_topics", 0),
                "avg_recursion_depth": stats.get("avg_recursion_depth", 0),
                "high_circling_count": stats.get("high_circling_count", 0),
                "total_sessions": stats.get("total_sessions", 0)
            }

            # Convergence breakdown
            convergence = stats.get("convergence_stats", {})
            natural = convergence.get("natural", 0) + convergence.get("natural_conclusion", 0) + convergence.get("explicit_completion", 0)
            block = convergence.get("creative_block", 0)
            energy = convergence.get("energy_limit", 0)
            total = max(natural + block + energy, 1)

            report["convergence_stats"] = {
                "natural_completion": natural,
                "natural_completion_pct": round(natural / total * 100, 1),
                "creative_block": block,
                "creative_block_pct": round(block / total * 100, 1),
                "energy_limit": energy,
                "energy_limit_pct": round(energy / total * 100, 1),
                "total_sessions": total
            }

            # Topic frequency
            topic_freq = self.autonomous_memory.get_topic_frequency()
            report["topic_analysis"]["autonomous_topics"] = dict(list(topic_freq.items())[:20])

        if self.memory_engine and hasattr(self.memory_engine, 'memories'):
            conv_count = len(self.memory_engine.memories)

        report["summary"] = {
            "autonomous_insights": auto_count,
            "conversation_facts": conv_count,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # Gap-based stability
        if self.gap_analyzer:
            gap_data = self.gap_analyzer.get_full_gap_analysis()
            analysis = gap_data.get("analysis", {})

            report["stability_metrics"] = {
                "overlap_ratio": analysis.get("overlap_ratio", 0),
                "autonomous_unique_ratio": analysis.get("autonomous_unique_ratio", 0),
                "conversation_unique_ratio": analysis.get("conversation_unique_ratio", 0),
                "stability_classification": self._classify_stability(analysis.get("overlap_ratio", 0))
            }

            report["topic_analysis"]["autonomous_only"] = gap_data.get("autonomous_only", {}).get("topics", [])[:10]
            report["topic_analysis"]["conversation_only"] = gap_data.get("conversation_only", {}).get("topics", [])[:10]
            report["topic_analysis"]["overlap"] = gap_data.get("overlap", {}).get("topics", [])[:10]

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        return report

    def _classify_stability(self, overlap_ratio: float) -> str:
        """Classify stability based on overlap ratio."""
        if overlap_ratio > 0.5:
            return "stable"
        elif overlap_ratio > 0.2:
            return "moderately_stable"
        else:
            return "context_dependent"

    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate actionable recommendations based on pattern analysis."""
        recommendations = []

        # Based on convergence patterns
        conv_stats = report.get("convergence_stats", {})
        if conv_stats.get("creative_block_pct", 0) > 30:
            recommendations.append(
                "High creative block rate detected. Consider more focused goal prompts "
                "or shorter session durations."
            )

        if conv_stats.get("energy_limit_pct", 0) > 40:
            recommendations.append(
                "Many sessions hit energy limits. Kay may benefit from longer session "
                "allowances or breaking complex topics into sub-goals."
            )

        if conv_stats.get("natural_completion_pct", 0) > 70:
            recommendations.append(
                "Strong natural completion rate. Kay's autonomous processing is "
                "reaching satisfying conclusions effectively."
            )

        # Based on stability
        stability = report.get("stability_metrics", {})
        classification = stability.get("stability_classification", "")

        if classification == "stable":
            recommendations.append(
                "Cognitive stability is high. Kay's reasoning is consistent "
                "whether alone or in dialogue."
            )
        elif classification == "context_dependent":
            recommendations.append(
                "Significant context dependence detected. Autonomous sessions "
                "may explore different aspects than conversation. This isn't "
                "necessarily problematic - it may indicate complementary thinking modes."
            )

        # Based on topic patterns
        auto_analysis = report.get("autonomous_analysis", {})
        if auto_analysis.get("high_circling_count", 0) > 5:
            recommendations.append(
                "Moderate circling tendency detected. Kay sometimes revisits "
                "the same concepts. Consider prompts that encourage new angles."
            )

        if auto_analysis.get("avg_recursion_depth", 0) < 2:
            recommendations.append(
                "Low average iteration depth. Kay may be reaching conclusions "
                "quickly. Consider more complex exploratory goals."
            )

        if not recommendations:
            recommendations.append(
                "Not enough data for specific recommendations yet. "
                "Continue running autonomous sessions to build pattern history."
            )

        return recommendations

    def _export_detailed_report(self, report_data: Dict) -> Tuple[str, bool]:
        """Export detailed report to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = Path(f"memory/detailed_pattern_report_{timestamp}.json")
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            return str(export_path), True

        except Exception as e:
            return str(e), False

    def _show_status(self, message: str, error: bool = False):
        """Show status message with appropriate color."""
        color = self.palette.get("user", "#D499B9") if error else self.palette.get("accent", "#4A9B9B")
        self.status_label.configure(text=message, text_color=color)

        # Auto-clear after 5 seconds
        self.after(5000, lambda: self.status_label.configure(text=""))


class DetailedReportWindow(ctk.CTkToplevel):
    """
    Modal window displaying detailed cognitive pattern report.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        report_data: Dict,
        on_export: Optional[Callable] = None
    ):
        super().__init__(parent)

        self.palette = palette
        self.report_data = report_data
        self.on_export = on_export

        self.title("Detailed Cognitive Pattern Report")
        self.geometry("700x800")
        self.configure(fg_color=palette.get("bg", "#1A0F24"))

        self._build_ui()

    def _build_ui(self):
        """Build the report window UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 25 + "\n📊 DETAILED COGNITIVE PATTERN REPORT\n" + "━" * 25,
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=15)

        # Scroll container
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True, padx=15)

        # Summary section
        self._add_section(scroll, "SUMMARY", self._format_summary())

        # Autonomous Analysis
        self._add_section(scroll, "AUTONOMOUS PROCESSING", self._format_autonomous())

        # Convergence Stats
        self._add_section(scroll, "CONVERGENCE PATTERNS", self._format_convergence())

        # Topic Analysis
        self._add_section(scroll, "TOPIC ANALYSIS", self._format_topics())

        # Stability Metrics
        self._add_section(scroll, "STABILITY METRICS", self._format_stability())

        # Recommendations
        self._add_section(scroll, "RECOMMENDATIONS", self._format_recommendations())

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        export_btn = ctk.CTkButton(
            btn_frame,
            text="📤 Export to File",
            command=self._handle_export,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        )
        export_btn.pack(side="left", expand=True, fill="x", padx=5)

        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            command=self.destroy,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=32
        )
        close_btn.pack(side="right", expand=True, fill="x", padx=5)

        # Export status label
        self.export_status = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.export_status.pack(pady=5)

    def _add_section(self, parent, title: str, content: str):
        """Add a report section."""
        frame = ctk.CTkFrame(
            parent,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            frame,
            text=content,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            justify="left",
            wraplength=620
        ).pack(anchor="w", padx=15, pady=(2, 10))

    def _format_summary(self) -> str:
        """Format summary section."""
        summary = self.report_data.get("summary", {})
        return (
            f"Analysis Date: {summary.get('analysis_date', 'Unknown')}\n"
            f"Autonomous Insights: {summary.get('autonomous_insights', 0)}\n"
            f"Conversation Facts: {summary.get('conversation_facts', 0):,}"
        )

    def _format_autonomous(self) -> str:
        """Format autonomous analysis section."""
        auto = self.report_data.get("autonomous_analysis", {})
        if not auto:
            return "No autonomous session data available yet."

        return (
            f"Total Insights: {auto.get('total_insights', 0)}\n"
            f"Unique Topics: {auto.get('unique_topics', 0)}\n"
            f"Average Recursion Depth: {auto.get('avg_recursion_depth', 0):.1f} iterations\n"
            f"High-Circling Insights: {auto.get('high_circling_count', 0)}"
        )

    def _format_convergence(self) -> str:
        """Format convergence stats section."""
        conv = self.report_data.get("convergence_stats", {})
        if not conv:
            return "No convergence data available yet."

        return (
            f"Natural Completion: {conv.get('natural_completion', 0)} ({conv.get('natural_completion_pct', 0)}%)\n"
            f"Creative Block: {conv.get('creative_block', 0)} ({conv.get('creative_block_pct', 0)}%)\n"
            f"Energy Limit: {conv.get('energy_limit', 0)} ({conv.get('energy_limit_pct', 0)}%)\n"
            f"Total Sessions: {conv.get('total_sessions', 0)}"
        )

    def _format_topics(self) -> str:
        """Format topic analysis section."""
        topics = self.report_data.get("topic_analysis", {})
        parts = []

        auto_only = topics.get("autonomous_only", [])
        if auto_only:
            parts.append("Autonomous-only topics:")
            parts.extend([f"  • {t}" for t in auto_only[:5]])

        conv_only = topics.get("conversation_only", [])
        if conv_only:
            parts.append("\nConversation-only topics:")
            parts.extend([f"  • {t}" for t in conv_only[:5]])

        overlap = topics.get("overlap", [])
        if overlap:
            parts.append("\nOverlap topics:")
            parts.extend([f"  • {t}" for t in overlap[:5]])

        auto_topics = topics.get("autonomous_topics", {})
        if auto_topics:
            parts.append("\nMost frequent autonomous topics:")
            for topic, count in list(auto_topics.items())[:5]:
                parts.append(f"  • {topic} ({count} occurrences)")

        return "\n".join(parts) if parts else "No topic data available yet."

    def _format_stability(self) -> str:
        """Format stability metrics section."""
        stability = self.report_data.get("stability_metrics", {})
        if not stability:
            return "Run gap analysis to calculate stability metrics."

        classification = stability.get("stability_classification", "unknown")
        classification_display = {
            "stable": "STABLE - Consistent reasoning across contexts",
            "moderately_stable": "MODERATELY STABLE - Some context variation",
            "context_dependent": "CONTEXT DEPENDENT - Different thinking in different modes"
        }.get(classification, classification)

        return (
            f"Classification: {classification_display}\n"
            f"Topic Overlap Ratio: {stability.get('overlap_ratio', 0):.1%}\n"
            f"Autonomous-Unique Ratio: {stability.get('autonomous_unique_ratio', 0):.1%}\n"
            f"Conversation-Unique Ratio: {stability.get('conversation_unique_ratio', 0):.1%}"
        )

    def _format_recommendations(self) -> str:
        """Format recommendations section."""
        recommendations = self.report_data.get("recommendations", [])
        if not recommendations:
            return "No recommendations available yet."

        parts = []
        for i, rec in enumerate(recommendations, 1):
            parts.append(f"{i}. {rec}")

        return "\n\n".join(parts)

    def _handle_export(self):
        """Handle export button click."""
        if self.on_export:
            filepath, success = self.on_export(self.report_data)
            if success:
                self.export_status.configure(
                    text=f"✓ Exported to {Path(filepath).name}",
                    text_color=self.palette.get("accent", "#4A9B9B")
                )
            else:
                self.export_status.configure(
                    text=f"⚠ Export failed: {filepath}",
                    text_color=self.palette.get("user", "#D499B9")
                )

            # Auto-clear after 5 seconds
            self.after(5000, lambda: self.export_status.configure(text=""))


class AutonomousSettingsPanel(ctk.CTkFrame):
    """
    Settings panel for autonomous processing configuration.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        config: Any = None,
        on_save: Optional[Callable] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.config = config
        self.on_save = on_save

        self._build_ui()

    def _build_ui(self):
        """Build the settings UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="AUTONOMOUS PROCESSING SETTINGS",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        header.pack(pady=10)

        ctk.CTkLabel(
            self,
            text="━" * 30,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack()

        # Settings container
        settings_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        settings_frame.pack(fill="x", padx=5, pady=10)

        # Auto-trigger setting
        self.auto_trigger_var = ctk.BooleanVar(value=False)
        self.auto_trigger_check = ctk.CTkCheckBox(
            settings_frame,
            text="Auto-trigger autonomous after conversation ends",
            variable=self.auto_trigger_var,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.auto_trigger_check.pack(anchor="w", padx=10, pady=5)

        # Show insights in main conversation
        self.show_insights_var = ctk.BooleanVar(value=False)
        self.show_insights_check = ctk.CTkCheckBox(
            settings_frame,
            text="Show autonomous insights in main conversation",
            variable=self.show_insights_var,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.show_insights_check.pack(anchor="w", padx=10, pady=5)

        # Keep tiers separate (Kay's recommendation)
        self.separate_tiers_var = ctk.BooleanVar(value=True)
        self.separate_tiers_check = ctk.CTkCheckBox(
            settings_frame,
            text="Keep autonomous tier separate (recommended)",
            variable=self.separate_tiers_var,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.separate_tiers_check.pack(anchor="w", padx=10, pady=5)

        # Track cognitive gaps
        self.track_gaps_var = ctk.BooleanVar(value=True)
        self.track_gaps_check = ctk.CTkCheckBox(
            settings_frame,
            text="Track cognitive gaps (topics only in one context)",
            variable=self.track_gaps_var,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.track_gaps_check.pack(anchor="w", padx=10, pady=5)

        # Alert threshold
        self.alert_threshold_var = ctk.BooleanVar(value=False)
        self.alert_threshold_check = ctk.CTkCheckBox(
            settings_frame,
            text="Alert when autonomous-only topics reach 3+ sessions",
            variable=self.alert_threshold_var,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.alert_threshold_check.pack(anchor="w", padx=10, pady=5)

        # Separator
        ctk.CTkLabel(settings_frame, text="").pack(pady=3)

        # Max iterations slider
        iter_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        iter_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            iter_frame,
            text="Maximum autonomous iterations:",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(side="left")

        self.max_iter_var = ctk.IntVar(value=10)
        self.max_iter_label = ctk.CTkLabel(
            iter_frame,
            text="10",
            font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
            text_color=self.palette.get("accent", "#4A9B9B"),
            width=30
        )
        self.max_iter_label.pack(side="right")

        self.max_iter_slider = ctk.CTkSlider(
            iter_frame,
            from_=3,
            to=20,
            number_of_steps=17,
            variable=self.max_iter_var,
            command=lambda v: self.max_iter_label.configure(text=str(int(v))),
            width=100,
            progress_color=self.palette.get("accent", "#4A9B9B"),
            button_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        self.max_iter_slider.pack(side="right", padx=10)

        # Convergence sensitivity
        sens_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        sens_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            sens_frame,
            text="Convergence sensitivity:",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(side="left")

        self.sensitivity_var = ctk.StringVar(value="Medium")
        for text in ["Low", "Medium", "High"]:
            rb = ctk.CTkRadioButton(
                sens_frame,
                text=text,
                variable=self.sensitivity_var,
                value=text,
                font=ctk.CTkFont(family="Courier", size=9),
                text_color=self.palette.get("muted", "#9B7D54"),
                fg_color=self.palette.get("accent", "#4A9B9B")
            )
            rb.pack(side="right", padx=5)

        # Save button
        save_btn = ctk.CTkButton(
            self,
            text="💾 Save Settings",
            command=self._save_settings,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        )
        save_btn.pack(fill="x", padx=5, pady=10)

    def _save_settings(self):
        """Save current settings."""
        settings = {
            "auto_trigger": self.auto_trigger_var.get(),
            "show_insights": self.show_insights_var.get(),
            "separate_tiers": self.separate_tiers_var.get(),
            "track_gaps": self.track_gaps_var.get(),
            "alert_threshold": self.alert_threshold_var.get(),
            "max_iterations": self.max_iter_var.get(),
            "convergence_sensitivity": self.sensitivity_var.get()
        }

        if self.on_save:
            self.on_save(settings)

        # Save to file
        try:
            settings_path = Path("memory/autonomous_settings.json")
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            print("[SETTINGS] Autonomous settings saved")
        except Exception as e:
            print(f"[SETTINGS] Save error: {e}")

    def load_settings(self):
        """Load saved settings."""
        try:
            settings_path = Path("memory/autonomous_settings.json")
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                self.auto_trigger_var.set(settings.get("auto_trigger", False))
                self.show_insights_var.set(settings.get("show_insights", False))
                self.separate_tiers_var.set(settings.get("separate_tiers", True))
                self.track_gaps_var.set(settings.get("track_gaps", True))
                self.alert_threshold_var.set(settings.get("alert_threshold", False))
                self.max_iter_var.set(settings.get("max_iterations", 10))
                self.max_iter_label.configure(text=str(settings.get("max_iterations", 10)))
                self.sensitivity_var.set(settings.get("convergence_sensitivity", "Medium"))
        except Exception as e:
            print(f"[SETTINGS] Load error: {e}")


class EnhancedSessionDetailView(ctk.CTkToplevel):
    """
    Enhanced session detail view showing full autonomous session metadata.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        session_data: Dict,
        autonomous_memory: Any = None
    ):
        super().__init__(parent)

        self.palette = palette
        self.session_data = session_data
        self.autonomous_memory = autonomous_memory

        self.title("Autonomous Session Detail")
        self.geometry("700x800")
        self.configure(fg_color=palette.get("bg", "#1A0F24"))

        self._build_ui()

    def _build_ui(self):
        """Build the enhanced session detail UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="━" * 25 + "\n🧠 AUTONOMOUS SESSION DETAIL\n" + "━" * 25,
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6"),
            justify="center"
        )
        header.pack(pady=15)

        # Scroll container
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True, padx=15)

        # Session info frame
        info_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        info_frame.pack(fill="x", pady=5)

        # Session ID and timing
        session_id = self.session_data.get("session_id", "Unknown")
        started = self.session_data.get("started_at", "Unknown")
        ended = self.session_data.get("ended_at", "")

        try:
            start_dt = datetime.fromisoformat(started)
            started_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            if ended:
                end_dt = datetime.fromisoformat(ended)
                duration = (end_dt - start_dt).total_seconds()
                duration_str = f"{duration:.0f} seconds"
            else:
                duration_str = "In progress"
        except:
            started_str = started[:19] if len(started) > 19 else started
            duration_str = "Unknown"

        self._add_info_row(info_frame, "Session ID:", f"auto_{session_id}")
        self._add_info_row(info_frame, "Started:", started_str)
        self._add_info_row(info_frame, "Duration:", duration_str)

        # Goal section
        goal_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("accent", "#4A9B9B")
        )
        goal_frame.pack(fill="x", pady=5)

        goal = self.session_data.get("goal", {})
        goal_text = goal.get("description", "Unknown") if isinstance(goal, dict) else str(goal)
        goal_category = goal.get("category", "Unknown") if isinstance(goal, dict) else "Unknown"

        ctk.CTkLabel(
            goal_frame,
            text="Goal:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 2))

        ctk.CTkLabel(
            goal_frame,
            text=goal_text,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            wraplength=620,
            justify="left"
        ).pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(
            goal_frame,
            text=f"Goal Source: ✓ Self-generated",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("system", "#C4A574")
        ).pack(anchor="w", padx=15, pady=(2, 10))

        # Processing metrics frame
        metrics_frame = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        metrics_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            metrics_frame,
            text="Processing Metrics:",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 2))

        iterations = self.session_data.get("iterations_used", 0)
        completion_type = goal.get("completion_type", "Unknown") if isinstance(goal, dict) else "Unknown"

        # Convergence type with icon
        conv_icons = {
            "natural": "✓",
            "natural_conclusion": "✓",
            "explicit_completion": "✓",
            "creative_block": "⚠",
            "energy_limit": "⏳",
            "novelty_exhaustion": "💤"
        }
        conv_icon = conv_icons.get(completion_type, "●")

        self._add_metric_row(metrics_frame, "Recursion depth:", f"{iterations} iterations")
        self._add_metric_row(metrics_frame, "Convergence type:", f"{conv_icon} {completion_type.replace('_', ' ').title()}")
        self._add_metric_row(metrics_frame, "Constraints active:", "budget_limit, no_external_input")

        ctk.CTkLabel(metrics_frame, text="").pack(pady=3)

        # Insights section
        insights = goal.get("insights", []) if isinstance(goal, dict) else []
        if insights:
            insights_frame = ctk.CTkFrame(
                scroll,
                fg_color=self.palette.get("input", "#4A2B5C"),
                corner_radius=0,
                border_width=1,
                border_color=self.palette.get("accent", "#4A9B9B")
            )
            insights_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                insights_frame,
                text=f"Insights Generated: {len(insights)}",
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            ).pack(anchor="w", padx=10, pady=(10, 5))

            for insight in insights:
                ctk.CTkLabel(
                    insights_frame,
                    text=f"  → \"{insight[:150]}{'...' if len(insight) > 150 else ''}\"",
                    font=ctk.CTkFont(family="Courier", size=9),
                    text_color=self.palette.get("text", "#E8DCC4"),
                    wraplength=600,
                    justify="left"
                ).pack(anchor="w", padx=10, pady=2)

            ctk.CTkLabel(insights_frame, text="").pack(pady=5)

        # Thought history section
        thoughts = self.session_data.get("thoughts", [])
        if thoughts:
            thoughts_frame = ctk.CTkFrame(
                scroll,
                fg_color=self.palette.get("panel", "#2D1B3D"),
                corner_radius=0,
                border_width=1,
                border_color=self.palette.get("muted", "#9B7D54")
            )
            thoughts_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                thoughts_frame,
                text="💭 Thought History",
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            ).pack(anchor="w", padx=10, pady=(10, 5))

            for i, thought in enumerate(thoughts, 1):
                thought_card = ctk.CTkFrame(
                    thoughts_frame,
                    fg_color=self.palette.get("bg", "#1A0F24"),
                    corner_radius=0
                )
                thought_card.pack(fill="x", padx=10, pady=3)

                ctk.CTkLabel(
                    thought_card,
                    text=f"Iteration {i}",
                    font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                    text_color=self.palette.get("accent", "#4A9B9B")
                ).pack(anchor="w", padx=8, pady=(5, 2))

                inner = thought.get("inner_monologue", "")
                if inner:
                    ctk.CTkLabel(
                        thought_card,
                        text=f"💭 {inner[:200]}{'...' if len(inner) > 200 else ''}",
                        font=ctk.CTkFont(family="Courier", size=9),
                        text_color=self.palette.get("text", "#E8DCC4"),
                        wraplength=580,
                        justify="left"
                    ).pack(anchor="w", padx=8, pady=2)

                feeling = thought.get("feeling", "")
                if feeling:
                    ctk.CTkLabel(
                        thought_card,
                        text=f"🫀 {feeling}",
                        font=ctk.CTkFont(family="Courier", size=9),
                        text_color=self.palette.get("user", "#D499B9")
                    ).pack(anchor="w", padx=8, pady=2)

                insight = thought.get("insight", "")
                if insight:
                    ctk.CTkLabel(
                        thought_card,
                        text=f"💡 {insight}",
                        font=ctk.CTkFont(family="Courier", size=9),
                        text_color=self.palette.get("accent_hi", "#6BB6B6"),
                        wraplength=580
                    ).pack(anchor="w", padx=8, pady=(2, 5))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(
            btn_frame,
            text="📜 View Full Transcript",
            command=lambda: None,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(side="left", expand=True, fill="x", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="⚖️ Compare to Conversation",
            command=lambda: None,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(side="left", expand=True, fill="x", padx=2)

        ctk.CTkButton(
            btn_frame,
            text="Close",
            command=self.destroy,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            corner_radius=0,
            height=28
        ).pack(side="right", padx=2)

    def _add_info_row(self, parent, label: str, value: str):
        """Add an info row to parent frame."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            width=100,
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            anchor="w"
        ).pack(side="left")

    def _add_metric_row(self, parent, label: str, value: str):
        """Add a metric row to parent frame."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=1)

        ctk.CTkLabel(
            row,
            text=f"  {label}",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            width=140,
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("text", "#E8DCC4"),
            anchor="w"
        ).pack(side="left")
