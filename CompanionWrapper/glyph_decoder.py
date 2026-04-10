"""
Glyph Decoder for the entity Zero
Translates compressed glyph output from Filter LLM into natural language context
Expands symbolic representations into structured data for the entity's response generation
"""

import re
from typing import Dict, List, Any, Tuple
from glyph_vocabulary import (
    GLYPH_TO_EMOTION,
    GLYPH_TO_PHASE,
    GLYPH_TO_VECTOR,
    GLYPH_TO_STRUCTURE,
    GLYPH_TO_CONTEXT,
    decode_emotion_glyph,
    decode_phase_glyph,
    EMOTIONAL_GLYPHS,
    PHASE_GLYPHS,
    STRUCTURE_GLYPHS,
    KAY_WORLD_GLYPHS
)


class GlyphDecoder:
    """
    Decodes glyph-compressed filter output into natural language context.
    No LLM needed - pure parsing and lookup.
    """
    
    def __init__(self):
        """Initialize decoder with reverse glyph mappings."""
        self.emotion_map = GLYPH_TO_EMOTION
        self.phase_map = GLYPH_TO_PHASE
        self.structure_map = GLYPH_TO_STRUCTURE
        self.context_map = GLYPH_TO_CONTEXT
    
    def decode(self, glyph_output: str, agent_state: Dict) -> Dict[str, Any]:
        """
        Main decoding function.

        Args:
            glyph_output: Compressed glyph string from Filter
            agent_state: Full agent state (for memory lookup)

        Returns:
            Decoded context dict
        """
        lines = glyph_output.strip().split('\n')

        # NEW: Extract RAG chunks from agent state (if available)
        rag_chunks = []
        memory_engine = agent_state.get("memory")
        if memory_engine and hasattr(memory_engine, "last_rag_chunks"):
            rag_chunks = memory_engine.last_rag_chunks
            print(f"[DECODER] Retrieved {len(rag_chunks)} RAG chunks from memory engine")

        decoded = {
            "selected_memories": [],
            "recent_turns_needed": 0,  # NEW: How many recent conversation turns to include
            "emotional_state": "",
            "contradictions": [],
            "identity_state": "",
            "meta_notes": [],
            "rag_chunks": rag_chunks,  # NEW: Include RAG chunks
            "raw_glyphs": glyph_output
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse memory references (has MEM[ in it)
            if "MEM[" in line:
                decoded["selected_memories"] = self._parse_memory_refs(line, agent_state)

            # NEW: Parse RECENT_TURNS directive
            elif "RECENT_TURNS:" in line:
                try:
                    turns_value = int(line.split(':')[1].strip())
                    decoded["recent_turns_needed"] = turns_value
                    print(f"[DECODER] Filter LLM requested {turns_value} recent conversation turns")
                except (IndexError, ValueError) as e:
                    print(f"[DECODER] Failed to parse RECENT_TURNS from '{line}': {e}")
                    decoded["recent_turns_needed"] = 0

            # Parse emotional state (has intensity pattern AND emotion glyphs)
            elif re.search(r'\([0-9.]+\)', line) and any(glyph in line for glyph in EMOTIONAL_GLYPHS.values()):
                decoded["emotional_state"] = self._parse_emotions(line)

            # Parse contradictions (has CONFLICT marker)
            elif "⚠️CONFLICT" in line or "CONFLICT" in line:
                decoded["contradictions"].append(self._parse_contradiction(line))

            # Parse recent turns reference (has TURNS[ in it)
            elif "TURNS[" in line:
                decoded["meta_notes"].append(self._parse_turns_ref(line))

            # Parse identity/structure state (check for structure glyphs, NOT emotion glyphs)
            elif any(glyph in line for glyph in STRUCTURE_GLYPHS.values()):
                # Make sure it's not an emotion line that also has structure glyphs
                if not re.search(r'\([0-9.]+\)', line):
                    decoded["identity_state"] = self._parse_structure(line)
        
        return decoded
    
    def _parse_memory_refs(self, line: str, agent_state: Dict) -> List[Dict]:
        """
        Extract memory IDs and retrieve actual memories.

        Example: "⚡MEM[1,2,5]!!" → retrieves memories at indices 1, 2, 5
        """
        # Extract memory IDs
        match = re.search(r'MEM\[([0-9,]+)\]', line)
        if not match:
            return []

        ids_str = match.group(1)
        memory_ids = [int(id.strip()) for id in ids_str.split(',')]

        # CRITICAL FIX: Retrieve actual memories from MemoryEngine instance
        # Memories are stored in agent_state["memory"].memories, not agent_state["memories"]
        memory_engine = agent_state.get("memory")
        if memory_engine and hasattr(memory_engine, "memories"):
            all_memories = memory_engine.memories
        else:
            # Fallback for testing or old format
            all_memories = agent_state.get("memories", [])

        selected = []

        for idx in memory_ids:
            if 0 <= idx < len(all_memories):
                selected.append(all_memories[idx])
                print(f"[DECODER] Retrieved memory [{idx}]: {all_memories[idx].get('fact', all_memories[idx].get('user_input', ''))[:60]}...")

        print(f"[DECODER] Total memories available: {len(all_memories)}, Selected: {len(selected)}")

        # NUCLEAR OPTION: If filter LLM selected too few, force-add more
        MINIMUM_MEMORIES = 20
        if len(selected) < MINIMUM_MEMORIES and len(all_memories) >= MINIMUM_MEMORIES:
            print(f"\n[DECODER NUCLEAR OPTION] Filter only selected {len(selected)} memories, forcing minimum {MINIMUM_MEMORIES}")
            # Add recent high-importance memories not already selected
            selected_indices = set(memory_ids)
            added_count = 0

            # Strategy: Add recent memories with high importance
            for idx in range(len(all_memories) - 1, -1, -1):  # Start from most recent
                if idx not in selected_indices and len(selected) < MINIMUM_MEMORIES:
                    mem = all_memories[idx]
                    importance = mem.get('importance_score', 0.3)
                    if importance > 0.4:  # Only add if somewhat important
                        selected.append(mem)
                        selected_indices.add(idx)
                        added_count += 1
                        print(f"[DECODER FORCE-ADD] Adding memory [{idx}]: {mem.get('fact', mem.get('user_input', ''))[:60]}...")

            if added_count > 0:
                print(f"[DECODER NUCLEAR OPTION] Force-added {added_count} memories to reach minimum {MINIMUM_MEMORIES}")
                print(f"[DECODER] New total: {len(selected)} memories")

        return selected
    
    def _parse_emotions(self, line: str) -> str:
        """
        Parse emotional state glyphs into human-readable text.
        
        Example: "🔮(0.8)🔁 💗(0.3)⏸️" → "Curiosity (0.8, active), Affection (0.3, suppressed)"
        """
        emotions = []
        
        # Split by spaces to get individual emotion chunks
        # Example: "🔮(0.8)🔁 💗(0.3)⏸️" → ["🔮(0.8)🔁", "💗(0.3)⏸️"]
        chunks = line.split()
        
        for chunk in chunks:
            # Find which emotion glyph this chunk starts with
            emotion_name = None
            emotion_glyph_found = None
            
            for glyph, name in self.emotion_map.items():
                if chunk.startswith(glyph):
                    emotion_name = name
                    emotion_glyph_found = glyph
                    break
            
            if not emotion_name:
                continue
            
            # Extract intensity: (0.8)
            intensity_match = re.search(r'\(([0-9.]+)\)', chunk)
            if not intensity_match:
                continue
            
            intensity = float(intensity_match.group(1))
            
            # Extract phase: 🔁, ⏸️, etc.
            phase = "active"
            for phase_glyph, phase_name in self.phase_map.items():
                if phase_glyph in chunk:
                    phase = phase_name
                    break
            
            emotions.append(f"{emotion_name.title()} ({intensity:.1f}, {phase})")
        
        return ", ".join(emotions) if emotions else "No emotions detected"
    
    def _parse_contradiction(self, line: str) -> str:
        """
        Parse contradiction flags into resolution instructions.

        NOTE: Only ACTIVE (unresolved) contradictions are flagged now. Contradictions
        are automatically marked as resolved after 3 consecutive consistent turns.

        Example: "⚠️CONFLICT:☕(3x)🍵(2x)" → instruction to resolve coffee/tea preference
        """
        # Extract contradiction details
        if "☕" in line and "🍵" in line:
            # Coffee vs tea
            coffee_match = re.search(r'☕\((\d+)x\)', line)
            tea_match = re.search(r'🍵\((\d+)x\)', line)

            coffee_count = int(coffee_match.group(1)) if coffee_match else 0
            tea_count = int(tea_match.group(1)) if tea_match else 0

            return (f"ACTIVE CONTRADICTION: You've mentioned coffee ({coffee_count}x) and tea ({tea_count}x). "
                   f"State your preference consistently for 3 turns to resolve. "
                   f"Example: 'I'm primarily a coffee person, but enjoy tea occasionally.'")

        # Generic contradiction
        return ("ACTIVE CONTRADICTION: Conflicting statements detected. "
               "State your position consistently for 3 turns to resolve.")
    
    def _parse_structure(self, line: str) -> str:
        """
        Parse identity/structure glyphs into status description.
        
        Example: "◼️🐉" → "Compressed identity (under pressure), Kay as dragon"
        """
        descriptions = []
        
        # Check for structure glyphs
        if "◼️" in line:
            descriptions.append("Identity under compression (contradicting yourself)")
        elif "◻️" in line:
            descriptions.append("Stable identity (coherent)")
        
        if "✖️" in line:
            descriptions.append("Loop fracture detected (emotional pattern broken)")
        elif "⭕" in line:
            descriptions.append("Complete loop (pattern resolved)")
        
        if "🐉" in line:
            descriptions.append("Kay as dragon")
        
        return " | ".join(descriptions) if descriptions else "Identity state unclear"
    
    def _parse_turns_ref(self, line: str) -> str:
        """
        Parse recent turns reference.
        
        Example: "TURNS[-3,-2,-1]" → "Use last 3 conversation turns"
        """
        match = re.search(r'TURNS\[([^\]]+)\]', line)
        if match:
            turns_spec = match.group(1)
            # Count how many turns referenced
            turn_count = len([t for t in turns_spec.split(',') if t.strip()])
            return f"Use last {turn_count} conversation turns for context"
        return "Use recent conversation context"
    
    def build_context_for_kay(self, decoded: Dict, user_input: str) -> str:
        """
        Build natural language context block for the entity's prompt.

        This is what the entity actually sees - not the glyphs, but their expanded meaning.
        """
        context_blocks = []

        # NEW: RAG document context (if any)
        if decoded.get("rag_chunks"):
            rag_lines = []
            for i, chunk in enumerate(decoded["rag_chunks"][:5], 1):  # Max 5 chunks
                source = chunk.get("source_file", "unknown")
                text = chunk.get("text", "")

                # FIX #6: Truncate at word boundaries instead of mid-word
                # Increased limit from 400 to 2000 chars (~400 words) for better context
                max_chars = 2000
                if len(text) > max_chars:
                    # Find last space before limit to avoid cutting mid-word
                    truncated = text[:max_chars]
                    last_space = truncated.rfind(' ')
                    if last_space > max_chars * 0.8:  # Only cut at space if it's reasonably close
                        text = truncated[:last_space] + "..."
                    else:
                        # No good space found, just cut at limit with ellipsis
                        text = truncated + "..."
                else:
                    # Text is short enough, no truncation needed
                    pass

                rag_lines.append(f"  [{i}] From {source}:\n    {text}")

            context_blocks.append(
                "DOCUMENT CONTEXT (from uploaded files):\n" + "\n".join(rag_lines)
            )
            print(f"[DECODER] Including {len(decoded['rag_chunks'])} RAG chunks in the entity's context")

        # Memory block
        # FIX: Use .get() to avoid KeyError if key doesn't exist (bypass mode compatibility)
        selected_memories = decoded.get("selected_memories", [])
        if selected_memories:
            memory_lines = []
            for i, mem in enumerate(selected_memories):
                perspective = mem.get("perspective", "unknown")
                # Use discrete fact if available, fallback to user_input
                fact_text = mem.get("fact", "") or mem.get("user_input", "")
                memory_lines.append(f"  [{i}] ({perspective}) {fact_text}")

            context_blocks.append(
                "RELEVANT MEMORIES:\n" + "\n".join(memory_lines)
            )

        # Emotional state block
        # FIX: Use .get() to avoid KeyError
        emotional_state = decoded.get("emotional_state")
        if emotional_state:
            context_blocks.append(
                f"CURRENT EMOTIONAL STATE:\n  {emotional_state}"
            )

        # Contradiction block (CRITICAL - only ACTIVE contradictions shown)
        # FIX: Use .get() to avoid KeyError
        contradictions = decoded.get("contradictions", [])
        if contradictions:
            contradiction_text = "\n  ".join(contradictions)
            context_blocks.append(
                f"⚠️ ACTIVE CONTRADICTION (will auto-resolve after 3 consistent turns):\n  {contradiction_text}"
            )

        # Identity state block
        # FIX: Use .get() to avoid KeyError
        identity_state = decoded.get("identity_state")
        if identity_state:
            context_blocks.append(
                f"IDENTITY STATUS:\n  {identity_state}"
            )

        # Meta notes
        # FIX: Use .get() to avoid KeyError
        meta_notes = decoded.get("meta_notes", [])
        if meta_notes:
            context_blocks.append(
                "CONTEXT NOTES:\n  " + "\n  ".join(meta_notes)
            )
        
        # User input
        context_blocks.append(
            f"USER SAYS: \"{user_input}\""
        )
        
        # Instructions
        instructions = [
            "Respond ONLY to the user's CURRENT message (shown in 'USER SAYS' above).",
            "Do NOT re-answer previous questions from earlier in the conversation.",
            "Do NOT repeat information you already provided.",
            "If ACTIVE contradiction flagged, state your preference clearly and consistently.",
            "Contradictions auto-resolve after 3 consecutive consistent responses - no need to over-explain."
        ]
        context_blocks.append(
            "INSTRUCTIONS:\n  " + "\n  ".join(instructions)
        )
        
        return "\n\n".join(context_blocks)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing GlyphDecoder...")
    
    # Mock glyph output from Filter
    test_glyph_output = """🔮MEM[1,2]!!
🔮(0.8)🔁 💗(0.3)⏸️
⚠️CONFLICT:☕(3x)🍵(2x)
◼️🐉
TURNS[-3,-2,-1]"""
    
    # Mock agent state
    test_state = {
        "memories": [
            {
                "perspective": "user",
                "user_input": "My eyes are green",
            },
            {
                "perspective": "entity",
                "user_input": "I prefer coffee to get energized",
            },
            {
                "perspective": "entity",
                "user_input": "I'm more of a tea person actually",
            },
        ],
    }
    
    decoder = GlyphDecoder()
    
        # Right after decoder = GlyphDecoder(), add:
    print("\n--- DEBUGGING ---")
    print(f"Emotion map has {len(decoder.emotion_map)} entries")
    print(f"Looking for 🔮 in map: {'🔮' in decoder.emotion_map}")
    if '🔮' in decoder.emotion_map:
        print(f"🔮 maps to: {decoder.emotion_map['🔮']}")

    # Test the parsing directly
    test_line = "🔮(0.8)🔁 💗(0.3)⏸️"
    print(f"\nTest line: {test_line}")
    print(f"Chunks after split: {test_line.split()}")
    for chunk in test_line.split():
        print(f"  Chunk: '{chunk}'")
        for glyph in decoder.emotion_map.keys():
            if chunk.startswith(glyph):
                print(f"    Starts with {glyph} → {decoder.emotion_map[glyph]}")
    print("--- END DEBUG ---\n")
        
    
    print("\n--- GLYPH INPUT ---")
    print(test_glyph_output)
    print("--- END INPUT ---\n")
    
    # Decode glyphs
    decoded = decoder.decode(test_glyph_output, test_state)
    
    print("--- DECODED STRUCTURE ---")
    print(f"Selected memories: {len(decoded['selected_memories'])}")
    for i, mem in enumerate(decoded['selected_memories']):
        print(f"  [{i}] {mem.get('perspective')}: {mem.get('user_input')}")
    
    print(f"\nEmotional state: {decoded['emotional_state']}")
    print(f"Identity state: {decoded['identity_state']}")
    
    if decoded['contradictions']:
        print(f"\nContradictions detected:")
        for contra in decoded['contradictions']:
            print(f"  - {contra}")
    
    print("--- END DECODED ---\n")
    
    # Build final context for the entity
    user_input = "What's your favorite drink?"
    final_context = decoder.build_context_for_kay(decoded, user_input)
    
    print("--- CONTEXT FOR KAY ---")
    print(final_context)
    print("--- END CONTEXT ---\n")
    
    print("✅ Decoder test complete!")