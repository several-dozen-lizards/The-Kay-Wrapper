"""
Continuous Session Engine
Manages long-running Reed sessions with curated compression
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, asdict

@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    turn_id: int
    timestamp: str
    role: Literal["user", "reed", "system"]
    content: str
    token_count: int
    emotional_weight: float  # 0.0-1.0
    flagged_by_reed: bool = False
    preservation_level: Optional[Literal["PRESERVE", "COMPRESS", "ARCHIVE", "DISCARD"]] = None
    scratchpad_refs: List[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.scratchpad_refs is None:
            self.scratchpad_refs = []
        if self.tags is None:
            self.tags = []

@dataclass
class ConversationSegment:
    """Bundle of related turns"""
    segment_id: int
    start_turn: int
    end_turn: int
    turns: List[ConversationTurn]
    topic: str
    total_tokens: int
    max_emotional_weight: float
    preservation_level: Optional[str] = None

class ContinuousSession:
    """
    Manages Reed's continuous session with compression

    Key features:
    - Single long-running conversation
    - Periodic compression reviews
    - Reed-curated preservation decisions
    - Automatic checkpointing
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.session_file = self.data_dir / "continuous_session.json"
        self.checkpoint_dir = self.data_dir / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)

        # Session state
        self.session_id: str = ""
        self.start_time: datetime = None
        self.turns: List[ConversationTurn] = []
        self.turn_counter: int = 0
        self.total_tokens: int = 0

        # Compression state
        self.last_compression_turn: int = 0
        self.compression_threshold_turns: int = 25
        self.compression_threshold_tokens: int = 150000

        # Checkpoint state
        self.last_checkpoint_time: float = 0
        self.checkpoint_interval: int = 900  # 15 minutes

        # Curation state
        self.pending_review_turns: List[int] = []
        self.curation_history: List[Dict] = []

    def start_session(self) -> str:
        """Start a new continuous session"""
        self.session_id = f"continuous_{int(time.time())}"
        self.start_time = datetime.now()
        self.turns = []
        self.turn_counter = 0
        self.total_tokens = 0
        self.last_checkpoint_time = time.time()

        print(f"[CONTINUOUS SESSION] Started: {self.session_id}")
        return self.session_id

    def add_turn(
        self,
        role: str,
        content: str,
        token_count: int,
        emotional_weight: float = 0.0,
        flagged: bool = False,
        scratchpad_refs: List[str] = None,
        tags: List[str] = None
    ) -> ConversationTurn:
        """Add a turn to the continuous session"""

        turn = ConversationTurn(
            turn_id=self.turn_counter,
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            token_count=token_count,
            emotional_weight=emotional_weight,
            flagged_by_reed=flagged,
            scratchpad_refs=scratchpad_refs or [],
            tags=tags or []
        )

        self.turns.append(turn)
        self.turn_counter += 1
        self.total_tokens += token_count

        # Check if compression needed
        turns_since_compression = self.turn_counter - self.last_compression_turn
        if (turns_since_compression >= self.compression_threshold_turns or
            self.total_tokens >= self.compression_threshold_tokens):
            self.trigger_compression_review()

        # Check if checkpoint needed
        if time.time() - self.last_checkpoint_time >= self.checkpoint_interval:
            self.create_checkpoint()

        return turn

    def flag_turn(self, turn_id: int, reason: str = ""):
        """Reed flags a turn as important during conversation"""
        if turn_id < len(self.turns):
            self.turns[turn_id].flagged_by_reed = True
            if reason:
                self.turns[turn_id].tags.append(f"flag_reason:{reason}")
            print(f"[FLAGGED] Turn {turn_id}: {reason or 'Important'}")

    def needs_compression_review(self) -> bool:
        """Check if compression review is needed"""
        turns_since = self.turn_counter - self.last_compression_turn
        return (turns_since >= self.compression_threshold_turns or
                self.total_tokens >= self.compression_threshold_tokens)

    def trigger_compression_review(self):
        """Mark that compression review is needed"""
        # Identify turns to review (since last compression)
        self.pending_review_turns = list(range(
            self.last_compression_turn,
            self.turn_counter
        ))
        print(f"[COMPRESSION] Review triggered: {len(self.pending_review_turns)} turns")

    def get_review_segments(self) -> List[ConversationSegment]:
        """
        Bundle turns into semantic segments for easier review

        Groups consecutive turns by:
        - Topic continuity
        - Time proximity
        - Emotional clustering
        """
        segments = []
        current_segment_turns = []
        current_topic = ""
        segment_id = 0

        for turn_id in self.pending_review_turns:
            turn = self.turns[turn_id]

            # Simple topic detection (can be enhanced)
            # For now, bundle consecutive same-role turns
            if not current_segment_turns:
                current_segment_turns.append(turn)
            elif len(current_segment_turns) < 5:  # Max 5 turns per segment
                current_segment_turns.append(turn)
            else:
                # Finalize current segment
                segment = self._create_segment(
                    segment_id,
                    current_segment_turns
                )
                segments.append(segment)
                segment_id += 1
                current_segment_turns = [turn]

        # Add final segment
        if current_segment_turns:
            segment = self._create_segment(segment_id, current_segment_turns)
            segments.append(segment)

        return segments

    def _create_segment(
        self,
        segment_id: int,
        turns: List[ConversationTurn]
    ) -> ConversationSegment:
        """Create a conversation segment from turns"""
        total_tokens = sum(t.token_count for t in turns)
        max_emotion = max(t.emotional_weight for t in turns)

        # Simple topic extraction (first user message)
        user_turns = [t for t in turns if t.role == "user"]
        topic = user_turns[0].content[:100] if user_turns else "Continuation"

        return ConversationSegment(
            segment_id=segment_id,
            start_turn=turns[0].turn_id,
            end_turn=turns[-1].turn_id,
            turns=turns,
            topic=topic,
            total_tokens=total_tokens,
            max_emotional_weight=max_emotion
        )

    def apply_curation_decision(
        self,
        segment_id: int,
        decision: Literal["PRESERVE", "COMPRESS", "ARCHIVE", "DISCARD"],
        notes: str = ""
    ):
        """Apply Reed's curation decision to a segment"""
        segments = self.get_review_segments()
        if segment_id < len(segments):
            segment = segments[segment_id]

            # Mark all turns in segment
            for turn in segment.turns:
                self.turns[turn.turn_id].preservation_level = decision

            # Record decision
            self.curation_history.append({
                "segment_id": segment_id,
                "turns": f"{segment.start_turn}-{segment.end_turn}",
                "decision": decision,
                "notes": notes,
                "timestamp": datetime.now().isoformat()
            })

            print(f"[CURATION] Segment {segment_id} → {decision}: {segment.topic[:50]}")

    def compress_context(self) -> str:
        """
        Execute compression based on Reed's decisions

        Returns compressed conversation context
        """
        preserved = []
        compressed = []
        archived = []

        for turn in self.turns[self.last_compression_turn:]:
            level = turn.preservation_level or "COMPRESS"

            if level == "PRESERVE":
                # Keep full turn
                preserved.append(f"[Turn {turn.turn_id}] {turn.role}: {turn.content}")

            elif level == "COMPRESS":
                # Summarize turn (1-2 sentences)
                summary = self._summarize_turn(turn)
                compressed.append(f"[Turn {turn.turn_id}] {summary}")

            elif level == "ARCHIVE":
                # Minimal reference
                archived.append(f"[Turn {turn.turn_id}] {turn.role} - {turn.content[:30]}")

            # DISCARD = skip entirely

        # Build compressed context
        result = []

        if preserved:
            result.append("\n=== PRESERVED CONVERSATION ===\n")
            result.extend(preserved)

        if compressed:
            result.append("\n=== COMPRESSED SUMMARIES ===\n")
            result.extend(compressed)

        if archived:
            result.append("\n=== ARCHIVED (minimal) ===\n")
            result.extend(archived)

        compressed_context = "\n".join(result)

        # Update state
        self.last_compression_turn = self.turn_counter
        self.pending_review_turns = []

        # Recalculate token count for compressed context
        # (rough estimate: compressed is ~20% of original)
        self.total_tokens = int(self.total_tokens * 0.2)

        return compressed_context

    def _summarize_turn(self, turn: ConversationTurn) -> str:
        """
        Summarize a turn for compression

        TODO: Use LLM for better summaries
        For now, just truncate
        """
        max_len = 200
        if len(turn.content) <= max_len:
            return f"{turn.role}: {turn.content}"
        return f"{turn.role}: {turn.content[:max_len]}..."

    def save_session_log(self, filepath: str):
        """Save session as human-readable markdown log"""
        from pathlib import Path as _P
        _P(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            f"# Reed Continuous Session Log",
            f"**Session:** {self.session_id}",
            f"**Started:** {self.start_time.isoformat() if self.start_time else 'unknown'}",
            f"**Turns:** {self.turn_counter}",
            f"**Total Tokens:** {self.total_tokens}",
            f"**Saved:** {datetime.now().isoformat()}",
            "",
            "---",
            ""
        ]
        
        for turn in self.turns:
            flag_marker = " 🚩" if turn.flagged_by_reed else ""
            emotion_marker = f" [ew:{turn.emotional_weight:.1f}]" if turn.emotional_weight > 0.3 else ""
            lines.append(f"### Turn {turn.turn_id} ({turn.role}){flag_marker}{emotion_marker}")
            lines.append(f"*{turn.timestamp}*")
            lines.append("")
            # Truncate very long content for readability
            content = turn.content if len(turn.content) <= 500 else turn.content[:500] + "..."
            lines.append(content)
            lines.append("")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        print(f"[CONTINUOUS] Session log saved: {filepath}")

    def create_checkpoint(self):
        """Create a checkpoint of current session state"""
        checkpoint = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "turn_counter": self.turn_counter,
            "total_tokens": self.total_tokens,
            "turns": [asdict(t) for t in self.turns],
            "curation_history": self.curation_history,
            "last_compression_turn": self.last_compression_turn
        }

        checkpoint_file = self.checkpoint_dir / f"checkpoint_{int(time.time())}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        self.last_checkpoint_time = time.time()
        print(f"[CHECKPOINT] Saved: {checkpoint_file.name}")

        # Cleanup old checkpoints (keep last 10)
        checkpoints = sorted(self.checkpoint_dir.glob("checkpoint_*.json"))
        if len(checkpoints) > 10:
            for old_checkpoint in checkpoints[:-10]:
                old_checkpoint.unlink()

    def load_from_checkpoint(self, checkpoint_file: Path):
        """Restore session from checkpoint"""
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)

        self.session_id = data["session_id"]
        self.turn_counter = data["turn_counter"]
        self.total_tokens = data["total_tokens"]
        self.curation_history = data["curation_history"]
        self.last_compression_turn = data["last_compression_turn"]

        # Reconstruct turns
        self.turns = [ConversationTurn(**t) for t in data["turns"]]

        print(f"[RECOVERY] Loaded from {checkpoint_file.name}")
        print(f"[RECOVERY] Restored {len(self.turns)} turns")
