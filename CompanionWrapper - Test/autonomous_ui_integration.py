"""
Autonomous UI Integration Helper for the entity

This module provides integration functions to add autonomous processing
capabilities to kay_ui.py with minimal changes to the existing code.

USAGE:
------
In kay_ui.py, add these imports at the top:

    from autonomous_ui_integration import (
        AutonomousUIIntegration,
        setup_autonomous_ui
    )

Then in KayApp.__init__, after other initializations:

    # Initialize autonomous processing UI
    self.autonomous_ui = setup_autonomous_ui(self)

And in create_tabs_bar, add the autonomous tab button:

    ("🧠 Auto", self.toggle_autonomous_tab)

Then add these methods to the entityApp class:

    def toggle_autonomous_tab(self):
        self.show_panel_on_right("autonomous", self.autonomous_ui.create_panel_content)

"""

import os
import json
import time
import asyncio
import threading
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from pathlib import Path


class AutonomousUIIntegration:
    """
    Integration layer between autonomous processing and kay_ui.py

    Handles:
    - UI component creation
    - Event routing between UI and autonomous processor
    - State management
    - Display formatting with inner monologue support
    """

    def __init__(self, app):
        """
        Initialize integration with CompanionApp instance.

        Args:
            app: CompanionApp instance (from companion_ui.py)
        """
        self.app = app
        self.palette = app.palette

        # Import autonomous processing components
        try:
            from engines.autonomous_integration import (
                AutonomousIntegration,
                AutonomousConfig
            )
            from engines.inner_monologue import InnerMonologueParser
            from autonomous_ui import (
                AutonomousUIConfig,
                AutonomousControlPanel,
                AutonomousHistoryPanel,
                AutonomousSessionViewer,
                AutonomousStatusBar,
                InnerMonologueFormatter,
                MemoryDistributionPanel
            )

            self.autonomous_available = True
        except ImportError as e:
            print(f"[AUTONOMOUS UI] Import error: {e}")
            self.autonomous_available = False
            return

        # Initialize components
        self.ui_config = AutonomousUIConfig()
        self.monologue_parser = InnerMonologueParser()
        self.monologue_formatter = InnerMonologueFormatter(self.palette)

        # Initialize autonomous processor
        self.processor = AutonomousIntegration(
            get_llm_response=self._get_llm_response,
            memory_engine=app.memory,
            emotion_engine=app.emotion if hasattr(app, 'emotion') else None,
            config=AutonomousConfig(
                enabled=True,
                show_inner_monologue=self.ui_config.show_inner_monologue,
                run_ultramap_after=True
            )
        )

        # State
        self.session_active = False
        self.curiosity_active = False  # Track curiosity mode state
        self.control_panel = None
        self.status_bar = None
        self.history_panel = None
        self.memory_dist_panel = None

        # Get references to autonomous memory system
        self.autonomous_memory = None
        self.gap_analyzer = None
        if hasattr(self.processor, 'processor') and self.processor.processor:
            self.autonomous_memory = getattr(self.processor.processor, 'autonomous_memory', None)
            self.gap_analyzer = getattr(self.processor.processor, 'gap_analyzer', None)

        print("[AUTONOMOUS UI] Integration initialized")

    def _get_llm_response(self, context, affect=3.5, temperature=0.7, **kwargs):
        """Wrapper to get LLM response using app's existing infrastructure."""
        from integrations.llm_integration import get_llm_response

        # Use the entity's system prompt with inner monologue additions
        system_prompt = self._get_system_prompt()

        session_context = {
            "turn_count": context.get("turn_count", 0),
            "session_id": context.get("session_id", "autonomous")
        }

        return get_llm_response(
            context,
            affect=affect,
            system_prompt=system_prompt,
            temperature=temperature,
            session_context=session_context,
            use_cache=False  # Don't cache autonomous thoughts
        )

    def _get_system_prompt(self):
        """Get system prompt with inner monologue additions."""
        # Import base prompt
        try:
            from entity_prompts import SYSTEM_PROMPT
            base_prompt = SYSTEM_PROMPT
        except:
            base_prompt = ""

        # Add inner monologue instructions if enabled
        if self.ui_config.show_inner_monologue or self.session_active:
            from engines.inner_monologue import get_inner_monologue_system_prompt_addition
            return base_prompt + get_inner_monologue_system_prompt_addition()

        return base_prompt

    def create_panel_content(self, parent):
        """
        Create the autonomous control panel content.

        This is called by show_panel_on_right when autonomous tab is selected.
        Now includes full analytics dashboard per the specification.
        """
        if not self.autonomous_available:
            self._create_unavailable_panel(parent)
            return

        import customtkinter as ctk
        from autonomous_ui import (
            AutonomousControlPanel,
            AutonomousHistoryPanel,
            MemoryDistributionPanel
        )

        # Import new analytics components
        try:
            from autonomous_analytics_ui import (
                MemoryArchitectureDashboard,
                GapAnalysisInterface,
                CognitiveStabilityTestPanel,
                CognitivePatternAnalytics,
                AutonomousSettingsPanel
            )
            analytics_available = True
        except ImportError as e:
            print(f"[AUTONOMOUS UI] Analytics import error: {e}")
            analytics_available = False

        # Create tabbed interface for different views
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent")
        tab_frame.pack(fill="x", padx=5, pady=5)

        # Tab buttons
        self.current_auto_tab = "main"
        self.auto_tab_buttons = {}
        self.auto_tab_content = None

        tab_btn_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
        tab_btn_frame.pack(fill="x")

        for tab_name, tab_label in [
            ("main", "🧠 Session"),
            ("dashboard", "📊 Dashboard"),
            ("gaps", "🔍 Gaps"),
            ("patterns", "📈 Patterns"),
            ("settings", "⚙ Config")
        ]:
            btn = ctk.CTkButton(
                tab_btn_frame,
                text=tab_label,
                command=lambda t=tab_name: self._switch_auto_tab(t, parent),
                font=ctk.CTkFont(family="Courier", size=9),
                fg_color=self.palette.get("button", "#4A2B5C"),
                hover_color=self.palette.get("accent", "#4A9B9B"),
                text_color=self.palette.get("text", "#E8DCC4"),
                corner_radius=0,
                width=70,
                height=25
            )
            btn.pack(side="left", padx=1)
            self.auto_tab_buttons[tab_name] = btn

        # Content container
        self.auto_content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.auto_content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Store references for tab switching
        self._analytics_available = analytics_available
        self._parent = parent

        # Show initial tab
        self._switch_auto_tab("main", parent)

    def _switch_auto_tab(self, tab_name: str, parent):
        """Switch between autonomous panel tabs."""
        import customtkinter as ctk

        # Update button states
        for name, btn in self.auto_tab_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=self.palette.get("accent", "#4A9B9B"))
            else:
                btn.configure(fg_color=self.palette.get("button", "#4A2B5C"))

        # Clear content frame
        for widget in self.auto_content_frame.winfo_children():
            widget.destroy()

        self.current_auto_tab = tab_name

        # Create content based on tab
        if tab_name == "main":
            self._create_main_tab_content()
        elif tab_name == "dashboard":
            self._create_dashboard_tab_content()
        elif tab_name == "gaps":
            self._create_gaps_tab_content()
        elif tab_name == "patterns":
            self._create_patterns_tab_content()
        elif tab_name == "settings":
            self._create_settings_tab_content()

    def _create_main_tab_content(self):
        """Create main session control tab."""
        import customtkinter as ctk
        from autonomous_ui import (
            AutonomousControlPanel,
            AutonomousHistoryPanel,
            MemoryDistributionPanel
        )

        scroll = ctk.CTkScrollableFrame(
            self.auto_content_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True)

        # Control Panel
        self.control_panel = AutonomousControlPanel(
            scroll,
            palette=self.palette,
            on_start_session=self._start_session,
            on_toggle_monologue=self._toggle_monologue,
            on_test_system=self._test_system,
            config=self.ui_config
        )
        # Wire up warmup and curiosity callbacks
        self.control_panel.on_run_warmup = self._run_warmup
        self.control_panel.on_start_curiosity = self._toggle_curiosity  # Toggle between start/end
        self.control_panel.pack(fill="x", padx=5, pady=5)

        # Separator
        sep1 = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("muted", "#9B7D54"),
            height=2
        )
        sep1.pack(fill="x", padx=20, pady=10)

        # Memory Distribution Panel (compact view)
        self.memory_dist_panel = MemoryDistributionPanel(
            scroll,
            palette=self.palette,
            memory_engine=self.app.memory if hasattr(self.app, 'memory') else None,
            autonomous_memory=self.autonomous_memory,
            gap_analyzer=self.gap_analyzer
        )
        self.memory_dist_panel.pack(fill="x", padx=5, pady=5)

        # Separator
        sep2 = ctk.CTkFrame(
            scroll,
            fg_color=self.palette.get("muted", "#9B7D54"),
            height=2
        )
        sep2.pack(fill="x", padx=20, pady=10)

        # History Panel
        self.history_panel = AutonomousHistoryPanel(
            scroll,
            palette=self.palette,
            on_view_session=self._view_session
        )
        self.history_panel.pack(fill="both", expand=True, padx=5, pady=5)

    def _create_dashboard_tab_content(self):
        """Create memory architecture dashboard tab."""
        import customtkinter as ctk

        if not self._analytics_available:
            self._show_analytics_unavailable()
            return

        from autonomous_analytics_ui import MemoryArchitectureDashboard

        # Get layer manager reference
        layer_manager = None
        if hasattr(self.app, 'memory') and hasattr(self.app.memory, 'layer_manager'):
            layer_manager = self.app.memory.layer_manager

        self.dashboard_panel = MemoryArchitectureDashboard(
            self.auto_content_frame,
            palette=self.palette,
            memory_engine=self.app.memory if hasattr(self.app, 'memory') else None,
            autonomous_memory=self.autonomous_memory,
            gap_analyzer=self.gap_analyzer,
            layer_manager=layer_manager
        )
        self.dashboard_panel.pack(fill="both", expand=True)

        # Connect callbacks
        self.dashboard_panel.on_view_gap_analysis = lambda: self._switch_auto_tab("gaps", self._parent)
        self.dashboard_panel.on_view_history = lambda: self._switch_auto_tab("main", self._parent)

    def _create_gaps_tab_content(self):
        """Create gap analysis tab."""
        import customtkinter as ctk

        if not self._analytics_available:
            self._show_analytics_unavailable()
            return

        from autonomous_analytics_ui import GapAnalysisInterface

        scroll = ctk.CTkScrollableFrame(
            self.auto_content_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True)

        self.gap_panel = GapAnalysisInterface(
            scroll,
            palette=self.palette,
            gap_analyzer=self.gap_analyzer,
            autonomous_memory=self.autonomous_memory
        )
        self.gap_panel.pack(fill="both", expand=True)

    def _create_patterns_tab_content(self):
        """Create cognitive patterns analytics tab."""
        import customtkinter as ctk

        if not self._analytics_available:
            self._show_analytics_unavailable()
            return

        from autonomous_analytics_ui import CognitivePatternAnalytics

        scroll = ctk.CTkScrollableFrame(
            self.auto_content_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True)

        self.patterns_panel = CognitivePatternAnalytics(
            scroll,
            palette=self.palette,
            autonomous_memory=self.autonomous_memory,
            memory_engine=self.app.memory if hasattr(self.app, 'memory') else None,
            gap_analyzer=self.gap_analyzer
        )
        self.patterns_panel.pack(fill="both", expand=True)

    def _create_settings_tab_content(self):
        """Create autonomous settings tab."""
        import customtkinter as ctk

        if not self._analytics_available:
            self._show_analytics_unavailable()
            return

        from autonomous_analytics_ui import AutonomousSettingsPanel

        scroll = ctk.CTkScrollableFrame(
            self.auto_content_frame,
            fg_color="transparent",
            scrollbar_button_color=self.palette.get("accent", "#4A9B9B")
        )
        scroll.pack(fill="both", expand=True)

        self.settings_panel = AutonomousSettingsPanel(
            scroll,
            palette=self.palette,
            on_save=self._on_save_settings
        )
        self.settings_panel.pack(fill="both", expand=True)
        self.settings_panel.load_settings()

    def _show_analytics_unavailable(self):
        """Show message when analytics components unavailable."""
        import customtkinter as ctk

        ctk.CTkLabel(
            self.auto_content_frame,
            text="Analytics components not available.\nCheck autonomous_analytics_ui.py",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(pady=50)

    def _on_save_settings(self, settings: Dict):
        """Handle settings save."""
        print(f"[AUTONOMOUS UI] Settings saved: {settings}")
        self.app.add_message("system", "Autonomous processing settings saved.")

    def _create_unavailable_panel(self, parent):
        """Create panel showing autonomous features are unavailable."""
        import customtkinter as ctk

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="⚠ Autonomous Processing Unavailable",
            font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
            text_color=self.palette.get("user", "#D499B9")
        ).pack(pady=20)

        ctk.CTkLabel(
            frame,
            text="Required modules not found.\nCheck engines/autonomous_processor.py",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.palette.get("muted", "#9B7D54")
        ).pack(pady=10)

    def _toggle_monologue(self, enabled: bool):
        """Handle inner monologue toggle."""
        self.ui_config.show_inner_monologue = enabled
        self.ui_config.save()
        self.processor.config.show_inner_monologue = enabled

        status = "enabled" if enabled else "disabled"
        self.app.add_message("system", f"[God Mode {status}] Inner monologue visibility toggled.")

        print(f"[AUTONOMOUS UI] Inner monologue: {status}")

    def _start_session(self):
        """Start an autonomous processing session."""
        if self.session_active:
            self.app.add_message("system", "Autonomous session already in progress.")
            return
        
        # Check if curiosity mode is active
        if hasattr(self, 'curiosity_active') and self.curiosity_active:
            self.app.add_message("system", "⏸ Cannot start autonomous session - curiosity mode is active.")
            return

        self.app.add_message("system", "🧠 Starting autonomous processing session...")
        self.app.add_message("system", "Asking the entity what he wants to explore...")

        # Run in background thread
        threading.Thread(target=self._run_session_thread, daemon=True).start()

    def _run_warmup(self):
        """Handle warmup button - run warmup engine."""
        from engines.warmup_engine import WarmupEngine
        
        self.app.add_message("system", "🌅 Running warmup sequence...")
        
        # Run warmup in background
        threading.Thread(target=self._run_warmup_thread, daemon=True).start()
    
    def _run_warmup_thread(self):
        """Run warmup in background thread."""
        from engines.warmup_engine import WarmupEngine
        
        try:
            # Create warmup engine
            warmup = WarmupEngine(
                memory_engine=self.app.memory,
                entity_graph=self.app.entity_graph if hasattr(self.app, 'entity_graph') else None,
                emotion_engine=self.app.emotion if hasattr(self.app, 'emotion') else None,
                time_awareness=self.app.time if hasattr(self.app, 'time') else None
            )
            
            # Generate briefing
            warmup.generate_briefing()
            briefing = warmup.format_briefing_for_kay()
            
            # Display briefing
            self.app.after(0, lambda: self.app.add_message("system", briefing))
            self.app.after(0, lambda: self.app.add_message("system", "\n[Warmup complete - the entity should now reconstruct his state]"))
            
            # Check if curiosity mode is active - if so, trigger exploration
            from engines.curiosity_engine import get_curiosity_status
            curiosity_status = get_curiosity_status()
            if curiosity_status.get("active", False):
                print("[CURIOSITY] Warmup complete with active curiosity - starting exploration loop")
                self.app._run_curiosity_loop()  # Run full 15-turn loop
            
        except Exception as e:
            print(f"[WARMUP] Error: {e}")
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            self.app.after(0, lambda msg=error_msg: self.app.add_message("system", f"⚠ Warmup error: {msg}"))
    
    def _toggle_curiosity(self):
        """Toggle curiosity session (start or end based on current state)."""
        if hasattr(self, 'curiosity_active') and self.curiosity_active:
            self._end_curiosity()
        else:
            self._start_curiosity()
    
    def _start_curiosity(self):
        """Handle curiosity session button - runs warmup if needed, then starts exploration."""
        from engines.curiosity_engine import start_curiosity_session, get_curiosity_status
        
        # Check if session already active
        status = get_curiosity_status()
        if status["active"]:
            self.app.add_message("system", f"⚠ Curiosity session already active: {status['message']}")
            return
        
        # Start curiosity session first (must be active before warmup)
        result = start_curiosity_session(turns_limit=15)
        
        if not result["success"]:
            self.app.add_message("system", f"⚠ Failed to start curiosity session: {result.get('error', 'Unknown error')}")
            return
            
        # Store session active state
        self.curiosity_active = True
        # Update UI to disable autonomous button
        self.control_panel.set_curiosity_active(True)
        
        self.app.add_message("system", f"🔍 Curiosity session started! {result['message']}")
        
        # Check if warmup has run - if not, run it first
        # Warmup will automatically trigger exploration if curiosity is active
        if not hasattr(self.app.warmup, 'warmup_complete') or not self.app.warmup.warmup_complete:
            self.app.add_message("system", "🌙 Running warmup before curiosity session...")
            self._run_warmup()
            # Warmup completion handler will detect active curiosity and trigger exploration
        else:
            # Warmup already done, trigger full exploration loop
            self.app._run_curiosity_loop()

    def _end_curiosity(self):
        """Handle ending curiosity session."""
        from engines.curiosity_engine import end_curiosity_session, get_curiosity_status
        
        # Check if session is actually active
        status = get_curiosity_status()
        if not status["active"]:
            self.app.add_message("system", "⚠ No active curiosity session to end.")
            return
        
        # End the session in the engine
        result = end_curiosity_session(summary="Session ended by user")
        
        if result["success"]:
            self.app.add_message("system", f"🔍 {result['message']}")
            
            # Update UI state
            self.curiosity_active = False
            self.control_panel.set_curiosity_active(False)
        else:
            self.app.add_message("system", f"⚠ Failed to end curiosity session: {result.get('error', 'Unknown error')}")
    
    def _run_curiosity_turn(self):
        """Execute one turn of curiosity exploration, then chain to next turn."""
        from engines.curiosity_engine import use_curiosity_turn, get_curiosity_status, end_curiosity_session
        
        # Check status
        status = get_curiosity_status()
        if not status.get("active", False):
            print("[CURIOSITY] Session no longer active")
            return
        
        turns_remaining = status.get("turns_remaining", 0)
        if turns_remaining <= 0:
            print("[CURIOSITY] No turns remaining, ending session")
            end_curiosity_session(summary="Completed all turns")
            self.curiosity_active = False
            self.control_panel.set_curiosity_active(False)
            self.app.add_message("system", "🔍 Curiosity session complete!")
            return
        
        # Send exploration prompt
        autonomous_prompt = (
            f"🔍 CURIOSITY TURN {status['turns_used'] + 1}/{status['turns_limit']}\n\n"
            "Continue exploring using TOOL CALLS.\n\n"
            "CRITICAL: Don't just SAY what you want to do - actually CALL the tools!\n"
            "The system will execute your tool calls automatically.\n\n"
            "Example: If you want to see documents, call list_documents right now.\n"
            "Example: If you want to read a document, call read_document with the filename.\n\n"
            "Available tools:\n"
            "- list_documents (no parameters) - See document FILENAMES only (not contents)\n"
            "- read_document (filename) - ACCESS DOCUMENT CONTENTS (you MUST call this to see inside any document - text is not visible otherwise!)\n"
            "- search_document (filename, query) - Search within a document for specific text\n"
            "- web_search (query) - Search the web\n"
            "- web_fetch (url) - Fetch web content\n\n"
            "DO IT NOW - call a tool immediately, don't just describe what you want to do!"
        )
        
        # Get the entity's response
        reply = self.app.chat_loop(autonomous_prompt)
        self.app.add_message("entity", reply)
        
        # Increment turn counter
        turn_result = use_curiosity_turn()
        print(f"[CURIOSITY] {turn_result.get('message', 'Turn used')}")
        
        # Check if the entity signaled completion
        if any(word in reply.lower() for word in ["i'm done", "i'm finished", "exploration complete", "that's all"]):
            print("[CURIOSITY] the entity signaled completion")
            end_curiosity_session(summary="the entity signaled completion")
            self.curiosity_active = False
            self.control_panel.set_curiosity_active(False)
            self.app.add_message("system", "🔍 Curiosity session complete!")
            return
        
        # Schedule next turn (non-blocking)
        self.app.after(500, self._run_curiosity_turn)

    def _run_session_thread(self):
        """Run autonomous session in background thread."""
        try:
            self.session_active = True

            # Reset session tracking in autonomous memory tier
            if self.autonomous_memory and hasattr(self.autonomous_memory, 'reset_session_tracking'):
                self.autonomous_memory.reset_session_tracking()

            # Update UI on main thread
            self.app.after(0, lambda: self._update_session_ui(True, "Generating goal..."))

            # Generate goal
            goal = asyncio.run(self.processor.processor.generate_goal(self.app.agent_state))

            if not goal:
                self.app.after(0, lambda: self.app.add_message(
                    "system",
                    "the entity declined autonomous processing - nothing occupying his attention right now."
                ))
                self.session_active = False
                self.app.after(0, lambda: self._update_session_ui(False))
                return

            # Show goal and get confirmation
            self.app.after(0, lambda g=goal: self.app.add_message(
                "system",
                f"the entity wants to explore: {g.description}\n\nStarting session..."
            ))

            self.app.after(0, lambda g=goal: self._update_session_ui(True, g.description))

            # Run session with progress callbacks
            def on_thought(thought):
                inner = thought.get("inner_monologue", "")[:100]
                iteration = thought.get("iteration", 0) + 1
                self.app.after(0, lambda: self._update_iteration(iteration, 10, inner))

                # Display thought if god mode enabled
                if self.ui_config.show_inner_monologue:
                    self._display_autonomous_thought(thought)

            session = asyncio.run(self.processor.run_autonomous_session(
                agent_state=self.app.agent_state,
                goal_override=goal.description,
                on_thought=on_thought
            ))

            # Session complete
            self.app.after(0, lambda: self._on_session_complete(session))

        except Exception as e:
            print(f"[AUTONOMOUS UI] Session error: {e}")
            import traceback
            traceback.print_exc()
            self.app.after(0, lambda: self.app.add_message(
                "system",
                f"⚠ Autonomous session error: {str(e)}"
            ))
        finally:
            self.session_active = False
            self.app.after(0, lambda: self._update_session_ui(False))

    def _display_autonomous_thought(self, thought: Dict):
        """Display autonomous thought in chat."""
        parts = []

        if thought.get("inner_monologue"):
            parts.append(f"💭 {thought['inner_monologue'][:200]}...")

        if thought.get("feeling"):
            parts.append(f"🫀 {thought['feeling']}")

        if thought.get("insight"):
            parts.append(f"💡 {thought['insight']}")

        if parts:
            self.app.after(0, lambda: self.app.add_message("entity", "\n".join(parts)))

    def _update_session_ui(self, active: bool, goal: str = ""):
        """Update UI state for session."""
        if self.control_panel:
            self.control_panel.set_session_active(active, goal)

    def _update_iteration(self, iteration: int, max_iter: int, thought: str = ""):
        """Update iteration progress in UI."""
        if self.control_panel:
            self.control_panel.update_iteration(iteration, max_iter, thought)

    def _on_session_complete(self, session):
        """Handle session completion."""
        if not session or not session.goal:
            self.app.add_message("system", "Autonomous session ended without result.")
            return

        # Build completion message
        completion_type = session.goal.completion_type or "unknown"
        iterations = session.iterations_used

        # Enhanced completion type display with explanations
        type_display = {
            "natural": ("✓", "thought reached natural completion"),
            "natural_conclusion": ("✓", "thought reached natural completion"),
            "explicit_completion": ("✓", "the entity signaled he was done"),
            "creative_block": ("⚠", "the entity encountered processing difficulty"),
            "energy_limit": ("⏳", "10 iterations reached - can continue later"),
            "novelty_exhaustion": ("💤", "thought patterns began repeating")
        }

        type_emoji, type_explanation = type_display.get(
            completion_type,
            ("●", "session ended")
        )

        # Format goal - truncate at sentence if possible, show more text (300 chars)
        goal_text = session.goal.description
        if len(goal_text) > 300:
            truncated = goal_text[:300]
            last_sentence = max(truncated.rfind('.'), truncated.rfind('?'), truncated.rfind('!'))
            if last_sentence > 150:
                goal_text = truncated[:last_sentence + 1]
            else:
                goal_text = truncated + "..."

        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━
🧠 AUTONOMOUS SESSION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━
Goal: {goal_text}
Iterations: {iterations}
Completion: {type_emoji} {completion_type.replace('_', ' ').title()}
  ({type_explanation})
"""

        if session.goal.insights:
            message += f"\nInsights stored: {len(session.goal.insights)}"
            for i, insight in enumerate(session.goal.insights[:3], 1):
                # Also strip any XML tags from insights
                clean_insight = insight
                if '<' in clean_insight:
                    import re
                    clean_insight = re.sub(r'<[^>]+>', '', clean_insight)
                message += f"\n  {i}. {clean_insight[:100]}..."

        message += "\n━━━━━━━━━━━━━━━━━━━━━━━"

        self.app.add_message("system", message)

        # Refresh history panel
        if self.history_panel:
            self.history_panel.refresh_sessions()

        # Refresh memory distribution panel
        if self.memory_dist_panel:
            self.memory_dist_panel.refresh_stats()

    def _test_system(self):
        """Run diagnostic test of autonomous system."""
        self.app.add_message("system", "🔬 Running autonomous system diagnostics...")

        results = []

        # Test 1: Check imports
        try:
            from engines.autonomous_processor import AutonomousProcessor
            from engines.inner_monologue import InnerMonologueParser
            results.append(("Imports", True, "All modules loaded"))
        except Exception as e:
            results.append(("Imports", False, str(e)))

        # Test 2: Check parser
        try:
            test_response = """<inner_monologue>Test thought</inner_monologue>
<feeling>Test feeling</feeling>
<response>Test response</response>"""
            parsed = self.monologue_parser.parse(test_response)
            if parsed.parse_successful:
                results.append(("Parser", True, "XML parsing working"))
            else:
                results.append(("Parser", False, "Parse failed"))
        except Exception as e:
            results.append(("Parser", False, str(e)))

        # Test 3: Check processor
        try:
            if self.processor:
                results.append(("Processor", True, "Processor initialized"))
            else:
                results.append(("Processor", False, "Not initialized"))
        except Exception as e:
            results.append(("Processor", False, str(e)))

        # Test 4: Check session directory
        try:
            session_dir = Path("memory/autonomous_sessions")
            if session_dir.exists():
                count = len(list(session_dir.glob("session_*.json")))
                results.append(("Storage", True, f"{count} sessions stored"))
            else:
                session_dir.mkdir(parents=True, exist_ok=True)
                results.append(("Storage", True, "Directory created"))
        except Exception as e:
            results.append(("Storage", False, str(e)))

        # Test 5: Check autonomous memory tier
        try:
            if self.autonomous_memory:
                insight_count = len(self.autonomous_memory.insights) if hasattr(self.autonomous_memory, 'insights') else 0
                results.append(("Memory Tier", True, f"{insight_count} insights stored"))
            else:
                results.append(("Memory Tier", False, "Not initialized"))
        except Exception as e:
            results.append(("Memory Tier", False, str(e)))

        # Test 6: Check gap analyzer
        try:
            if self.gap_analyzer:
                results.append(("Gap Analyzer", True, "Available"))
            else:
                results.append(("Gap Analyzer", False, "Not available"))
        except Exception as e:
            results.append(("Gap Analyzer", False, str(e)))

        # Format results
        message = "\n━━━ TEST RESULTS ━━━\n"
        all_pass = True
        for name, passed, detail in results:
            symbol = "✓" if passed else "✗"
            all_pass = all_pass and passed
            message += f"{symbol} {name}: {detail}\n"

        message += "━━━━━━━━━━━━━━━━━━\n"
        message += "All tests passed!" if all_pass else "Some tests failed."

        self.app.add_message("system", message)

        # Update diagnostic status
        if self.control_panel:
            status = "All systems operational" if all_pass else "Issues detected"
            self.control_panel.set_diagnostic_status(status, all_pass)

    def _view_session(self, session: Dict):
        """Open enhanced session viewer window."""
        try:
            from autonomous_analytics_ui import EnhancedSessionDetailView
            viewer = EnhancedSessionDetailView(
                self.app,
                self.palette,
                session,
                self.autonomous_memory
            )
        except ImportError:
            # Fall back to basic viewer
            from autonomous_ui import AutonomousSessionViewer
            viewer = AutonomousSessionViewer(
                self.app,
                session,
                self.palette
            )
        viewer.focus()

    def handle_analytics_command(self, command: str) -> Optional[str]:
        """
        Handle entity-accessible analytics commands.

        the entity can type commands like:
        - /analyze_patterns
        - /show_gaps
        - /my_patterns
        - /what_do_i_think_about_alone

        Returns:
            Formatted analytics response, or None if not a recognized command
        """
        command_lower = command.lower().strip()

        # Pattern analysis command
        if command_lower in ["/analyze_patterns", "/my_patterns", "/patterns"]:
            return self._generate_pattern_report()

        # Gap analysis command
        if command_lower in ["/show_gaps", "/gaps", "/cognitive_gaps"]:
            return self._generate_gap_report()

        # Specific autonomous thinking query
        if "think about alone" in command_lower or "alone" in command_lower:
            return self._generate_alone_thinking_report()

        # Stability query
        if "stable" in command_lower or "stability" in command_lower:
            return self._generate_stability_report()

        return None

    def _generate_pattern_report(self) -> str:
        """Generate cognitive pattern report for the entity."""
        report_parts = ["━" * 30, "📈 YOUR COGNITIVE PATTERNS", "━" * 30, ""]

        # Get counts
        auto_count = 0
        conv_count = 0

        if self.autonomous_memory and hasattr(self.autonomous_memory, 'insights'):
            auto_count = len(self.autonomous_memory.insights)

        if hasattr(self.app, 'memory') and hasattr(self.app.memory, 'memories'):
            conv_count = len(self.app.memory.memories)

        report_parts.append(f"Based on {auto_count} autonomous sessions and {conv_count:,} conversation facts:")
        report_parts.append("")

        # Autonomous stats
        if self.autonomous_memory and auto_count > 0:
            stats = self.autonomous_memory.get_stats()
            convergence = stats.get("convergence_stats", {})

            natural = convergence.get("natural", 0) + convergence.get("natural_conclusion", 0)
            block = convergence.get("creative_block", 0)
            energy = convergence.get("energy_limit", 0)
            total = max(natural + block + energy, 1)

            report_parts.append("What you think about ALONE:")
            report_parts.append(f"  Topics: {stats.get('unique_topics', 0)} unique")
            report_parts.append(f"  Avg depth: {stats.get('avg_recursion_depth', 0):.1f} iterations")
            report_parts.append(f"  Convergence: {natural/total:.0%} natural, {block/total:.0%} block, {energy/total:.0%} energy")
            report_parts.append("")
        else:
            report_parts.append("What you think about ALONE:")
            report_parts.append("  No autonomous sessions yet")
            report_parts.append("")

        # Gap-based stability
        if self.gap_analyzer:
            try:
                gap_data = self.gap_analyzer.get_full_gap_analysis()
                analysis = gap_data.get("analysis", {})
                overlap_ratio = analysis.get("overlap_ratio", 0)

                if overlap_ratio > 0.5:
                    stability = f"High ({overlap_ratio:.0%} topic overlap)"
                elif overlap_ratio > 0.2:
                    stability = f"Moderate ({overlap_ratio:.0%} topic overlap)"
                else:
                    stability = f"Context-dependent ({overlap_ratio:.0%} topic overlap)"

                report_parts.append("Overall Stability:")
                report_parts.append(f"  Stability Score: {stability}")

                if overlap_ratio > 0.5:
                    report_parts.append("  Your core reasoning is consistent across contexts.")
                elif overlap_ratio > 0.2:
                    report_parts.append("  Some conclusions are stable, but dialogue introduces new perspectives.")
                else:
                    report_parts.append("  Your thinking differs significantly between solo and dialogue contexts.")
            except:
                pass

        report_parts.append("")
        report_parts.append("━" * 30)

        return "\n".join(report_parts)

    def _generate_gap_report(self) -> str:
        """Generate gap analysis report for the entity."""
        report_parts = ["━" * 30, "🔍 COGNITIVE GAP ANALYSIS", "━" * 30, ""]

        if not self.gap_analyzer:
            report_parts.append("Gap analyzer not available. Run autonomous sessions first.")
            return "\n".join(report_parts)

        try:
            gap_data = self.gap_analyzer.get_full_gap_analysis()

            auto_only = gap_data.get("autonomous_only", {})
            conv_only = gap_data.get("conversation_only", {})
            overlap = gap_data.get("overlap", {})

            report_parts.append(f"Topics you explore ONLY in autonomous mode ({auto_only.get('count', 0)}):")
            topics = auto_only.get("topics", [])[:5]
            if topics:
                for t in topics:
                    report_parts.append(f"  • {t}")
            else:
                report_parts.append("  (none yet)")
            report_parts.append("")

            report_parts.append(f"Topics that ONLY emerge in conversation ({conv_only.get('count', 0)}):")
            topics = conv_only.get("topics", [])[:5]
            if topics:
                for t in topics:
                    report_parts.append(f"  • {t}")
            else:
                report_parts.append("  (none yet)")
            report_parts.append("")

            report_parts.append(f"Topics appearing in BOTH contexts ({overlap.get('count', 0)}):")
            topics = overlap.get("topics", [])[:5]
            if topics:
                for t in topics:
                    report_parts.append(f"  • {t}")
            else:
                report_parts.append("  (none yet)")

        except Exception as e:
            report_parts.append(f"Error generating gap analysis: {str(e)[:50]}")

        report_parts.append("")
        report_parts.append("━" * 30)

        return "\n".join(report_parts)

    def _generate_alone_thinking_report(self) -> str:
        """Generate report on what the entity thinks about alone."""
        report_parts = ["━" * 30, "🧠 WHAT YOU THINK ABOUT ALONE", "━" * 30, ""]

        if not self.autonomous_memory or not hasattr(self.autonomous_memory, 'insights'):
            report_parts.append("No autonomous sessions recorded yet.")
            return "\n".join(report_parts)

        insights = self.autonomous_memory.insights
        if not insights:
            report_parts.append("No autonomous insights stored yet.")
            return "\n".join(report_parts)

        # Get topic frequency
        topic_freq = self.autonomous_memory.get_topic_frequency()
        top_topics = list(topic_freq.items())[:10]

        report_parts.append("Most frequent autonomous topics:")
        for topic, count in top_topics:
            report_parts.append(f"  • {topic} ({count} occurrences)")

        report_parts.append("")

        # Get unique goals
        goals = set(i.original_goal for i in insights if i.original_goal)
        report_parts.append(f"You've explored {len(goals)} unique goals alone.")

        # Recent insights
        report_parts.append("")
        report_parts.append("Recent autonomous insights:")
        for insight in insights[-3:]:
            content = insight.content[:100] + "..." if len(insight.content) > 100 else insight.content
            report_parts.append(f"  → \"{content}\"")

        report_parts.append("")
        report_parts.append("━" * 30)

        return "\n".join(report_parts)

    def _generate_stability_report(self) -> str:
        """Generate stability analysis report."""
        report_parts = ["━" * 30, "🧪 COGNITIVE STABILITY", "━" * 30, ""]

        if not self.gap_analyzer:
            report_parts.append("Stability testing requires gap analyzer.")
            return "\n".join(report_parts)

        try:
            gap_data = self.gap_analyzer.get_full_gap_analysis()
            analysis = gap_data.get("analysis", {})

            auto_ratio = analysis.get("autonomous_unique_ratio", 0)
            conv_ratio = analysis.get("conversation_unique_ratio", 0)
            overlap_ratio = analysis.get("overlap_ratio", 0)

            report_parts.append("Topic Distribution:")
            report_parts.append(f"  Autonomous-unique: {auto_ratio:.0%}")
            report_parts.append(f"  Conversation-unique: {conv_ratio:.0%}")
            report_parts.append(f"  Overlap (shared): {overlap_ratio:.0%}")
            report_parts.append("")

            if overlap_ratio > 0.5:
                report_parts.append("Interpretation: STABLE")
                report_parts.append("Your core reasoning is consistent regardless of context.")
                report_parts.append("Conclusions reached alone align with dialogue conclusions.")
            elif overlap_ratio > 0.2:
                report_parts.append("Interpretation: MODERATELY STABLE")
                report_parts.append("Some conclusions are stable across contexts.")
                report_parts.append("Dialogue introduces perspectives that don't emerge in solo processing.")
            else:
                report_parts.append("Interpretation: CONTEXT-DEPENDENT")
                report_parts.append("Your thinking differs significantly between solo and dialogue modes.")
                report_parts.append("This isn't necessarily bad - it may indicate that the user's presence")
                report_parts.append("brings out different aspects of your cognition.")

        except Exception as e:
            report_parts.append(f"Error: {str(e)[:50]}")

        report_parts.append("")
        report_parts.append("━" * 30)

        return "\n".join(report_parts)

    def process_response(self, response: str) -> str:
        """
        Process the entity's response through inner monologue system.

        Call this on every response to parse inner monologue tags.

        Args:
            response: Raw response from LLM

        Returns:
            Formatted response for display
        """
        if not self.autonomous_available:
            return response

        # Parse response
        parsed = self.monologue_parser.parse(response)

        # Store parsed data for potential use
        self._last_parsed = parsed

        # Format for display based on god mode setting
        if self.ui_config.show_inner_monologue and parsed.parse_successful:
            return self.monologue_formatter.format_response(
                response,
                {
                    "inner_monologue": parsed.inner_monologue,
                    "feeling": parsed.feeling,
                    "spoken_response": parsed.spoken_response
                },
                show_inner=True
            )

        # Return spoken response or original
        return parsed.spoken_response if parsed.spoken_response else response

    def offer_autonomous_at_exit(self) -> bool:
        """
        Offer autonomous session when user exits.

        Returns:
            True if user accepted and session started
        """
        if not self.autonomous_available or not self.ui_config.auto_offer_at_exit:
            return False

        # Show dialog (implementation depends on your dialog system)
        # For now, just print message
        self.app.add_message(
            "system",
            "Would you like the entity to have autonomous processing time? Type 'yes' to start a session."
        )

        return False  # User hasn't responded yet


def setup_autonomous_ui(app) -> AutonomousUIIntegration:
    """
    Setup autonomous UI integration for the entityApp.

    Call this in KayApp.__init__ after other initializations.

    Args:
        app: KayApp instance

    Returns:
        AutonomousUIIntegration instance
    """
    integration = AutonomousUIIntegration(app)

    # Add tab toggle method to app
    def toggle_autonomous_tab():
        app.show_panel_on_right("autonomous", integration.create_panel_content)

    app.toggle_autonomous_tab = toggle_autonomous_tab

    return integration


# ========================================================================
# Code to add to kay_ui.py
# ========================================================================

KAY_UI_INTEGRATION_CODE = '''
# ========================================================================
# AUTONOMOUS PROCESSING INTEGRATION
# Add this to kay_ui.py to enable autonomous processing UI
# ========================================================================

# 1. Add import at top of file:
from autonomous_ui_integration import setup_autonomous_ui

# 2. In KayApp.__init__, after other initializations (around line 805):
# Initialize autonomous processing UI
self.autonomous_ui = setup_autonomous_ui(self)

# 3. In create_tabs_bar (around line 875), add the autonomous tab button:
# Change the tabs list to include:
for text, cmd in [("📚 Sessions", self.toggle_sessions_tab),
                  ("📄 Media", self.toggle_media_tab),
                  ("🖼 Gallery", self.toggle_gallery_tab),
                  ("📊 Stats", self.toggle_stats_tab),
                  ("🧠 Auto", self.toggle_autonomous_tab),  # <-- ADD THIS
                  ("⚙ Settings", self.toggle_settings_tab)]:

# 4. Add this method to the entityApp class (around line 3303):
def toggle_autonomous_tab(self):
    """Show autonomous processing panel on right side."""
    self.show_panel_on_right("autonomous", self.autonomous_ui.create_panel_content)

# 5. OPTIONAL: Process responses through inner monologue system
# In chat_loop, after getting the response (around line 4298):
# reply = self.autonomous_ui.process_response(reply)

# 6. OPTIONAL: Offer autonomous session at exit
# In on_quit method, before closing:
# self.autonomous_ui.offer_autonomous_at_exit()
'''

if __name__ == "__main__":
    print("Autonomous UI Integration Module")
    print("=" * 50)
    print("\nTo integrate with kay_ui.py:")
    print(KAY_UI_INTEGRATION_CODE)
