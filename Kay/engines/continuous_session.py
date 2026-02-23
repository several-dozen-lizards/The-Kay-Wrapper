"""
Continuous Session Engine
Manages long-running Kay sessions with curated compression
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
    role: Literal["user", "kay", "system"]
    content: str
    token_count: int
    emotional_weight: float  # 0.0-1.0
    flagged_by_kay: bool = False
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
    Manages Kay's continuous session with compression
    
    Key features:
    - Single long-running conversation
    - Periodic compression reviews
    - Kay-curated preservation decisions
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
            flagged_by_kay=flagged,
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
        """Kay flags a turn as important during conversation"""
        if turn_id < len(self.turns):
            self.turns[turn_id].flagged_by_kay = True
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
        """Apply Kay's curation decision to a segment"""
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
        Execute compression based on Kay's decisions
        
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

    def generate_session_summary(self, working_memory_start_turn: int) -> str:
        """
        Generate compressed summary of turns before the working memory window.

        This gives Kay awareness of the full conversation arc without blowing
        the token budget. Preserved/important turns get more detail.

        Args:
            working_memory_start_turn: The turn_id where verbatim working memory begins.
                Everything before this gets summarized.

        Returns:
            A compressed text summary of older conversation context.
        """
        older_turns = [t for t in self.turns if t.turn_id < working_memory_start_turn]
        if not older_turns:
            return ""

        # Use curation decisions to weight importance
        preserved_turns = []
        other_turns = []
        for turn in older_turns:
            is_preserved = self._is_turn_preserved(turn.turn_id)
            if is_preserved or turn.flagged_by_kay or turn.emotional_weight > 0.7:
                preserved_turns.append(turn)
            else:
                other_turns.append(turn)

        # Build summary sections
        summary_parts = []

        # Session metadata
        session_start = older_turns[0].timestamp if older_turns else "unknown"
        summary_parts.append(f"[Session context: {len(older_turns)} earlier turns, session started {session_start}]")

        # Include preserved/important turns with more detail
        if preserved_turns:
            summary_parts.append("\nKey moments from earlier in our conversation:")
            # Cap at 15 most recent important turns to control token usage
            for turn in preserved_turns[-15:]:
                role = "Re" if turn.role == "user" else "Kay"
                # Truncate content for summary while preserving essence
                content = turn.content[:200] + "..." if len(turn.content) > 200 else turn.content
                summary_parts.append(f"- {role}: {content}")

        # Summarize themes from other turns (topic-level mention only)
        if other_turns:
            topics = set()
            for turn in other_turns:
                # Extract first sentence as topic indicator
                first_sentence = turn.content.split('.')[0][:80]
                if len(first_sentence) > 20:  # Skip very short fragments
                    topics.add(first_sentence)
            if topics:
                topic_list = list(topics)[:10]  # Cap at 10 topics
                summary_parts.append(f"\nOther topics discussed: {'; '.join(topic_list)}")

        return "\n".join(summary_parts)

    def _is_turn_preserved(self, turn_id: int) -> bool:
        """
        Check if a turn falls within a PRESERVE curation segment.

        Args:
            turn_id: The turn ID to check

        Returns:
            True if the turn was marked PRESERVE in curation history
        """
        for decision in self.curation_history:
            if decision.get("decision") == "PRESERVE":
                turns_range = decision.get("turns", "")
                if "-" in turns_range:
                    try:
                        start, end = turns_range.split("-")
                        if int(start) <= turn_id <= int(end):
                            return True
                    except (ValueError, AttributeError):
                        # Skip malformed range entries
                        continue
        return False
