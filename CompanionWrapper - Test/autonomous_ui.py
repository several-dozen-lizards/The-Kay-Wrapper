"""
Autonomous Processing UI Components for the entity

CustomTkinter-based UI components for:
- Inner monologue toggle and display
- Autonomous session controls
- Session status monitoring
- Session history view
- Debug/diagnostics panel
"""

import os
import json
import time
import threading
from typing import Dict, Optional, Callable, List, Any
from datetime import datetime
from pathlib import Path
import customtkinter as ctk


class AutonomousUIConfig:
    """UI configuration that persists across sessions."""

    CONFIG_FILE = "memory/autonomous_ui_config.json"

    def __init__(self):
        self.show_inner_monologue = False
        self.auto_offer_at_exit = True
        self.show_iteration_progress = True
        self.load()

    def load(self):
        """Load config from file."""
        try:
            if Path(self.CONFIG_FILE).exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.show_inner_monologue = data.get("show_inner_monologue", False)
                    self.auto_offer_at_exit = data.get("auto_offer_at_exit", True)
                    self.show_iteration_progress = data.get("show_iteration_progress", True)
        except Exception as e:
            print(f"[AUTONOMOUS UI] Config load error: {e}")

    def save(self):
        """Save config to file."""
        try:
            Path(self.CONFIG_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "show_inner_monologue": self.show_inner_monologue,
                    "auto_offer_at_exit": self.auto_offer_at_exit,
                    "show_iteration_progress": self.show_iteration_progress
                }, f, indent=2)
        except Exception as e:
            print(f"[AUTONOMOUS UI] Config save error: {e}")


class AutonomousControlPanel(ctk.CTkFrame):
    """
    Main control panel for autonomous processing features.

    Provides:
    - Inner monologue toggle
    - Start autonomous session button
    - Session status display
    - Quick diagnostics
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        on_start_session: Callable[[], None],
        on_toggle_monologue: Callable[[bool], None],
        on_test_system: Callable[[], None],
        config: Optional[AutonomousUIConfig] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.on_start_session = on_start_session
        self.on_toggle_monologue = on_toggle_monologue
        self.on_test_system = on_test_system
        self.config = config or AutonomousUIConfig()

        # State
        self.session_active = False
        self.current_iteration = 0
        self.max_iterations = 10

        self._build_ui()

    def _build_ui(self):
        """Build the control panel UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="⟨ AUTONOMOUS PROCESSING ⟩",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        header.pack(pady=(10, 5))

        # Inner Monologue Toggle Section
        monologue_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        monologue_frame.pack(fill="x", padx=5, pady=5)

        monologue_header = ctk.CTkLabel(
            monologue_frame,
            text="Inner Monologue",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        monologue_header.pack(anchor="w", padx=10, pady=(8, 2))

        self.monologue_var = ctk.BooleanVar(value=self.config.show_inner_monologue)
        self.monologue_checkbox = ctk.CTkCheckBox(
            monologue_frame,
            text="Show Inner Thoughts (God Mode)",
            variable=self.monologue_var,
            command=self._on_monologue_toggle,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4"),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            checkmark_color=self.palette.get("bg", "#1A0F24")
        )
        self.monologue_checkbox.pack(anchor="w", padx=10, pady=(2, 8))

        # Session Controls Section
        session_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        session_frame.pack(fill="x", padx=5, pady=5)

        session_header = ctk.CTkLabel(
            session_frame,
            text="Autonomous Session",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        session_header.pack(anchor="w", padx=10, pady=(8, 2))

        # Warmup Button
        self.warmup_btn = ctk.CTkButton(
            session_frame,
            text="🌅 Run Warmup",
            command=self._on_run_warmup,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("text", "#E8DCC4"),
            corner_radius=0,
            height=28
        )
        self.warmup_btn.pack(fill="x", padx=10, pady=(8, 4))

        # Curiosity Session Button
        self.curiosity_btn = ctk.CTkButton(
            session_frame,
            text="🔍 Start Curiosity Session",
            command=self._on_start_curiosity,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("text", "#E8DCC4"),
            corner_radius=0,
            height=28
        )
        self.curiosity_btn.pack(fill="x", padx=10, pady=4)

        self.start_session_btn = ctk.CTkButton(
            session_frame,
            text="🧠 Begin Autonomous Session",
            command=self._on_start_session,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.palette.get("accent", "#4A9B9B"),
            hover_color=self.palette.get("accent_hi", "#6BB6B6"),
            text_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            height=32
        )
        self.start_session_btn.pack(fill="x", padx=10, pady=8)

        # Status Display
        self.status_frame = ctk.CTkFrame(
            session_frame,
            fg_color=self.palette.get("bg", "#1A0F24"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        self.status_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Status: Idle",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.status_label.pack(anchor="w", padx=8, pady=4)

        self.iteration_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.iteration_label.pack(anchor="w", padx=8, pady=(0, 4))

        # Progress bar (hidden by default)
        self.progress_bar = ctk.CTkProgressBar(
            self.status_frame,
            progress_color=self.palette.get("accent", "#4A9B9B"),
            fg_color=self.palette.get("panel", "#2D1B3D"),
            height=8
        )
        self.progress_bar.set(0)

        # Last Thought Display
        self.thought_display = ctk.CTkTextbox(
            self.status_frame,
            height=60,
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=self.palette.get("panel", "#2D1B3D"),
            text_color=self.palette.get("text", "#E8DCC4"),
            border_width=0,
            wrap="word"
        )
        self.thought_display.pack(fill="x", padx=8, pady=(0, 8))
        self.thought_display.insert("1.0", "No active session")
        self.thought_display.configure(state="disabled")

        # Diagnostics Section
        diag_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        diag_frame.pack(fill="x", padx=5, pady=5)

        diag_header = ctk.CTkLabel(
            diag_frame,
            text="Diagnostics",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("text", "#E8DCC4")
        )
        diag_header.pack(anchor="w", padx=10, pady=(8, 2))

        self.test_btn = ctk.CTkButton(
            diag_frame,
            text="🔬 Test Autonomous System",
            command=self._on_test_system,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            text_color=self.palette.get("text", "#E8DCC4"),
            corner_radius=0,
            height=28
        )
        self.test_btn.pack(fill="x", padx=10, pady=(4, 8))

        self.diag_status = ctk.CTkLabel(
            diag_frame,
            text="✓ System ready",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("accent", "#4A9B9B")
        )
        self.diag_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_monologue_toggle(self):
        """Handle monologue toggle."""
        enabled = self.monologue_var.get()
        self.config.show_inner_monologue = enabled
        self.config.save()
        self.on_toggle_monologue(enabled)

    def _on_start_session(self):
        """Handle start session button."""
        if not self.session_active:
            self.on_start_session()

    def _on_run_warmup(self):
        """Handle warmup button - delegate to integration layer."""
        # This will be wired up in autonomous_ui_integration.py
        if hasattr(self, 'on_run_warmup'):
            self.on_run_warmup()

    def _on_start_curiosity(self):
        """Handle curiosity session button - delegate to integration layer."""
        # This will be wired up in autonomous_ui_integration.py
        if hasattr(self, 'on_start_curiosity'):
            self.on_start_curiosity()

    def _on_test_system(self):
        """Handle test system button."""
        self.on_test_system()

    def set_curiosity_active(self, active: bool):
        """Update UI when curiosity mode state changes."""
        if active:
            # Update curiosity button to show "End"
            self.curiosity_btn.configure(
                text="⏹ End Curiosity Session",
                fg_color=self.palette.get("muted", "#9B7D54"),
                hover_color=self.palette.get("accent", "#4A9B9B")
            )
            # Disable autonomous session button when curiosity is active
            self.start_session_btn.configure(
                text="⏸ Curiosity Mode Active",
                state="disabled",
                fg_color=self.palette.get("muted", "#9B7D54")
            )
            self.status_label.configure(
                text="Status: Curiosity session in progress",
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            )
        else:
            # Update curiosity button back to "Start"
            self.curiosity_btn.configure(
                text="🔍 Start Curiosity Session",
                fg_color=self.palette.get("button", "#4A2B5C"),
                hover_color=self.palette.get("accent", "#4A9B9B")
            )
            # Re-enable if no autonomous session running
            if not self.session_active:
                self.start_session_btn.configure(
                    text="🧠 Begin Autonomous Session",
                    state="normal",
                    fg_color=self.palette.get("accent", "#4A9B9B")
                )
                self.status_label.configure(
                    text="Status: Idle",
                    text_color=self.palette.get("muted", "#9B7D54")
                )

    def set_session_active(self, active: bool, goal: str = ""):
        """Update UI for session state change."""
        self.session_active = active

        if active:
            # Disable both autonomous and curiosity buttons when autonomous session starts
            self.start_session_btn.configure(
                text="⏳ Session in Progress...",
                state="disabled",
                fg_color=self.palette.get("muted", "#9B7D54")
            )
            self.curiosity_btn.configure(
                state="disabled",
                fg_color=self.palette.get("muted", "#9B7D54")
            )
            self.status_label.configure(
                text=f"Status: Processing",
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            )
            if goal:
                # Strip any XML tags from goal display
                import re
                clean_goal = re.sub(r'<[^>]+>', '', goal).strip()
                # Show more of the goal (200 chars instead of 100)
                display_goal = clean_goal[:200] + "..." if len(clean_goal) > 200 else clean_goal
                self.thought_display.configure(state="normal")
                self.thought_display.delete("1.0", "end")
                self.thought_display.insert("1.0", f"Goal: {display_goal}")
                self.thought_display.configure(state="disabled")

            self.progress_bar.pack(fill="x", padx=8, pady=4)
            self.progress_bar.set(0)
            self.iteration_label.configure(text="Iteration: 0/10")
        else:
            # Re-enable both buttons when autonomous session ends
            self.start_session_btn.configure(
                text="🧠 Begin Autonomous Session",
                state="normal",
                fg_color=self.palette.get("accent", "#4A9B9B")
            )
            self.curiosity_btn.configure(
                state="normal",
                fg_color=self.palette.get("button", "#4A2B5C")
            )
            self.status_label.configure(
                text="Status: Idle",
                text_color=self.palette.get("muted", "#9B7D54")
            )
            self.progress_bar.pack_forget()

    def update_iteration(self, iteration: int, max_iter: int, thought: str = ""):
        """Update iteration progress."""
        self.current_iteration = iteration
        self.max_iterations = max_iter

        self.iteration_label.configure(text=f"Iteration: {iteration}/{max_iter}")
        self.progress_bar.set(iteration / max_iter)

        if thought:
            self.thought_display.configure(state="normal")
            self.thought_display.delete("1.0", "end")
            self.thought_display.insert("1.0", f"💭 {thought[:150]}...")
            self.thought_display.configure(state="disabled")

    def set_diagnostic_status(self, status: str, success: bool = True):
        """Update diagnostic status display."""
        color = self.palette.get("accent", "#4A9B9B") if success else self.palette.get("user", "#D499B9")
        symbol = "✓" if success else "✗"
        self.diag_status.configure(text=f"{symbol} {status}", text_color=color)


class AutonomousSessionViewer(ctk.CTkToplevel):
    """
    Detailed viewer for autonomous session results.

    Shows:
    - Full thought history
    - Insights discovered
    - Emotional mapping
    - Session statistics
    """

    def __init__(self, parent, session_data: Dict, palette: Dict[str, str]):
        super().__init__(parent)

        self.session_data = session_data
        self.palette = palette

        self.title("Autonomous Session Details")
        self.geometry("600x700")
        self.configure(fg_color=palette.get("bg", "#1A0F24"))

        self._build_ui()

    def _build_ui(self):
        """Build the viewer UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="⟨ AUTONOMOUS SESSION DETAILS ⟩",
            font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        header.pack(pady=15)

        # Summary Section
        summary_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        summary_frame.pack(fill="x", padx=15, pady=10)

        goal = self.session_data.get("goal", {})
        goal_text = goal.get("description", "Unknown") if isinstance(goal, dict) else str(goal)

        for label, value in [
            ("Goal", goal_text[:80] + "..." if len(goal_text) > 80 else goal_text),
            ("Category", goal.get("category", "Unknown") if isinstance(goal, dict) else "Unknown"),
            ("Iterations", str(self.session_data.get("iterations_used", 0))),
            ("Completion", goal.get("completion_type", "Unknown") if isinstance(goal, dict) else "Unknown"),
            ("Started", self.session_data.get("started_at", "Unknown")),
        ]:
            row = ctk.CTkFrame(summary_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)

            ctk.CTkLabel(
                row,
                text=f"{label}:",
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color=self.palette.get("muted", "#9B7D54"),
                width=80
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(family="Courier", size=10),
                text_color=self.palette.get("text", "#E8DCC4"),
                wraplength=450
            ).pack(side="left", fill="x", expand=True)

        # Insights Section
        insights = goal.get("insights", []) if isinstance(goal, dict) else []
        if insights:
            insights_frame = ctk.CTkFrame(
                self,
                fg_color=self.palette.get("panel", "#2D1B3D"),
                corner_radius=0,
                border_width=1,
                border_color=self.palette.get("accent", "#4A9B9B")
            )
            insights_frame.pack(fill="x", padx=15, pady=10)

            ctk.CTkLabel(
                insights_frame,
                text="💡 Insights Discovered",
                font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            ).pack(anchor="w", padx=10, pady=(10, 5))

            for i, insight in enumerate(insights[:5], 1):
                ctk.CTkLabel(
                    insights_frame,
                    text=f"{i}. {insight[:150]}...",
                    font=ctk.CTkFont(family="Courier", size=10),
                    text_color=self.palette.get("text", "#E8DCC4"),
                    wraplength=550
                ).pack(anchor="w", padx=15, pady=2)

            ctk.CTkLabel(insights_frame, text="").pack(pady=5)  # Spacer

        # Thought History Section
        thoughts_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        thoughts_frame.pack(fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(
            thoughts_frame,
            text="💭 Thought History",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        thought_scroll = ctk.CTkScrollableFrame(
            thoughts_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        thought_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        thoughts = self.session_data.get("thoughts", [])
        for i, thought in enumerate(thoughts, 1):
            thought_card = ctk.CTkFrame(
                thought_scroll,
                fg_color=self.palette.get("input", "#4A2B5C"),
                corner_radius=0,
                border_width=1,
                border_color=self.palette.get("muted", "#9B7D54")
            )
            thought_card.pack(fill="x", pady=5)

            # Iteration number
            ctk.CTkLabel(
                thought_card,
                text=f"Iteration {i}",
                font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                text_color=self.palette.get("accent", "#4A9B9B")
            ).pack(anchor="w", padx=8, pady=(5, 2))

            # Inner monologue
            inner = thought.get("inner_monologue", "")
            if inner:
                ctk.CTkLabel(
                    thought_card,
                    text=f"💭 {inner[:200]}..." if len(inner) > 200 else f"💭 {inner}",
                    font=ctk.CTkFont(family="Courier", size=9),
                    text_color=self.palette.get("text", "#E8DCC4"),
                    wraplength=520
                ).pack(anchor="w", padx=8, pady=2)

            # Feeling
            feeling = thought.get("feeling", "")
            if feeling:
                ctk.CTkLabel(
                    thought_card,
                    text=f"🫀 {feeling}",
                    font=ctk.CTkFont(family="Courier", size=9),
                    text_color=self.palette.get("user", "#D499B9"),
                    wraplength=520
                ).pack(anchor="w", padx=8, pady=2)

            # Insight
            insight = thought.get("insight", "")
            if insight:
                ctk.CTkLabel(
                    thought_card,
                    text=f"💡 {insight}",
                    font=ctk.CTkFont(family="Courier", size=9),
                    text_color=self.palette.get("accent_hi", "#6BB6B6"),
                    wraplength=520
                ).pack(anchor="w", padx=8, pady=2)

            ctk.CTkLabel(thought_card, text="").pack(pady=2)  # Spacer

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


class AutonomousHistoryPanel(ctk.CTkFrame):
    """
    Panel showing autonomous session history.

    Allows viewing past sessions and their results.
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        session_dir: str = "memory/autonomous_sessions",
        on_view_session: Optional[Callable[[Dict], None]] = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.session_dir = Path(session_dir)
        self.on_view_session = on_view_session

        self._build_ui()
        self.refresh_sessions()

    def _build_ui(self):
        """Build the history panel UI."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            header_frame,
            text="⟨ SESSION HISTORY ⟩",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(side="left")

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="↻",
            command=self.refresh_sessions,
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            width=30,
            height=25,
            corner_radius=0
        )
        refresh_btn.pack(side="right")

        # Session list
        self.session_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        self.session_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Placeholder
        self.no_sessions_label = ctk.CTkLabel(
            self.session_scroll,
            text="No autonomous sessions yet",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        )

    def refresh_sessions(self):
        """Reload and display session history."""
        # Clear existing
        for widget in self.session_scroll.winfo_children():
            widget.destroy()

        # Load sessions
        sessions = self._load_sessions()

        if not sessions:
            self.no_sessions_label = ctk.CTkLabel(
                self.session_scroll,
                text="No autonomous sessions yet",
                font=ctk.CTkFont(family="Courier", size=10),
                text_color=self.palette.get("muted", "#9B7D54")
            )
            self.no_sessions_label.pack(pady=20)
            return

        for session in sessions[:20]:  # Show last 20
            self._create_session_card(session)

    def _load_sessions(self) -> List[Dict]:
        """Load session data from disk."""
        sessions = []

        if not self.session_dir.exists():
            return sessions

        for session_file in sorted(self.session_dir.glob("session_*.json"), reverse=True):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    sessions.append(json.load(f))
            except Exception as e:
                print(f"[AUTONOMOUS UI] Failed to load session {session_file}: {e}")

        return sessions

    def _create_session_card(self, session: Dict):
        """Create a card for a single session."""
        card = ctk.CTkFrame(
            self.session_scroll,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        card.pack(fill="x", pady=3)

        # Date/time
        started = session.get("started_at", "Unknown")
        try:
            dt = datetime.fromisoformat(started)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = started[:16] if len(started) > 16 else started

        ctk.CTkLabel(
            card,
            text=date_str,
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(anchor="w", padx=8, pady=(5, 0))

        # Goal summary
        goal = session.get("goal", {})
        goal_text = goal.get("description", "Unknown goal")[:60] if isinstance(goal, dict) else str(goal)[:60]

        ctk.CTkLabel(
            card,
            text=goal_text + "...",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("text", "#E8DCC4")
        ).pack(anchor="w", padx=8, pady=2)

        # Status row
        status_frame = ctk.CTkFrame(card, fg_color="transparent")
        status_frame.pack(fill="x", padx=8, pady=(0, 5))

        completion = goal.get("completion_type", "Unknown") if isinstance(goal, dict) else "Unknown"
        iterations = session.get("iterations_used", 0)

        # Status indicator
        status_color = {
            "natural": self.palette.get("accent", "#4A9B9B"),
            "creative_block": self.palette.get("user", "#D499B9"),
            "energy_limit": self.palette.get("system", "#C4A574"),
        }.get(completion, self.palette.get("muted", "#9B7D54"))

        ctk.CTkLabel(
            status_frame,
            text=f"● {completion} ({iterations} iter)",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=status_color
        ).pack(side="left")

        # View button
        view_btn = ctk.CTkButton(
            status_frame,
            text="View",
            command=lambda s=session: self._view_session(s),
            font=ctk.CTkFont(family="Courier", size=9),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            width=50,
            height=22,
            corner_radius=0
        )
        view_btn.pack(side="right")

    def _view_session(self, session: Dict):
        """Open detailed session viewer."""
        if self.on_view_session:
            self.on_view_session(session)
        else:
            # Default: open viewer window
            viewer = AutonomousSessionViewer(
                self.winfo_toplevel(),
                session,
                self.palette
            )
            viewer.focus()


class AutonomousStatusBar(ctk.CTkFrame):
    """
    Compact status bar for autonomous processing.

    Shows current status inline in the main UI.
    """

    def __init__(self, parent, palette: Dict[str, str]):
        super().__init__(parent, fg_color="transparent", height=25)

        self.palette = palette
        self._build_ui()

    def _build_ui(self):
        """Build the status bar UI."""
        # Indicator dot
        self.indicator = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.indicator.pack(side="left", padx=(5, 3))

        # Status text
        self.status_text = ctk.CTkLabel(
            self,
            text="Autonomous: Idle",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        self.status_text.pack(side="left")

    def set_status(self, status: str, active: bool = False):
        """Update status display."""
        if active:
            self.indicator.configure(text_color=self.palette.get("accent_hi", "#6BB6B6"))
            self.status_text.configure(
                text=f"Autonomous: {status}",
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            )
        else:
            self.indicator.configure(text_color=self.palette.get("muted", "#9B7D54"))
            self.status_text.configure(
                text=f"Autonomous: {status}",
                text_color=self.palette.get("muted", "#9B7D54")
            )


class InnerMonologueFormatter:
    """
    Utility class for formatting responses with inner monologue.

    Handles the display formatting when god mode is enabled/disabled.
    """

    def __init__(self, palette: Dict[str, str]):
        self.palette = palette

    def format_response(
        self,
        response: str,
        parsed: Optional[Dict] = None,
        show_inner: bool = False
    ) -> str:
        """
        Format response for display.

        Args:
            response: Raw response text
            parsed: Pre-parsed response dict (inner_monologue, feeling, spoken)
            show_inner: Whether to show inner monologue

        Returns:
            Formatted string for display
        """
        if not show_inner:
            # Just return spoken response
            if parsed and parsed.get("spoken_response"):
                return parsed["spoken_response"]
            return response

        # Show all components
        parts = []

        if parsed:
            if parsed.get("inner_monologue"):
                parts.append(f"💭 [Inner] {parsed['inner_monologue']}")

            if parsed.get("feeling"):
                parts.append(f"🫀 [Feeling] {parsed['feeling']}")

            if parsed.get("spoken_response"):
                parts.append(f"💬 {parsed['spoken_response']}")

            if parts:
                return "\n\n".join(parts)

        return response

    def get_tag_config(self, textbox: ctk.CTkTextbox) -> Dict[str, Dict]:
        """
        Get tag configurations for rich text display.

        Returns dict of tag_name -> config_dict
        """
        return {
            "inner": {
                "foreground": self.palette.get("muted", "#9B7D54"),
            },
            "feeling": {
                "foreground": self.palette.get("user", "#D499B9"),
            },
            "spoken": {
                "foreground": self.palette.get("entity", "#6BB6B6"),
            }
        }


class MemoryDistributionPanel(ctk.CTkFrame):
    """
    Panel showing memory distribution between conversation and autonomous tiers.

    Implements the specification:
    - Conversation: X facts
    - Autonomous: Y insights
    - Overlap topics: Z
    - Autonomous-only: N
    """

    def __init__(
        self,
        parent,
        palette: Dict[str, str],
        memory_engine: Any = None,
        autonomous_memory: Any = None,
        gap_analyzer: Any = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.palette = palette
        self.memory_engine = memory_engine
        self.autonomous_memory = autonomous_memory
        self.gap_analyzer = gap_analyzer

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        """Build the distribution panel UI."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            header_frame,
            text="⟨ MEMORY DISTRIBUTION ⟩",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        ).pack(side="left")

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="↻",
            command=self.refresh_stats,
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color=self.palette.get("button", "#4A2B5C"),
            hover_color=self.palette.get("accent", "#4A9B9B"),
            width=30,
            height=25,
            corner_radius=0
        )
        refresh_btn.pack(side="right")

        # Stats frame
        self.stats_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("input", "#4A2B5C"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        self.stats_frame.pack(fill="x", padx=5, pady=5)

        # Separator line (visual)
        separator = ctk.CTkLabel(
            self.stats_frame,
            text="━" * 24,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        separator.pack(pady=(8, 4))

        # Conversation count
        self.conv_row = self._create_stat_row(
            "Conversation:",
            "0 facts",
            self.palette.get("text", "#E8DCC4")
        )

        # Autonomous count
        self.auto_row = self._create_stat_row(
            "Autonomous:",
            "0 insights",
            self.palette.get("accent", "#4A9B9B")
        )

        # Overlap topics
        self.overlap_row = self._create_stat_row(
            "Overlap topics:",
            "0",
            self.palette.get("system", "#C4A574")
        )

        # Autonomous-only
        self.auto_only_row = self._create_stat_row(
            "Autonomous-only:",
            "0",
            self.palette.get("user", "#D499B9")
        )

        # Separator line (visual)
        separator2 = ctk.CTkLabel(
            self.stats_frame,
            text="━" * 24,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        )
        separator2.pack(pady=(4, 8))

        # Gap analysis section (expandable)
        self.gap_frame = ctk.CTkFrame(
            self,
            fg_color=self.palette.get("panel", "#2D1B3D"),
            corner_radius=0,
            border_width=1,
            border_color=self.palette.get("muted", "#9B7D54")
        )
        self.gap_frame.pack(fill="x", padx=5, pady=5)

        gap_header = ctk.CTkLabel(
            self.gap_frame,
            text="Gap Analysis",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.palette.get("accent_hi", "#6BB6B6")
        )
        gap_header.pack(anchor="w", padx=10, pady=(8, 4))

        # Autonomous-only topics display
        self.auto_topics_label = ctk.CTkLabel(
            self.gap_frame,
            text="Autonomous-only topics:\n  (none yet)",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            justify="left"
        )
        self.auto_topics_label.pack(anchor="w", padx=10, pady=2)

        # Overlap topics display
        self.overlap_topics_label = ctk.CTkLabel(
            self.gap_frame,
            text="Shared topics:\n  (none yet)",
            font=ctk.CTkFont(family="Courier", size=9),
            text_color=self.palette.get("muted", "#9B7D54"),
            justify="left"
        )
        self.overlap_topics_label.pack(anchor="w", padx=10, pady=(2, 8))

    def _create_stat_row(self, label: str, value: str, value_color: str) -> Dict:
        """Create a stat row and return references to update it."""
        row = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)

        label_widget = ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54"),
            width=120,
            anchor="w"
        )
        label_widget.pack(side="left")

        value_widget = ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=value_color,
            anchor="e"
        )
        value_widget.pack(side="right")

        return {"label": label_widget, "value": value_widget, "color": value_color}

    def refresh_stats(self):
        """Refresh memory distribution statistics."""
        try:
            # Get conversation memory count
            conv_count = 0
            if self.memory_engine:
                if hasattr(self.memory_engine, 'memories'):
                    conv_count = len(self.memory_engine.memories)

            # Get autonomous memory count
            auto_count = 0
            if self.autonomous_memory:
                if hasattr(self.autonomous_memory, 'insights'):
                    auto_count = len(self.autonomous_memory.insights)

            # Get gap analysis
            overlap_count = 0
            auto_only_count = 0
            auto_only_topics = []
            overlap_topics = []

            if self.gap_analyzer:
                try:
                    gap_data = self.gap_analyzer.get_full_gap_analysis()
                    overlap_count = gap_data.get("overlap", {}).get("count", 0)
                    auto_only_count = gap_data.get("autonomous_only", {}).get("count", 0)
                    auto_only_topics = gap_data.get("autonomous_only", {}).get("topics", [])[:8]
                    overlap_topics = gap_data.get("overlap", {}).get("topics", [])[:8]
                except Exception as e:
                    print(f"[MEMORY DIST] Gap analysis error: {e}")

            # Update UI
            self.conv_row["value"].configure(text=f"{conv_count:,} facts")
            self.auto_row["value"].configure(text=f"{auto_count:,} insights")
            self.overlap_row["value"].configure(text=str(overlap_count))
            self.auto_only_row["value"].configure(text=str(auto_only_count))

            # Update topic displays
            if auto_only_topics:
                topics_text = "Autonomous-only topics:\n  " + ", ".join(auto_only_topics[:8])
                if len(auto_only_topics) > 8:
                    topics_text += "..."
            else:
                topics_text = "Autonomous-only topics:\n  (none yet)"
            self.auto_topics_label.configure(text=topics_text)

            if overlap_topics:
                overlap_text = "Shared topics:\n  " + ", ".join(overlap_topics[:8])
                if len(overlap_topics) > 8:
                    overlap_text += "..."
            else:
                overlap_text = "Shared topics:\n  (none yet)"
            self.overlap_topics_label.configure(text=overlap_text)

        except Exception as e:
            print(f"[MEMORY DIST] Refresh error: {e}")
            import traceback
            traceback.print_exc()

    def set_engines(
        self,
        memory_engine: Any = None,
        autonomous_memory: Any = None,
        gap_analyzer: Any = None
    ):
        """Update engine references and refresh."""
        if memory_engine:
            self.memory_engine = memory_engine
        if autonomous_memory:
            self.autonomous_memory = autonomous_memory
        if gap_analyzer:
            self.gap_analyzer = gap_analyzer
        self.refresh_stats()
