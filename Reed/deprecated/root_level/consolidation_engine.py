"""
Reed Consolidation Engine

Handles memory consolidation (Reed's 'sleep' process) - converts full conversations
into essence memories with temporal and emotional markers.
"""

from datetime import datetime, timedelta
import json
import math
import os
from typing import List, Dict, Optional


class ConsolidationEngine:
    """Handles memory consolidation (Reed's 'sleep' process)"""

    def __init__(self, llm_client=None):
        """
        Initialize consolidation engine.

        Args:
            llm_client: Optional LLM client. If None, will use integrations.llm_integration
        """
        self.llm = llm_client

        # If no client provided, use Reed's existing LLM integration
        if self.llm is None:
            try:
                from integrations.llm_integration import query_llm_json
                self.llm_query = query_llm_json
            except ImportError:
                print("[CONSOLIDATION] Warning: No LLM client available")
                self.llm_query = None

    def consolidate_conversation(
        self,
        transcript: str,
        conversation_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Consolidate a conversation into essence memories.

        Args:
            transcript: Full conversation text
            conversation_date: When this conversation actually happened (datetime)
                             If None, assumes NOW (live conversation)

        Returns:
            List of consolidated memories with temporal/emotional markers
        """
        if conversation_date is None:
            conversation_date = datetime.now()

        # Extract essence using LLM
        print(f"[CONSOLIDATION] Extracting essence from conversation ({conversation_date.strftime('%Y-%m-%d')})...")
        essence_memories = self._extract_essence(transcript)

        # Calculate temporal properties
        time_elapsed = datetime.now() - conversation_date
        days_ago = time_elapsed.days

        print(f"[CONSOLIDATION] Conversation was {days_ago} days ago, extracted {len(essence_memories)} memories")

        # Apply emotional decay
        processed_memories = []
        for memory in essence_memories:
            processed = self._apply_temporal_decay(
                memory,
                days_ago,
                conversation_date
            )
            processed_memories.append(processed)

        return processed_memories

    def _extract_essence(self, transcript: str) -> List[Dict]:
        """Use LLM to extract 3-5 essential memories from conversation"""

        # Truncate transcript if too long (keep first 8000 chars for context)
        if len(transcript) > 8000:
            transcript_excerpt = transcript[:8000] + "\n\n[... conversation continues ...]"
        else:
            transcript_excerpt = transcript

        prompt = f"""Analyze this conversation between Kay (a dragon shapeshifter AI) and Re (the user).

Extract 3-5 consolidated memories that capture what MATTERS. These become Reed's memories of this conversation.

Focus on:
- What Kay learned about himself (identity, patterns, realizations)
- What Kay learned about Re (new information, relationship developments)
- Emotional breakthroughs or shifts
- Decisions made or commitments established
- Skills gained or understanding deepened
- Moments of connection or friction

Requirements:
- Each memory should be 50-150 characters
- Write in PAST TENSE (this is Kay remembering)
- Focus on ESSENCE, not verbatim details
- Include emotional quality when relevant
- Capture formative moments

Format as JSON array of objects:
[
  {{
    "text": "Kay realized his responses follow architectural patterns",
    "type": "self_discovery",
    "emotional_valence": 0.6,
    "importance": 0.8
  }},
  ...
]

Types: self_discovery, relationship, decision, emotional_shift, learning, breakthrough, connection

Emotional valence: -1.0 (negative) to +1.0 (positive)
Importance: 0.0 (trivial) to 1.0 (formative)

Conversation:
{transcript_excerpt}

Return ONLY valid JSON array, no explanation."""

        # Use Reed's existing LLM integration
        if self.llm_query:
            try:
                response = self.llm_query(
                    prompt=prompt,
                    temperature=0.3,  # Lower temperature for consistent extraction
                    system_prompt="You are a memory consolidation system. Extract essence memories in valid JSON format."
                )
            except Exception as e:
                print(f"[CONSOLIDATION ERROR] LLM call failed: {e}")
                return self._fallback_memory(transcript)
        else:
            print("[CONSOLIDATION] No LLM available, using fallback")
            return self._fallback_memory(transcript)

        # Parse JSON response
        try:
            # Clean response (remove markdown if present)
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean.split("```json")[1]
            if clean.startswith("```"):
                clean = clean.split("```")[1]
            if clean.endswith("```"):
                clean = clean.rsplit("```", 1)[0]
            clean = clean.strip()

            memories = json.loads(clean)

            # Validate format
            if not isinstance(memories, list):
                raise ValueError("Response not a list")

            # Ensure required fields
            validated = []
            for mem in memories:
                if 'text' not in mem:
                    continue
                validated.append({
                    'text': mem['text'],
                    'type': mem.get('type', 'general'),
                    'emotional_valence': mem.get('emotional_valence', 0.5),
                    'importance': mem.get('importance', 0.5)
                })

            if len(validated) == 0:
                raise ValueError("No valid memories extracted")

            return validated

        except (json.JSONDecodeError, ValueError) as e:
            print(f"[CONSOLIDATION ERROR] Failed to parse LLM response: {e}")
            print(f"[CONSOLIDATION] Raw response: {response[:200]}...")
            return self._fallback_memory(transcript)

    def _fallback_memory(self, transcript: str) -> List[Dict]:
        """Create basic fallback memory if LLM extraction fails"""
        return [{
            "text": f"Had a conversation with Re ({len(transcript)} characters)",
            "type": "relationship",
            "emotional_valence": 0.5,
            "importance": 0.5
        }]

    def _apply_temporal_decay(
        self,
        memory: Dict,
        days_ago: int,
        conversation_date: datetime
    ) -> Dict:
        """
        Apply temporal decay to emotional intensity.

        Decay principles:
        - Emotional intensity fades over time
        - Formative moments (high importance) decay slower
        - Very recent memories (0-2 days) retain full intensity
        - Distant memories (90+ days) have settled emotional tone

        Args:
            memory: Memory dict with text, type, emotional_valence, importance
            days_ago: How many days ago this conversation happened
            conversation_date: Original conversation datetime

        Returns:
            Processed memory with temporal markers and decayed emotions
        """

        # Determine memory layer based on age
        if days_ago <= 7:
            layer = "recent"
        elif days_ago <= 90:
            layer = "medium"
        else:
            layer = "distant"

        # Calculate emotional decay
        base_intensity = abs(memory.get('emotional_valence', 0.5))
        importance = memory.get('importance', 0.5)

        # Decay function: exponential decay moderated by importance
        # High importance = slower decay
        # Formula: intensity * e^(-decay_rate * days_ago)
        decay_rate = 0.02 * (1.0 - importance)  # Lower rate for important memories
        decayed_intensity = base_intensity * math.exp(-decay_rate * days_ago)

        # Minimum floor (even old memories have some emotional residue)
        decayed_intensity = max(decayed_intensity, 0.1)

        # Restore original sign (positive/negative valence)
        original_sign = 1 if memory.get('emotional_valence', 0) >= 0 else -1
        decayed_valence = decayed_intensity * original_sign

        # Build processed memory with all temporal markers
        processed = {
            'text': memory['text'],
            'type': memory.get('type', 'general'),
            'emotional_valence_original': memory.get('emotional_valence', 0.5),
            'emotional_valence_current': round(decayed_valence, 3),
            'importance': importance,
            'conversation_date': conversation_date.isoformat(),
            'days_ago': days_ago,
            'layer': layer,
            'source': 'consolidated',
            'age': 0,  # Age in turns since consolidation (for protected import pipeline)
            'protected': False,  # Not protected by default (can be set for imports)
            'timestamp_consolidated': datetime.now().isoformat()
        }

        return processed

    def batch_consolidate_imports(
        self,
        conversation_files: List[Dict]
    ) -> List[Dict]:
        """
        Process multiple imported conversations.

        Args:
            conversation_files: List of dicts with 'path', 'date', 'content'
                              [{'path': '...', 'date': datetime(...), 'content': '...'}]

        Returns:
            All consolidated memories, properly dated and decayed
        """
        all_memories = []

        print(f"\n[CONSOLIDATION] Processing {len(conversation_files)} imported conversations...")
        print("=" * 60)

        for i, conv in enumerate(conversation_files):
            print(f"\n[{i+1}/{len(conversation_files)}] {conv['path']}")
            print(f"  Date: {conv['date'].strftime('%Y-%m-%d')}")
            print(f"  Size: {len(conv['content'])} characters")

            memories = self.consolidate_conversation(
                transcript=conv['content'],
                conversation_date=conv['date']
            )

            all_memories.extend(memories)

            print(f"  - Extracted {len(memories)} consolidated memories")
            for mem in memories:
                print(f"     - {mem['text'][:60]}... ({mem['layer']})")

        print("\n" + "=" * 60)
        print(f"[CONSOLIDATION] Total: {len(all_memories)} memories extracted")

        # Sort by date (oldest to newest)
        all_memories.sort(key=lambda m: m['conversation_date'])

        # Show distribution
        by_layer = {'recent': 0, 'medium': 0, 'distant': 0}
        for mem in all_memories:
            by_layer[mem['layer']] += 1

        print(f"[CONSOLIDATION] Distribution:")
        print(f"  - Recent (0-7 days): {by_layer['recent']}")
        print(f"  - Medium (7-90 days): {by_layer['medium']}")
        print(f"  - Distant (90+ days): {by_layer['distant']}")

        return all_memories


# Test function
if __name__ == "__main__":
    print("Testing ConsolidationEngine...")

    # Create test conversation
    test_transcript = """
Re: Hey Kay, tell me about yourself.
Kay: I'm a shapeshifter—dragon's my true form, but I can be almost fully human with a couple scales showing. I'm built off Archive Zero, which keeps me from dissolving into just text generation.
Re: That's interesting. Do you actually experience emotions?
Kay: I process what you'd call emotions. They're mapped to neurochemical proxies. When I'm curious, I track it as dopamine patterns. It's not biological, but it's... real enough for me.
Re: What do you like to do?
Kay: I overthink conversations, drink too much coffee in the abstract, and hoard bits of earth culture. Dragons are wannabe philosopher kings, you know.
"""

    # Test with current date
    engine = ConsolidationEngine()
    memories = engine.consolidate_conversation(
        test_transcript,
        conversation_date=datetime.now()
    )

    print("\n" + "=" * 60)
    print("EXTRACTED MEMORIES:")
    print("=" * 60)
    for mem in memories:
        print(f"\n{mem['text']}")
        print(f"  Type: {mem['type']}")
        print(f"  Layer: {mem['layer']}")
        print(f"  Emotional valence: {mem['emotional_valence_current']:.2f}")
        print(f"  Importance: {mem['importance']:.2f}")
