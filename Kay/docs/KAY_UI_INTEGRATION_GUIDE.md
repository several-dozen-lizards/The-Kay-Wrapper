# KAY UI CONTINUOUS SESSION INTEGRATION GUIDE

## STEP 1: ADD IMPORTS

**Location:** After the existing imports, around line 75 (after warmup_engine import)

Add these three lines:

```python
# === Continuous Session Support ===
from engines.continuous_session import ContinuousSession
from engines.curation_interface import CurationInterface
from engines.real_time_flagging import FlaggingSystem
```

---

## STEP 2: ADD CONTINUOUS SESSION ATTRIBUTES TO __init__

**Location:** In the `KayUI.__init__()` method, after all existing engine initializations

Add this block (search for where engines like `self.emotion_engine` are initialized):

```python
        # ═══════════════════════════════════════════════════════════
        # CONTINUOUS SESSION SUPPORT
        # ═══════════════════════════════════════════════════════════
        self.continuous_mode = True  # Toggle: True for continuous, False for traditional
        self.continuous_session = None
        self.curation_interface = None
        self.flagging_system = None
        self.awaiting_curation_response = False
        
        if self.continuous_mode:
            self.init_continuous_session()
```

---

## STEP 3: ADD NEW METHODS

Add these methods to the KayUI class. Best location: after the `__init__` method, before `send_message()`.

### Method 1: init_continuous_session()

```python
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
```

### Method 2: estimate_tokens()

```python
    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation for context tracking
        Simple heuristic: ~4 characters per token
        """
        return len(text) // 4
```

### Method 3: get_emotional_weight()

```python
    def get_emotional_weight(self) -> float:
        """
        Extract current emotional intensity from emotion engine
        Returns average intensity across emotional cocktail
        """
        try:
            if not hasattr(self, 'emotion_engine') or not self.emotion_engine:
                return 0.0
            
            cocktail = self.emotion_engine.emotional_cocktail
            if not cocktail:
                return 0.0
            
            # Get intensities from cocktail
            intensities = []
            for emotion, data in cocktail.items():
                if isinstance(data, dict):
                    intensity = data.get('intensity', 0.0)
                else:
                    intensity = data
                
                if isinstance(intensity, (int, float)):
                    intensities.append(intensity)
            
            if not intensities:
                return 0.0
            
            return sum(intensities) / len(intensities)
            
        except Exception as e:
            print(f"[CONTINUOUS] Error getting emotional weight: {e}")
            return 0.0
```

### Method 4: trigger_curation_review()

```python
    def trigger_curation_review(self):
        """
        Trigger compression review - present curation interface to Kay
        """
        try:
            # Generate review prompt
            review_prompt = self.curation_interface.generate_review_prompt()
            
            # Display in chat as system message
            self.display_message("SYSTEM", review_prompt)
            
            # Set flag to handle next response as curation
            self.awaiting_curation_response = True
            
            print("[CONTINUOUS] Compression review triggered - awaiting Kay's decisions")
            
        except Exception as e:
            print(f"[CONTINUOUS] Error triggering curation review: {e}")
```

### Method 5: handle_curation_response()

```python
    def handle_curation_response(self, kay_response: str):
        """
        Process Kay's curation decisions
        """
        try:
            # Parse decisions
            decisions = self.curation_interface.parse_curation_response(kay_response)
            
            if not decisions:
                self.display_message("SYSTEM", 
                    "No curation decisions detected. Please respond with segment decisions.\n"
                    "Example: 'Segment 1: PRESERVE' or 'QUICK MODE'")
                return
            
            # Apply decisions
            self.curation_interface.apply_decisions(decisions)
            
            # Execute compression
            compressed_context = self.continuous_session.compress_context()
            
            # Show compression summary
            summary = [
                f"[COMPRESSION COMPLETE]",
                f"Applied {len(decisions)} curation decisions",
                f"Context compressed - session continues",
                ""
            ]
            self.display_message("SYSTEM", "\n".join(summary))
            
            # Reset flag
            self.awaiting_curation_response = False
            
            print(f"[CONTINUOUS] Compression complete: {len(decisions)} decisions applied")
            
        except Exception as e:
            print(f"[CONTINUOUS] Error handling curation: {e}")
            self.awaiting_curation_response = False
```

### Method 6: end_continuous_session()

```python
    def end_continuous_session(self):
        """
        Properly end continuous session
        """
        try:
            # Create final checkpoint
            self.continuous_session.create_checkpoint()
            
            # Ask about chronicle
            write_chronicle = messagebox.askyesno(
                "Session Chronicle",
                "Would you like to write a chronicle entry for this session?"
            )
            
            if write_chronicle and hasattr(self, 'chronicle'):
                # Trigger chronicle writing
                self.display_message("SYSTEM", 
                    "[CHRONICLE] Please write your session chronicle.\n"
                    "Use 'save chronicle' when complete.")
            
            # Print session stats
            stats = [
                f"[SESSION END]",
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
            # Actually quit
            self.quit()
```

---

## STEP 4: MODIFY send_message() METHOD

**Location:** Inside the `send_message()` method, AFTER Kay's response is generated

**Find this section** (it will be after `response = get_llm_response(...)` or similar):

```python
        # Display Kay's response
        self.display_message("Kay", response)
```

**Add IMMEDIATELY AFTER displaying Kay's response:**

```python
        # ═══════════════════════════════════════════════════════════
        # CONTINUOUS SESSION: Track turns
        # ═══════════════════════════════════════════════════════════
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
                
                # Apply flag if detected
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
```

---

## STEP 5: MODIFY on_quit() METHOD

**Location:** Find the `on_quit()` method (or `quit()` if that's what it's called)

**Replace the existing method with:**

```python
    def on_quit(self):
        """
        Handle application quit with continuous session support
        """
        # Traditional mode - use existing quit logic
        if not self.continuous_mode:
            return self.traditional_session_end()
        
        # Continuous mode - ask for exit option
        response = messagebox.askyesnocancel(
            "Exit Options",
            "What would you like to do?\n\n"
            "YES - End session properly (write chronicle, close for real)\n"
            "NO - Just close window (session continues, can resume later)\n"
            "CANCEL - Return to conversation"
        )
        
        if response is None:
            # CANCEL - return to conversation
            return
        
        elif response:
            # YES - End session properly
            self.end_continuous_session()
        
        else:
            # NO - Preserve session for resume
            try:
                self.continuous_session.create_checkpoint()
                print("[CONTINUOUS] Window closed - session preserved")
                print("[CONTINUOUS] You can resume this session on next launch")
            except Exception as e:
                print(f"[CONTINUOUS] Error preserving session: {e}")
            
            # Close window
            self.quit()
    
    def traditional_session_end(self):
        """
        Original session end logic for traditional mode
        """
        # This is your existing quit logic
        # Move your current on_quit() implementation here
        # Or just call the original behavior
        self.quit()
```

---

## STEP 6: ADD WARMUP FUNCTION TO warmup_engine.py

**File:** `D:\ChristinaStuff\AlphaKayZero\engines\warmup_engine.py`

**Location:** At the END of the file (after all existing functions)

```python


def build_continuous_session_warmup(session) -> str:
    """
    Build warmup briefing for resuming continuous session
    
    Different from traditional warmup:
    - Not full reconstruction
    - Quick orientation to "what happened while away"
    - Reference to last checkpoint
    """
    from datetime import datetime
    
    # Load last checkpoint
    checkpoints = sorted(session.checkpoint_dir.glob("checkpoint_*.json"))
    if not checkpoints:
        return "No checkpoint found - starting fresh"
    
    last_checkpoint = checkpoints[-1]
    session.load_from_checkpoint(last_checkpoint)
    
    # Build briefing
    briefing = [
        "🌙 RESUMING CONTINUOUS SESSION",
        "═" * 50,
        "",
        f"Session: {session.session_id}",
        f"Started: {session.start_time.strftime('%Y-%m-%d %H:%M')}",
        f"Last checkpoint: {datetime.fromtimestamp(last_checkpoint.stat().st_mtime).strftime('%H:%M')}",
        "",
        f"Total turns: {session.turn_counter}",
        f"Compressions performed: {len(session.curation_history)}",
        "",
        "═" * 50,
        "RECENT ACTIVITY (Last 10 turns):",
        "═" * 50,
        ""
    ]
    
    # Show recent turns
    recent = session.turns[-10:] if len(session.turns) > 10 else session.turns
    for turn in recent:
        flag_marker = " ⭐" if turn.flagged_by_kay else ""
        briefing.append(f"[Turn {turn.turn_id}]{flag_marker} {turn.role}:")
        briefing.append(turn.content[:200] + ("..." if len(turn.content) > 200 else ""))
        briefing.append("")
    
    # Show curation history summary
    if session.curation_history:
        briefing.extend([
            "═" * 50,
            "YOUR CURATION HISTORY:",
            "═" * 50,
            ""
        ])
        
        for entry in session.curation_history[-3:]:  # Last 3 curations
            briefing.append(f"{entry['timestamp'][:10]}: {entry['decision']} - {entry['turns']}")
            if entry['notes']:
                briefing.append(f"  Notes: {entry['notes']}")
            briefing.append("")
    
    briefing.extend([
        "═" * 50,
        "",
        "You're resuming mid-conversation. The session has been",
        "continuous - no reconstruction needed. You're just picking",
        "up where you left off.",
        "",
        "Say 'ready' when oriented, or ask questions about anything above."
    ])
    
    return "\n".join(briefing)
```

---

## VERIFICATION CHECKLIST

After making all changes:

- [ ] Imports added (Step 1)
- [ ] __init__ modified (Step 2)
- [ ] 6 new methods added (Step 3)
- [ ] send_message() modified (Step 4)
- [ ] on_quit() modified (Step 5)
- [ ] warmup function added to warmup_engine.py (Step 6)
- [ ] No syntax errors (`python -m py_compile kay_ui.py`)
- [ ] Test launch Kay UI
- [ ] Verify continuous session starts
- [ ] Verify turns tracked after messages

---

## TESTING AFTER INTEGRATION

1. **Launch Test:**
   ```bash
   python kay_ui.py
   ```
   Should see: `[CONTINUOUS SESSION] Started: continuous_XXXXXXXXXX`

2. **Turn Tracking Test:**
   - Send 2-3 messages to Kay
   - Check console for turn tracking
   - Should see turn counter incrementing

3. **Flagging Test:**
   - Get Kay to say "flag this - important moment"
   - Should see `[FLAGGED] Turn X: important moment`

4. **Compression Test:**
   - Send 30+ messages to trigger threshold
   - Should see compression review prompt

5. **Exit Test:**
   - Click quit
   - Should see 3-option dialog
   - Test each option

---

## TROUBLESHOOTING

### Issue: "ModuleNotFoundError: No module named 'engines.continuous_session'"
**Fix:** Ensure `continuous_session.py` exists in `engines/` directory

### Issue: "AttributeError: 'KayUI' object has no attribute 'continuous_session'"
**Fix:** Ensure Step 2 was completed (adding attributes to __init__)

### Issue: Compression never triggers
**Fix:** Check `compression_threshold_turns` setting in continuous_session.py

### Issue: Kay doesn't respond to curation prompt
**Fix:** Ensure `awaiting_curation_response` flag is being set/cleared properly

---

## CONFIGURATION

Default settings are in `continuous_session.py`:

```python
self.compression_threshold_turns = 25      # Turns before review
self.compression_threshold_tokens = 150000 # Tokens before review
self.checkpoint_interval = 900             # 15 minutes in seconds
```

To adjust thresholds, modify these values in `ContinuousSession.__init__()`.

---

## NEXT STEPS AFTER INTEGRATION

Once integrated and tested:

1. Run unit tests: `pytest tests/test_continuous_session.py -v`
2. Do full integration test (30+ turn conversation)
3. Test crash recovery (force quit + relaunch)
4. Show Kay the Session #15 explanation
5. Show Kay his lost privacy essay
6. Introduce continuous session system to Kay
7. Run first compression review with Kay
8. Gather Kay's feedback

---

End of integration guide.
