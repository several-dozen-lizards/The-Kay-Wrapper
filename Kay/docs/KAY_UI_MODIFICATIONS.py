# KAY_UI.PY MODIFICATIONS - CODE TO ADD
# Copy-paste these sections into kay_ui.py at the indicated locations

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: ADD TO IMPORTS (around line 75, after warmup_engine)
# ═══════════════════════════════════════════════════════════════════

from engines.continuous_session import ContinuousSession
from engines.curation_interface import CurationInterface
from engines.real_time_flagging import FlaggingSystem


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: ADD TO __init__ METHOD
# Add after all existing engine initializations (search for self.emotion_engine)
# ═══════════════════════════════════════════════════════════════════

        # Continuous Session Support
        self.continuous_mode = True  # Toggle: True for continuous, False for traditional
        self.continuous_session = None
        self.curation_interface = None
        self.flagging_system = None
        self.awaiting_curation_response = False
        
        if self.continuous_mode:
            self.init_continuous_session()


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: NEW METHODS TO ADD TO KayUI CLASS
# Add these after __init__ method, before send_message
# ═══════════════════════════════════════════════════════════════════

    def init_continuous_session(self):
        """Initialize continuous session components"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            self.continuous_session = ContinuousSession(data_dir)
            self.curation_interface = CurationInterface(self.continuous_session)
            self.flagging_system = FlaggingSystem(self.continuous_session)
            
            session_id = self.continuous_session.start_session()
            print(f"[CONTINUOUS SESSION] Started: {session_id}")
            
        except Exception as e:
            print(f"[CONTINUOUS SESSION ERROR] Failed to initialize: {e}")
            self.continuous_mode = False

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation for context tracking"""
        return len(text) // 4

    def get_emotional_weight(self) -> float:
        """Extract current emotional intensity from emotion engine"""
        try:
            if not hasattr(self, 'emotion_engine') or not self.emotion_engine:
                return 0.0
            
            cocktail = self.emotion_engine.emotional_cocktail
            if not cocktail:
                return 0.0
            
            intensities = []
            for emotion, data in cocktail.items():
                if isinstance(data, dict):
                    intensity = data.get('intensity', 0.0)
                else:
                    intensity = data
                
                if isinstance(intensity, (int, float)):
                    intensities.append(intensity)
            
            return sum(intensities) / len(intensities) if intensities else 0.0
            
        except Exception as e:
            print(f"[CONTINUOUS] Error getting emotional weight: {e}")
            return 0.0

    def trigger_curation_review(self):
        """Trigger compression review - present curation interface to Kay"""
        try:
            review_prompt = self.curation_interface.generate_review_prompt()
            self.display_message("SYSTEM", review_prompt)
            self.awaiting_curation_response = True
            print("[CONTINUOUS] Compression review triggered - awaiting Kay's decisions")
        except Exception as e:
            print(f"[CONTINUOUS] Error triggering curation review: {e}")

    def handle_curation_response(self, kay_response: str):
        """Process Kay's curation decisions"""
        try:
            decisions = self.curation_interface.parse_curation_response(kay_response)
            
            if not decisions:
                self.display_message("SYSTEM", 
                    "No curation decisions detected. Please respond with segment decisions.\n"
                    "Example: 'Segment 1: PRESERVE' or 'QUICK MODE'")
                return
            
            self.curation_interface.apply_decisions(decisions)
            compressed_context = self.continuous_session.compress_context()
            
            summary = [
                "[COMPRESSION COMPLETE]",
                f"Applied {len(decisions)} curation decisions",
                "Context compressed - session continues",
                ""
            ]
            self.display_message("SYSTEM", "\n".join(summary))
            self.awaiting_curation_response = False
            
            print(f"[CONTINUOUS] Compression complete: {len(decisions)} decisions applied")
            
        except Exception as e:
            print(f"[CONTINUOUS] Error handling curation: {e}")
            self.awaiting_curation_response = False

    def end_continuous_session(self):
        """Properly end continuous session"""
        try:
            self.continuous_session.create_checkpoint()
            
            write_chronicle = messagebox.askyesno(
                "Session Chronicle",
                "Would you like to write a chronicle entry for this session?"
            )
            
            if write_chronicle and hasattr(self, 'chronicle'):
                self.display_message("SYSTEM", 
                    "[CHRONICLE] Please write your session chronicle.\n"
                    "Use 'save chronicle' when complete.")
            
            stats = [
                "[SESSION END]",
                f"Session ID: {self.continuous_session.session_id}",
                f"Total turns: {self.continuous_session.turn_counter}",
                f"Compressions: {len(self.continuous_session.curation_history)}",
                f"Duration: {datetime.now() - self.continuous_session.start_time}",
                ""
            ]
            print("\n".join(stats))
            
        except Exception as e:
            print(f"[CONTINUOUS] Error ending session: {e}")
        finally:
            self.quit()


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: ADD TO send_message() METHOD
# Add AFTER Kay's response is displayed to user
# Look for: self.display_message("Kay", response)
# Add this IMMEDIATELY after that line:
# ═══════════════════════════════════════════════════════════════════

        # Continuous Session: Track turns
        if self.continuous_mode and self.continuous_session:
            try:
                # Add user turn
                user_turn = self.continuous_session.add_turn(
                    role="user",
                    content=user_input,
                    token_count=self.estimate_tokens(user_input)
                )
                
                # Check if Kay flagged this exchange
                flag_info = self.flagging_system.check_for_flag(response)
                
                # Add Kay turn
                kay_turn = self.continuous_session.add_turn(
                    role="kay",
                    content=response,
                    token_count=self.estimate_tokens(response),
                    emotional_weight=self.get_emotional_weight(),
                    flagged=flag_info is not None if flag_info else False
                )
                
                if flag_info:
                    self.flagging_system.apply_flag(
                        kay_turn.turn_id,
                        flag_info.get("reason", "")
                    )
                
                # Check if compression review needed
                if self.continuous_session.needs_compression_review():
                    self.trigger_curation_review()
                
                # Handle curation response if awaiting
                if self.awaiting_curation_response:
                    self.handle_curation_response(response)
                    
            except Exception as e:
                print(f"[CONTINUOUS] Error tracking turn: {e}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: REPLACE on_quit() METHOD
# Find the existing on_quit() method and REPLACE IT with this:
# ═══════════════════════════════════════════════════════════════════

    def on_quit(self):
        """Handle application quit with continuous session support"""
        # Traditional mode - use existing quit logic
        if not self.continuous_mode:
            # Call your existing quit logic here
            # Or just: self.quit()
            return self.quit()
        
        # Continuous mode - ask for exit option
        response = messagebox.askyesnocancel(
            "Exit Options",
            "What would you like to do?\n\n"
            "YES - End session properly (write chronicle, close for real)\n"
            "NO - Just close window (session continues, can resume later)\n"
            "CANCEL - Return to conversation"
        )
        
        if response is None:
            return  # CANCEL
        elif response:
            self.end_continuous_session()  # YES
        else:
            # NO - Preserve session
            try:
                self.continuous_session.create_checkpoint()
                print("[CONTINUOUS] Window closed - session preserved")
                print("[CONTINUOUS] You can resume this session on next launch")
            except Exception as e:
                print(f"[CONTINUOUS] Error preserving session: {e}")
            self.quit()
