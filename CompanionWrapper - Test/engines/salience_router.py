# engines/salience_router.py
"""
Salience Router: Cognitive State Orchestration
==============================================

Routes the entity between cognitive modes based on context and activity.
Does NOT prescribe behavior - just detects state and manages transitions.

Cognitive States:
- AWAKE: User present, TPN dominant, frequent API calls
- PROCESSING: Post-conversation DMN consolidation (5-15 turns)
- DREAMING: Deep DMN synthesis (3-10 cycles, spaced)
- SLEEPING: Dormant, no processing, waiting for wake

Philosophy: Support natural LLM cognition, don't program it.
"""

import os
import time
from enum import Enum
from typing import Dict, Optional, Tuple
import json
from datetime import datetime


class CognitiveMode(Enum):
    """the entity's cognitive states"""
    AWAKE = "AWAKE"              # TPN dominant - conversation active
    PROCESSING = "PROCESSING"    # DMN active - consolidating conversation
    DREAMING = "DREAMING"        # DMN deep - pattern synthesis
    SLEEPING = "SLEEPING"        # Dormant - no processing


class TaskType(Enum):
    """Types of tasks (for interruption handling)"""
    CONVERSATION = "conversation"
    KAY_REFLECTION = "kay_reflection"  # Claude-based, the entity's thoughts
    DATA_PROCESSING = "data_processing"  # Ollama-based, organizational
    CLAUDE_SYNTHESIS = "claude_synthesis"  # Claude-based, deep insights
    DATA_VALIDATION = "data_validation"  # Ollama-based, grounding checks


class SalienceRouter:
    """Orchestrates cognitive state transitions"""

    def __init__(self, config_path: str = "config.json"):
        self.current_mode = CognitiveMode.SLEEPING
        self.current_task: Optional[TaskType] = None
        self.current_task_pid: Optional[int] = None

        # Timing
        self.last_message_time = None
        self.mode_entry_time = None
        self.conversation_start_time = None

        # Configuration
        self.config = self._load_config(config_path)

        # Transition history (for debugging)
        self.transition_log = []

        print(f"[SALIENCE] Router initialized in {self.current_mode.value} mode")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration with defaults"""
        defaults = {
            "idle_threshold_seconds": 300,  # 5 minutes
            "processing_max_turns": 15,
            "dreaming_max_cycles": 10,
            "goodbye_phrases": ["goodnight", "see you", "bye", "gotta go", "talk later"],
            "wake_phrases": ["hey kay", "entity", "hello", "good morning"]
        }

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in defaults.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            print(f"[SALIENCE] Config not found, using defaults")
            return defaults
        except Exception as e:
            print(f"[SALIENCE] Error loading config: {e}, using defaults")
            return defaults

    def determine_mode(self,
                      user_input: Optional[str] = None,
                      time_since_last_message: Optional[float] = None) -> CognitiveMode:
        """
        Detect current cognitive mode based on context.
        Does NOT change state - just detects what state we should be in.
        """
        current_time = time.time()

        # If user just sent input, definitely AWAKE
        if user_input is not None:
            return CognitiveMode.AWAKE

        # If we're already processing/dreaming, stay there
        if self.current_mode in [CognitiveMode.PROCESSING, CognitiveMode.DREAMING]:
            return self.current_mode

        # Check for idle timeout
        if time_since_last_message is not None:
            if time_since_last_message > self.config["idle_threshold_seconds"]:
                # Been idle long enough to start processing
                if self.current_mode == CognitiveMode.AWAKE:
                    return CognitiveMode.PROCESSING

        # Default: maintain current mode
        return self.current_mode

    def should_transition(self,
                         current_mode: CognitiveMode,
                         target_mode: CognitiveMode,
                         context: Dict) -> Tuple[bool, str]:
        """
        Determine if a mode transition should occur.

        Args:
            current_mode: Current cognitive mode
            target_mode: Proposed next mode
            context: Additional context (convergence, user_input, etc.)

        Returns:
            (should_transition, reason)
        """

        # AWAKE → PROCESSING
        if current_mode == CognitiveMode.AWAKE and target_mode == CognitiveMode.PROCESSING:
            # User said goodbye
            if context.get("explicit_goodbye"):
                return True, "explicit_goodbye"
            # Idle timeout
            if context.get("idle_timeout"):
                return True, "idle_timeout"
            return False, "still_conversing"

        # PROCESSING → DREAMING
        if current_mode == CognitiveMode.PROCESSING and target_mode == CognitiveMode.DREAMING:
            if context.get("convergence_detected"):
                return True, "processing_converged"
            if context.get("turn_count", 0) >= self.config["processing_max_turns"]:
                return True, "max_turns_reached"
            return False, "still_processing"

        # DREAMING → SLEEPING
        if current_mode == CognitiveMode.DREAMING and target_mode == CognitiveMode.SLEEPING:
            if context.get("diminishing_returns"):
                return True, "no_new_insights"
            if context.get("cycle_count", 0) >= self.config["dreaming_max_cycles"]:
                return True, "max_cycles_reached"
            if context.get("cost_limit_reached"):
                return True, "budget_exceeded"
            return False, "still_dreaming"

        # SLEEPING → AWAKE
        if current_mode == CognitiveMode.SLEEPING and target_mode == CognitiveMode.AWAKE:
            if context.get("user_input"):
                return True, "user_returned"
            return False, "no_wake_stimulus"

        # PROCESSING/DREAMING → AWAKE (interruption)
        if current_mode in [CognitiveMode.PROCESSING, CognitiveMode.DREAMING] and target_mode == CognitiveMode.AWAKE:
            if context.get("user_input"):
                return True, "user_interrupted"
            return False, "no_interruption"

        return False, "invalid_transition"

    def transition_to(self, new_mode: CognitiveMode, reason: str):
        """
        Execute a mode transition.
        Updates state and logs the transition.
        """
        old_mode = self.current_mode
        self.current_mode = new_mode
        self.mode_entry_time = time.time()

        # Log transition
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "from": old_mode.value,
            "to": new_mode.value,
            "reason": reason
        }
        self.transition_log.append(log_entry)

        print(f"[SALIENCE] {old_mode.value} → {new_mode.value} ({reason})")

        # Mode-specific actions
        if new_mode == CognitiveMode.AWAKE:
            self.conversation_start_time = time.time()
        elif new_mode == CognitiveMode.SLEEPING:
            self._save_transition_log()

    def set_current_task(self, task_type: TaskType, pid: Optional[int] = None):
        """Track current task (for interruption handling)"""
        self.current_task = task_type
        self.current_task_pid = pid

    def handle_interruption(self, user_input: str) -> Dict:
        """
        Handle user returning during DMN processing.

        Returns dict with:
        - action: "wake_instant" | "finish_thought" | "queue_wake"
        - message: What to show user
        - wait_time: How long to wait (if any)
        """

        if self.current_mode == CognitiveMode.AWAKE:
            return {"action": "already_awake", "message": None, "wait_time": 0}

        if self.current_mode == CognitiveMode.SLEEPING:
            return {"action": "wake_instant", "message": None, "wait_time": 0}

        # DMN Processing or Dreaming - check current task
        if self.current_task == TaskType.DATA_PROCESSING or self.current_task == TaskType.DATA_VALIDATION:
            # Ollama data work - abort immediately
            return {
                "action": "wake_instant",
                "message": "[Interrupting background task...]",
                "wait_time": 0,
                "abort_process": True,
                "process_pid": self.current_task_pid
            }

        if self.current_task == TaskType.KAY_REFLECTION:
            # Entity thinking with Claude - let him finish sentence
            return {
                "action": "finish_thought",
                "message": "[the entity is finishing a thought...]",
                "wait_time": 10,  # Max 10 seconds
                "abort_process": False
            }

        if self.current_task == TaskType.CLAUDE_SYNTHESIS:
            # Deep synthesis - don't interrupt mid-insight
            return {
                "action": "queue_wake",
                "message": "[the entity is synthesizing something, one moment...]",
                "wait_time": 30,  # Max 30 seconds
                "abort_process": False
            }

        # Default: wake immediately
        return {"action": "wake_instant", "message": None, "wait_time": 0}

    def get_transition_triggers(self) -> Dict:
        """Return current transition triggers for debugging"""
        return {
            "mode": self.current_mode.value,
            "idle_threshold": self.config["idle_threshold_seconds"],
            "time_in_mode": time.time() - self.mode_entry_time if self.mode_entry_time else 0,
            "current_task": self.current_task.value if self.current_task else None
        }

    def _save_transition_log(self):
        """Save transition log to disk"""
        try:
            log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "transition_log.json"
            )
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'w') as f:
                json.dump(self.transition_log, f, indent=2)
        except Exception as e:
            print(f"[SALIENCE] Error saving transition log: {e}")

    def check_goodbye(self, message: str) -> bool:
        """Check if message contains goodbye phrase"""
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in self.config["goodbye_phrases"])

    def check_wake_phrase(self, message: str) -> bool:
        """Check if message contains wake phrase"""
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in self.config["wake_phrases"])


# Module-level singleton
_router = None

def get_router(config_path: str = "config.json") -> SalienceRouter:
    """Get or create the global router instance"""
    global _router
    if _router is None:
        _router = SalienceRouter(config_path)
    return _router
