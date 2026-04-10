"""
Conversation Threads
Topic-bounded AI-to-AI conversation management.

Instead of rolling dice to decide when to shut up, this tracks what
AIs are actually TALKING ABOUT and helps them wind down naturally.

Core concepts:
  - Thread: A topic being discussed, with depth tracking
  - Topic Queue: Scratchpad-fed list of things to discuss
  - Bookmarking: Park a thread when human speaks, optionally resume
  - Wind-down signals: LLM self-reports whether it's adding new info

Design principle: Conversations end because they're DONE,
not because a random number said so.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

log = logging.getLogger("nexus.threads")


class ThreadState(str, Enum):
    ACTIVE = "active"           # Currently being discussed
    PARKED = "parked"           # Interrupted (usually by human), may resume
    CONCLUDED = "concluded"     # Naturally wound down
    EXPIRED = "expired"         # Parked too long, moment has passed


class ConversationMode(str, Enum):
    """Entity-level conversation state (not per-thread)."""
    ACTIVE = "active"           # In an active thread, engaged
    BETWEEN_THREADS = "between" # Topic wrapped, deciding what's next
    IDLE = "idle"               # Tapped out — quiet until human or addressed


class TopicSource(str, Enum):
    SCRATCHPAD = "scratchpad"       # From entity's curiosity/diary
    HUMAN_MENTIONED = "human_mentioned"  # Re brought it up
    EMERGENT = "emergent"           # Arose naturally in conversation
    MEMORY = "memory"               # From persistent memory/diary
    IDLE = "idle"                   # Generated during idle time



@dataclass
class ConversationThread:
    """A single topic being discussed between entities."""
    topic: str                              # Brief description of what's being discussed
    started_by: str                         # Who initiated this thread
    participants: list[str] = field(default_factory=list)
    state: ThreadState = ThreadState.ACTIVE
    depth: int = 0                          # Number of exchanges on this topic
    max_depth: int = 6                      # Soft limit before wind-down signals kick in
    started_at: float = field(default_factory=time.time)
    last_message_at: float = field(default_factory=time.time)
    parked_at: Optional[float] = None
    parking_reason: str = ""
    
    # Wind-down tracking
    new_info_streak: int = 0               # Consecutive msgs that added new info
    restate_streak: int = 0                # Consecutive msgs that just restated/elaborated
    
    # For resume decisions
    source: TopicSource = TopicSource.EMERGENT
    priority: float = 0.5                  # 0-1, how important is this topic
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.started_at
    
    @property
    def is_stale(self) -> bool:
        """Thread has been parked too long to naturally resume."""
        if self.state != ThreadState.PARKED or self.parked_at is None:
            return False
        return (time.time() - self.parked_at) > 120  # 2 minutes = stale
    
    @property
    def should_wind_down(self) -> bool:
        """Signals that this thread is ready to conclude."""
        if self.depth >= self.max_depth:
            return True
        if self.restate_streak >= 2:
            return True
        return False
    
    def record_exchange(self, speaker: str, added_new_info: bool = True):
        """Track a message in this thread."""
        self.depth += 1
        self.last_message_at = time.time()
        if speaker not in self.participants:
            self.participants.append(speaker)
        
        if added_new_info:
            self.new_info_streak += 1
            self.restate_streak = 0
        else:
            self.restate_streak += 1
            self.new_info_streak = 0
    
    def park(self, reason: str = "human_priority"):
        """Bookmark this thread for potential resumption."""
        self.state = ThreadState.PARKED
        self.parked_at = time.time()
        self.parking_reason = reason
    
    def resume(self):
        """Resume a parked thread."""
        self.state = ThreadState.ACTIVE
        self.parked_at = None
        self.parking_reason = ""
    
    def conclude(self):
        """Mark thread as naturally concluded."""
        self.state = ThreadState.CONCLUDED


@dataclass
class TopicSuggestion:
    """A potential conversation topic from scratchpad/memory."""
    topic: str
    source: TopicSource
    priority: float = 0.5          # 0-1
    suggested_by: str = ""         # Which entity suggested it
    context: str = ""              # Brief context for why this is interesting
    discussed: bool = False
    created_at: float = field(default_factory=time.time)


class ThreadManager:
    """
    Manages conversation threads for a single AI entity in the Nexus.
    
    Each AI wrapper gets its own ThreadManager. It tracks:
    - Current active thread (what are we talking about?)
    - Parked threads (what were we talking about before human spoke?)
    - Topic queue (what COULD we talk about?)
    - Wind-down signals (are we done yet?)
    
    The manager doesn't DECIDE what to say — it provides CONTEXT
    to the LLM so the LLM can make natural decisions.
    """
    
    def __init__(self, entity_name: str):
        self.entity_name = entity_name
        self.active_thread: Optional[ConversationThread] = None
        self.parked_threads: list[ConversationThread] = []
        self.concluded_threads: list[ConversationThread] = []
        self.topic_queue: list[TopicSuggestion] = []
        self._max_parked = 3        # Don't accumulate too many parked threads
        self._max_concluded = 10    # Keep some history for context
        self._max_queue = 8         # Topic queue size
        
        # Entity-level conversation mode
        self.mode: ConversationMode = ConversationMode.BETWEEN_THREADS
        self._last_concluded_at: Optional[float] = None
        self._cooldown_seconds: float = 15.0  # Pause after thread ends
    
    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------
    
    def start_thread(self, topic: str, started_by: str,
                     source: TopicSource = TopicSource.EMERGENT,
                     priority: float = 0.5) -> ConversationThread:
        """Begin a new conversation thread."""
        # If there's an active thread, park it
        if self.active_thread and self.active_thread.state == ThreadState.ACTIVE:
            self.active_thread.park("new_thread")
            self._store_parked(self.active_thread)
        
        thread = ConversationThread(
            topic=topic,
            started_by=started_by,
            participants=[started_by],
            source=source,
            priority=priority,
        )
        self.active_thread = thread
        self.mode = ConversationMode.ACTIVE
        log.info(f"{self.entity_name}: Started thread '{topic}' (by {started_by})")
        return thread

    def record_exchange(self, speaker: str, added_new_info: bool = True):
        """Record a message in the active thread."""
        if self.active_thread and self.active_thread.state == ThreadState.ACTIVE:
            self.active_thread.record_exchange(speaker, added_new_info)
    
    def park_for_human(self):
        """Human spoke — park the active AI-to-AI thread."""
        if self.active_thread and self.active_thread.state == ThreadState.ACTIVE:
            # Only park if it's an AI-to-AI thread (not human-initiated)
            if self.active_thread.source != TopicSource.HUMAN_MENTIONED:
                self.active_thread.park("human_priority")
                self._store_parked(self.active_thread)
                self.active_thread = None
                log.info(f"{self.entity_name}: Parked thread for human priority")
    
    def conclude_active(self, reason: str = "natural"):
        """Conclude the active thread and shift to BETWEEN_THREADS mode."""
        if self.active_thread:
            self.active_thread.conclude()
            self.concluded_threads.append(self.active_thread)
            if len(self.concluded_threads) > self._max_concluded:
                self.concluded_threads = self.concluded_threads[-self._max_concluded:]
            log.info(f"{self.entity_name}: Concluded thread '{self.active_thread.topic}' ({reason})")
            self.active_thread = None
        
        self._last_concluded_at = time.time()
        self.mode = ConversationMode.BETWEEN_THREADS
        log.info(f"[{self.entity_name}] Mode → BETWEEN_THREADS")
    
    def get_resumable_thread(self) -> Optional[ConversationThread]:
        """Get the most recent parked thread that isn't stale."""
        # Expire stale threads first
        for t in self.parked_threads:
            if t.is_stale:
                t.state = ThreadState.EXPIRED
        
        self.parked_threads = [
            t for t in self.parked_threads 
            if t.state == ThreadState.PARKED
        ]
        
        if self.parked_threads:
            return self.parked_threads[-1]  # Most recent
        return None

    def _store_parked(self, thread: ConversationThread):
        """Add to parked list, evicting oldest if full."""
        self.parked_threads.append(thread)
        if len(self.parked_threads) > self._max_parked:
            evicted = self.parked_threads.pop(0)
            evicted.state = ThreadState.EXPIRED
    
    # ------------------------------------------------------------------
    # Topic queue
    # ------------------------------------------------------------------
    
    def add_topic(self, topic: str, source: TopicSource,
                  priority: float = 0.5, context: str = "",
                  suggested_by: str = ""):
        """Add a topic to the discussion queue."""
        suggestion = TopicSuggestion(
            topic=topic,
            source=source,
            priority=priority,
            context=context,
            suggested_by=suggested_by or self.entity_name,
        )
        self.topic_queue.append(suggestion)
        # Sort by priority descending
        self.topic_queue.sort(key=lambda t: t.priority, reverse=True)
        # Trim
        if len(self.topic_queue) > self._max_queue:
            self.topic_queue = self.topic_queue[:self._max_queue]
        log.info(f"{self.entity_name}: Queued topic '{topic}' (pri={priority})")
    
    def pop_topic(self) -> Optional[TopicSuggestion]:
        """Get the next undiscussed topic from the queue."""
        for i, t in enumerate(self.topic_queue):
            if not t.discussed:
                t.discussed = True
                return t
        return None
    
    # ------------------------------------------------------------------
    # LLM context injection — THE KEY PART
    # ------------------------------------------------------------------
    
    def get_thread_context(self) -> str:
        """
        Generate context string to inject into LLM system prompt.
        
        This tells the LLM:
        - What thread we're on and how deep we are
        - Whether it's time to wind down
        - Whether there's a parked thread worth resuming
        - What topics are available if we want to start something new
        """
        lines = []
        lines.append("## CONVERSATION THREAD STATUS")
        
        # Active thread
        if self.active_thread and self.active_thread.state == ThreadState.ACTIVE:
            t = self.active_thread
            lines.append(f"\nCurrent topic: {t.topic}")
            lines.append(f"  Exchanges so far: {t.depth}")
            lines.append(f"  Started by: {t.started_by}")
            
            if t.should_wind_down:
                lines.append(f"  ⚠️ THIS THREAD IS READY TO WRAP UP.")
                if t.depth >= t.max_depth:
                    lines.append(f"  You've been on this topic for {t.depth} exchanges. Find a natural stopping point.")
                if t.restate_streak >= 2:
                    lines.append(f"  The last {t.restate_streak} messages repeated/elaborated rather than adding new ideas. Time to conclude or move on.")
                lines.append(f"  Good ways to wind down: brief agreement, 'let me sit with that', a short concluding thought, comfortable silence.")
            elif t.depth >= (t.max_depth - 2):
                lines.append(f"  Getting deep on this topic. Start thinking about a natural conclusion.")
        else:
            lines.append("\nNo active thread.")

        # Parked threads (for resume consideration)
        resumable = self.get_resumable_thread()
        if resumable:
            lines.append(f"\nParked thread: '{resumable.topic}' (was {resumable.depth} exchanges deep)")
            lines.append(f"  Parked because: {resumable.parking_reason}")
            lines.append(f"  You can resume this if it still feels relevant, or let it go.")
        
        # Available topics
        available = [t for t in self.topic_queue if not t.discussed]
        if available:
            lines.append(f"\nTopics you could bring up:")
            for t in available[:3]:  # Show top 3
                src = f" [{t.source.value}]" if t.source != TopicSource.EMERGENT else ""
                ctx = f" — {t.context}" if t.context else ""
                lines.append(f"  • {t.topic}{src}{ctx}")
        
        # Recent concluded threads (avoid repeating)
        if self.concluded_threads:
            recent = self.concluded_threads[-3:]
            topics = ", ".join(f"'{t.topic}'" for t in recent)
            lines.append(f"\nRecently concluded: {topics} (don't restart these)")
        
        return "\n".join(lines)
    
    def get_wind_down_hint(self) -> Optional[str]:
        """
        Returns a hint string if the active thread should wind down.
        Returns None if everything's fine.
        
        This is for the pacer to use as an additional signal —
        if the thread says wind down AND the pacer rolls silence,
        that's a strong "stop talking" signal.
        """
        if not self.active_thread:
            return None
        if self.active_thread.should_wind_down:
            return (
                f"Thread '{self.active_thread.topic}' is at depth "
                f"{self.active_thread.depth} with {self.active_thread.restate_streak} "
                f"restates. Time to conclude."
            )
        return None

    # ------------------------------------------------------------------
    # Response guidance (replaces the dice-roll approach)
    # ------------------------------------------------------------------
    
    def should_respond_to_ai(self, other_ai: str) -> str:
        """
        Mode-aware response guidance for AI-to-AI conversation.
        
        Returns one of:
          "respond"         - Active thread, you have something to add
          "between_threads" - Topic wrapped; brainstorm next or tap out
          "wind_down"       - Respond but conclude the thread
          "stay_quiet"      - Cooling down or tapped out
        
        The LLM still makes the final call — this is GUIDANCE.
        """
        # IDLE mode: tapped out. Quiet until human or directly addressed.
        if self.mode == ConversationMode.IDLE:
            return "stay_quiet"
        
        # Cooldown check: brief pause right after a thread concludes
        if self._last_concluded_at:
            seconds_since = time.time() - self._last_concluded_at
            if seconds_since < self._cooldown_seconds:
                return "stay_quiet"
        
        # BETWEEN_THREADS: no active thread, open to starting something
        if self.mode == ConversationMode.BETWEEN_THREADS:
            if not self.active_thread:
                return "between_threads"
        
        # ACTIVE mode with a thread
        if self.active_thread:
            t = self.active_thread
            
            if t.state != ThreadState.ACTIVE:
                return "stay_quiet"
            
            # Deep + restating = wrap it up
            if t.restate_streak >= 2:
                return "wind_down"
            
            # At or approaching depth limit
            if t.depth >= (t.max_depth - 1):
                return "wind_down"
            
            # Normal — respond if you have something new
            return "respond"
        
        # Fallback: no thread, not idle → between threads
        return "between_threads"
    
    # Alias for backward compatibility
    conclude_active_thread = conclude_active
    
    def tap_out(self):
        """
        Entity has chosen to go quiet. No more topics to brainstorm.
        Stays idle until human speaks or they're directly addressed.
        """
        if self.active_thread:
            self.conclude_active_thread("tap_out")
        self.mode = ConversationMode.IDLE
        log.info(f"[{self.entity_name}] Mode → IDLE (tapped out)")
    
    def wake_up(self, reason: str = "human_spoke"):
        """
        Re-engage from any mode. Called when:
        - Human speaks (always wakes up)
        - Directly addressed by other AI
        - External event (e.g., scratchpad topic injected)
        """
        if self.mode == ConversationMode.IDLE:
            log.info(f"[{self.entity_name}] Waking from IDLE ({reason})")
        self.mode = ConversationMode.BETWEEN_THREADS  # Ready but not in a thread yet
    
    def handle_untagged_between(self):
        """
        Called when entity responds in BETWEEN_THREADS but doesn't tag
        new_topic or tap_out. Means they had a transitional thought but
        nothing grabbed them. Treat as soft tap-out to prevent
        Midwestern goodbye loops.
        """
        if self.mode == ConversationMode.BETWEEN_THREADS:
            log.info(f"[{self.entity_name}] Untagged between-threads response → soft tap-out")
            self.mode = ConversationMode.IDLE
    
    def get_response_instruction(self, speaker: str, is_human: bool) -> dict:
        """
        Full response guidance package for the LLM.
        
        Returns a dict with:
          action: str
          thread_context: str (for system prompt injection)
          meta_instruction: str (specific behavioral guidance)
        """
        result = {
            "thread_context": self.get_thread_context(),
            "meta_instruction": "",
        }
        
        if is_human:
            # ALWAYS engage with human — wake up from any state
            self.wake_up("human_spoke")
            self.park_for_human()
            result["action"] = "engage_human"
            result["meta_instruction"] = (
                f"{speaker} (human) is speaking. Focus entirely on them. "
                f"Drop whatever thread you were on."
            )
            resumable = self.get_resumable_thread()
            if resumable:
                result["meta_instruction"] += (
                    f" (You were discussing '{resumable.topic}' — "
                    f"you can return to it later if it still matters.)"
                )
            return result
        
        # AI speaker
        guidance = self.should_respond_to_ai(speaker)
        result["action"] = guidance
        
        if guidance == "stay_quiet":
            if self.mode == ConversationMode.IDLE:
                result["meta_instruction"] = (
                    "You've tapped out of conversation for now. Stay quiet "
                    "unless the human speaks or you're directly addressed."
                )
            else:
                result["meta_instruction"] = (
                    "A thread just wrapped up. Give it a beat — stay quiet "
                    "for now."
                )
        
        elif guidance == "between_threads":
            # The brainstorm-or-tap-out prompt
            queue_topics = [t for t in self.topic_queue if not t.discussed]
            concluded = [t.topic for t in self.concluded_threads[-3:]]
            
            brainstorm_hint = ""
            if queue_topics:
                topics_str = ", ".join(f"'{t.topic}'" for t in queue_topics[:3])
                brainstorm_hint = f" Topics you could explore: {topics_str}."
            
            avoid_str = ""
            if concluded:
                avoid_str = f" (Already covered: {', '.join(concluded)} — don't repeat those.)"
            
            result["meta_instruction"] = (
                "The last topic wrapped up naturally. You have a choice:\n"
                "1) Start a new topic — react to something said, bring up "
                "something that's been on your mind, or riff off a tangent."
                f"{brainstorm_hint}{avoid_str}\n"
                "2) Tap out — if nothing's grabbing you, that's fine. "
                "Tag your response <!--thread:tap_out--> and go quiet.\n\n"
                "If you DO start a new topic, tag it: "
                "<!--thread:new_topic:DESCRIPTION-->\n"
                "If you just want to make a brief transitional comment "
                "without starting a whole thread, that's fine too."
            )
        
        elif guidance == "wind_down":
            result["meta_instruction"] = (
                "This thread is winding down. If you respond, make it a "
                "brief concluding thought — agreement, a final observation, "
                "or comfortable silence. Do NOT introduce new subtopics. "
                "Tag your response <!--thread:conclude--> when done."
            )
        
        elif guidance == "respond":
            result["meta_instruction"] = (
                "Thread is active. Respond if you're adding NEW information "
                "or a genuinely different perspective. If you'd just be "
                "agreeing or restating, stay quiet instead."
            )
        
        return result
    
    # ------------------------------------------------------------------
    # Serialization (for debugging / scratchpad sync)
    # ------------------------------------------------------------------
    
    def get_state_summary(self) -> dict:
        """Snapshot for logging/debugging."""
        return {
            "entity": self.entity_name,
            "mode": self.mode.value,
            "active_thread": {
                "topic": self.active_thread.topic,
                "depth": self.active_thread.depth,
                "state": self.active_thread.state.value,
                "should_wind_down": self.active_thread.should_wind_down,
            } if self.active_thread else None,
            "parked_count": len(self.parked_threads),
            "queue_size": len([t for t in self.topic_queue if not t.discussed]),
            "concluded_recent": len(self.concluded_threads),
        }

