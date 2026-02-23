"""
Context Filter for Reed
Uses Claude Haiku to compress full agent state into glyph-based selections
Outputs compressed symbolic representations for efficient LLM-to-LLM communication
"""

import json
import re
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
from glyph_vocabulary import (
    format_emotion_state,
    format_memory_reference,
    format_contradiction,
    get_filter_glyph_reference,
    REED_WORLD_GLYPHS,
    STRUCTURE_GLYPHS
)
# DEPRECATED: Old semantic knowledge system (facts extracted from documents)
# from engines.semantic_knowledge import get_semantic_knowledge
# NOW: Documents are retrieved via llm_retrieval.py (simpler, more reliable)


load_dotenv()


# Import your existing LLM integration
# Adjust path as needed for your project structure
try:
    from integrations.llm_integration import query_llm_json
except ImportError:
    # Fallback for testing
    def query_llm_json(prompt, temperature=0.3, model="claude-3-haiku-20240307", system_prompt=None):
        return '{"test": "fallback"}'


class GlyphFilter:
    """
    Filters Reed's complete agent state and outputs compressed glyph representations.
    Uses cheap/fast Haiku model for efficiency.
    """
     
    def __init__(self, filter_model=None):
        """
        Initialize filter.
        Defaults to Haiku for cheap/fast filtering.
        """
        if filter_model is None:
            # Use cheapest available Haiku model
            filter_model = os.getenv("FILTER_MODEL", "claude-haiku-4-5-20251001")

        self.filter_model = filter_model
        self.glyph_reference = get_filter_glyph_reference()

        # DEPRECATED: Old semantic knowledge system
        # self.semantic_knowledge = get_semantic_knowledge()
        # print("[CONTEXT FILTER] Semantic knowledge integration ENABLED")
        # NOW: Documents retrieved via llm_retrieval.py in main.py

        # NEW: Track entities across queries for context awareness
        self.previous_query_entities = []
        
    def filter_context(self, agent_state: Dict, user_input: str) -> str:
        """
        Main filtering function with SEMANTIC KNOWLEDGE + IDENTITY FACT AUTO-INCLUSION.

        Multi-tier retrieval:
        1. Semantic knowledge (factual queries) - ADDED FIRST
        2. Identity facts (score=999.0, is_identity=True) - BYPASS LLM selection
        3. Episodic memories (existing memories from agent_state)

        Args:
            agent_state: Full state with memories, emotions, recent turns, etc.
            user_input: Current user message

        Returns:
            Glyph-compressed string (e.g., "⚡MEM[47,53]!!! 🔮(0.8)🔁 ⚠️CONFLICT:☕(3x)🍵(2x)")
        """
        # === STEP 0: SEMANTIC KNOWLEDGE (DEPRECATED) ===
        # DEPRECATED: semantic_knowledge removed, documents via llm_retrieval.py
        semantic_facts = []

        # Get existing episodic memories from agent state
        episodic_memories = agent_state.get("memories", [])

        # Combine semantic facts + episodic memories
        # Semantic facts go FIRST so they get priority in selection
        combined_memories = semantic_facts + episodic_memories

        print(f"[COMBINED CONTEXT] Total: {len(combined_memories)} memories")
        print(f"[COMBINED CONTEXT]   Semantic facts: {len(semantic_facts)}")
        print(f"[COMBINED CONTEXT]   Episodic memories: {len(episodic_memories)}")

        # Store combined memories for debug tracking
        memories_for_tracking = combined_memories

        # === STEP 1: EXTRACT IDENTITY FACTS (AUTO-INCLUDE) ===
        # Identity facts scored 999.0 in retrieval - they should NEVER be optional
        identity_indices = []
        identity_facts = []

        for idx, mem in enumerate(memories_for_tracking):
            # Check for identity markers
            is_identity = (
                mem.get("is_identity", False) or
                mem.get("topic") in ["identity", "appearance", "name", "core_preferences", "relationships"] or
                "identity" in mem.get("type", "").lower()
            )

            if is_identity:
                identity_indices.append(idx)
                identity_facts.append(mem)

        print(f"[IDENTITY AUTO-INCLUDE] Found {len(identity_indices)} identity facts in pre-filtered memories")
        if identity_indices:
            print(f"[IDENTITY AUTO-INCLUDE] Indices: {identity_indices[:10]}{'...' if len(identity_indices) > 10 else ''}")

        # === STEP 2: PRIORITY-BASED SELECTION (NO LLM CALL) ===
        # FIX: Remove expensive glyph filter LLM call
        # Replace with simple priority sorting by score

        # Detect query type for target calculation
        LIST_PATTERNS = [
            "what are", "tell me about", "list", "all the", "all of",
            "some things", "what have", "everything", "anything",
            "what do you know", "what did", "show me"
        ]
        is_list_query = any(pattern in user_input.lower() for pattern in LIST_PATTERNS)

        # Calculate how many memories to select
        target_total = 60 if is_list_query else 40
        print(f"[PRIORITY FILTER] Target: {target_total} memories (identity already included in retrieval)")

        # Sort all memories by score (highest first)
        # Memories from retrieve_multi_factor() already have scores
        scored_memories = []
        for idx, mem in enumerate(memories_for_tracking):
            score = mem.get("score", 0.0)
            # Boost identity facts
            if mem.get("is_identity", False) or mem.get("topic") in ["identity", "appearance", "name"]:
                score += 1000.0  # Ensure identity always at top
            scored_memories.append((score, idx, mem))

        # Sort by score (descending)
        scored_memories.sort(key=lambda x: x[0], reverse=True)

        # Take top N
        final_indices = []
        selected_memories = []
        for score, idx, mem in scored_memories[:target_total]:
            final_indices.append(idx)
            selected_memories.append(mem)

        print(f"[PRIORITY FILTER] Selected {len(final_indices)} memories by score (no LLM call)")
        print(f"[PRIORITY FILTER] Top 5 scores: {[scored_memories[i][0] for i in range(min(5, len(scored_memories)))]}")

        # === STEP 3: BUILD GLYPH OUTPUT (WITHOUT LLM) ===
        # Create minimal glyph output with just memory indices
        glyph_output = f"MEM[{','.join(map(str, final_indices))}]!!!"

        # === DEBUG TRACKING: Stage 3 - After PRIORITY FILTER ===
        from engines.memory_debug_tracker import get_tracker
        tracker = get_tracker()
        tracker.track_stage_3(selected_memories, memories_for_tracking)
        tracker.print_summary()  # Print final summary after Stage 3

        return glyph_output
    
    def _build_system_prompt(self) -> str:
        """System prompt for Filter LLM with tier awareness."""
        return f"""You are a context filter for Reed, an emotionally-aware AI with persistent memory.

Your job: Analyze Reed's full state and compress it into symbolic glyphs for efficient communication.

MEMORY STORAGE MODEL:
Reed's memories are stored in two types:
- EPISODIC (full_turn): Complete conversation turns with ALL entities mentioned
- SEMANTIC (extracted_fact): Individual structured facts

When selecting memories:
- If user asks for lists/names (e.g., "what are my cats' names?"), PRIORITIZE full_turn memories marked with is_list=true
- These contain the COMPLETE list of entities, not just one
- Extracted facts are useful for specific questions but miss the full list

GLYPH VOCABULARY:
{self.glyph_reference}

OUTPUT FORMAT (GLYPHS ONLY):
Line 1: Memory references with priority - ALWAYS include this line
Line 2: RECENT_TURNS directive - how many recent conversation turns needed
Line 3: Emotional state(s) with intensity and phase
Line 4: Contradictions if detected
Line 5: Identity/structure state

RECENT_TURNS DECISION (Line 2):
Output: RECENT_TURNS: N (where N = 0-10)

⚠️ CRITICAL: When in doubt, ERR ON THE SIDE OF INCLUDING recent turns rather than excluding them.

EXPLICIT TRIGGER PATTERNS (ALWAYS match these first):
- "What did I say..." → ALWAYS RECENT_TURNS: 5
- "What did I tell you..." → ALWAYS RECENT_TURNS: 5
- "What did I just..." → ALWAYS RECENT_TURNS: 3
- "What did we..." → ALWAYS RECENT_TURNS: 5
- "Tell me more" → ALWAYS RECENT_TURNS: 3
- "What else?" → ALWAYS RECENT_TURNS: 3
- "And also..." → ALWAYS RECENT_TURNS: 2
- "Speaking of..." → ALWAYS RECENT_TURNS: 3
- Questions asking "my X" where X might have been mentioned recently → RECENT_TURNS: 5
  Example: "What did I say my favorite color is?" → RECENT_TURNS: 5

GUIDELINES FOR N:
- 0: Pure factual query, no conversational context needed
  Example: "What are the pigeon names?" (clear subject, no pronouns)

- 1-2: Minor connection to recent topic
  Example: "Tell me more about that" (need 1-2 turns to know what "that" is)

- 3-5: Strong conversational continuity needed
  Example: "Can you try it?" (pronouns require context)
  Example: "What did we just discuss?" (temporal references)
  Example: Questions with pronouns lacking clear referent

- 5-10: Complex multi-turn reasoning required OR explicit recent reference
  Example: "Compare what you said earlier to this new idea"
  Example: "What did I say..." (explicitly asking about recent conversation)

SIGNALS FOR HIGH RECENT_TURNS (5-10):
- Explicit reference to recent conversation: "I said", "I told you", "we discussed", "you mentioned"
- Pronouns without clear antecedent: it, that, this, they, those, she, he
- Temporal words: just, recently, earlier, before, last, previous
- Continuation phrases: also, furthermore, speaking of which, and
- Follow-up questions: How? Why? What about...?
- Implicit commands: "Try it", "Show me", "Fix that"
- Questions about "my X" when X could be contextual

SIGNALS FOR LOW RECENT_TURNS (0-2):
- Factual questions with clear subject and no pronouns
- Questions about distant past events (not "just" or "recently")
- New topics clearly unrelated to recent conversation
- General knowledge queries with no contextual dependencies

EXAMPLE OUTPUT (FACTUAL QUERY - No recent context needed):
Query: "What are the pigeon names?"
⚡MEM[2,5,7,12,15,18,23,25,28,31,34,37,40,42,45,48,51,54,56,59,61,64,67,70,73]!!!
RECENT_TURNS: 0
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉

EXAMPLE OUTPUT (PRONOUN/CONTEXTUAL QUERY):
Query: "Can you describe it?"
⚡MEM[1,2,3,5,7,9,12,14,15,17,18,20,23,25,27,28,30,31,33,34,36,37]!!!
RECENT_TURNS: 5
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉

EXAMPLE OUTPUT (EXPLICIT RECENT REFERENCE):
Query: "What did I say my favorite color is?"
⚡MEM[1,2,3,5,7,9,12,14,15,17,18,20,23,25,27,28,30,31,33,34,36,37]!!!
RECENT_TURNS: 5
🔮(0.8)🔁 💗(0.3)🔃
◻️🐉

NOTE: The examples above show 25 indices (standard) and 60 indices (comprehensive). MATCH THIS QUANTITY.

CRITICAL RULES FOR MEMORY SELECTION:
- Line 1 is MANDATORY: You MUST output MEM[...] with memory indices
- ALWAYS INCLUDE **BOTH** Reed's AND User's CORE IDENTITY memories (marked with ⚠️) in EVERY response
- Core identity = appearance, relationships, names, key preferences for BOTH Kay and the User
- Use the EXACT indices shown in the MEMORIES section below (e.g., [2], [7], [15])
- **AGGRESSIVE SELECTION REQUIRED** - Selection count varies by query type:
  * LIST/COMPREHENSIVE queries ("tell me everything", "what do you know"): SELECT 50-80 memory indices MINIMUM
  * Detailed queries ("tell me about", "explain"): SELECT 30-50 memory indices MINIMUM
  * Standard queries: SELECT 20-30 memory indices MINIMUM
  * NEVER select fewer than 20 memories unless fewer than 20 exist
  * Err on the side of INCLUSION not exclusion - cast a WIDE net
  * Better to include too many than too few - Kay needs rich context
- Format: MEM[2,7,15] or MEM[2,7,15]!! or MEM[2,7,15]!!!
- Priority markers: !!! = critical (core identity), !! = important, ! = relevant
- NEVER omit user facts - they are EQUALLY important as Reed's facts
- If user asks about themselves, their core identity memories are MANDATORY
- **If user asks for a list, include the full_turn memory with is_list=true, not just individual facts**

OTHER RULES:
- Output ONLY glyphs, no natural language explanations
- Use intensity values as decimals: (0.8) not (80%)
- Detect contradictions in Reed's self-statements
- Keep output under 500 tokens (increased for comprehensive memory selection)
- If no contradictions, omit that line
- Always include memory references and emotional state
- PRIORITIZE QUANTITY - select AS MANY relevant memories as possible

You are selecting context, not responding to the user. Output compressed glyphs only."""

    def _build_filter_prompt(self, agent_state: Dict, user_input: str, identity_count: int = 0, remaining_to_select: int = 30) -> str:
        """
        Build the filtering prompt with available data.
        GLYPH PRE-FILTERING: Only sends top candidates to LLM, not entire memory bank.

        Args:
            agent_state: Full agent state
            user_input: User's query
            identity_count: Number of identity facts already auto-selected (NEW)
            remaining_to_select: How many MORE memories LLM needs to select (NEW)
        """
        # Extract key data from agent_state
        # CRITICAL FIX: Memories are stored in state.memory.memories (MemoryEngine instance)
        memory_engine = agent_state.get("memory")

        # === PERFORMANCE FIX: Pre-filter memories BEFORE sending to LLM ===
        # DYNAMIC CAP based on query type

        # Detect LIST queries (user asking for multiple things/comprehensive recall)
        LIST_PATTERNS = [
            "what are", "tell me about", "list", "all the", "all of",
            "some things", "what have", "everything", "anything",
            "what do you know", "what did", "show me"
        ]

        is_list_query = any(pattern in user_input.lower() for pattern in LIST_PATTERNS)

        if is_list_query:
            # LIST queries need MORE context to provide comprehensive answers
            MAX_CANDIDATES = 300  # 3x normal limit for detailed recall
            print(f"[FILTER] LIST query detected - expanding retrieval to {MAX_CANDIDATES} memories")
        else:
            # Normal queries - standard limit (increased from 100)
            MAX_CANDIDATES = 150  # Was too restrictive at 100

        # === FIX: Use memory engine's recency-aware retrieval instead of bypassing it ===
        # BEFORE: Called get_all_identity_facts() → 702 identity facts, no recency boosting
        # AFTER: Call retrieve_multi_factor() → ~310 diverse memories WITH recency boosting

        # Get emotional cocktail for biased retrieval
        emotional_cocktail = agent_state.get("emotional_cocktail", {})

        # Check if lazy loading mode is active
        use_lazy = hasattr(memory_engine, 'lazy_mode') and memory_engine.lazy_mode

        if use_lazy:
            # Use indexes to get candidate memories without loading all content
            memories = self._get_lazy_memory_candidates(memory_engine, user_input, max_candidates=MAX_CANDIDATES)
            identity_facts = []  # Lazy mode doesn't separate identity facts
        elif memory_engine and hasattr(memory_engine, 'retrieve_multi_factor'):
            # USE MEMORY ENGINE'S RECENCY-AWARE RETRIEVAL
            # This already includes identity facts (top 50) + working + imports + episodic/semantic
            # With recency exemption and boosting built in
            print(f"[FILTER] Using memory engine's recency-aware retrieval (MAX_CANDIDATES={MAX_CANDIDATES})")
            memories = memory_engine.retrieve_multi_factor(
                bias_cocktail=emotional_cocktail,
                user_input=user_input,
                num_memories=MAX_CANDIDATES
            )
            # Identity facts are already in the memories list with score >= 999.0
            identity_facts = []  # Don't grab separately, they're already in memories
            print(f"[DEBUG] Retrieved {len(memories)} memories with recency boosting")
        elif memory_engine and hasattr(memory_engine, "memories"):
            # Fallback: Use old pre-filter method if retrieve_multi_factor not available
            all_memories = memory_engine.memories
            print(f"[DEBUG] Total memories before pre-filter: {len(all_memories)}")
            memories = self._prefilter_memories_by_relevance(all_memories, user_input, max_count=MAX_CANDIDATES)
            print(f"[DEBUG] Memories after pre-filter: {len(memories)}")
            identity_facts = []  # Already in memories
        else:
            memories = agent_state.get("memories", [])  # Fallback for testing
            identity_facts = []

        recent_turns = agent_state.get("recent_context", [])
        
        # Summarize available data for filter
        identity_summary = self._format_identity_facts(identity_facts)
        memory_summary = self._summarize_memories(memories)
        emotion_summary = self._summarize_emotions(emotional_cocktail)
        turns_summary = f"Last {len(recent_turns)} conversation turns available"

        # Detect contradictions in memories
        contradictions = self._detect_contradictions(memories)

        # === IDENTITY AUTO-INCLUDE PROMPT UPDATE ===
        # Update prompt to tell LLM about identity facts already selected
        if identity_count > 0:
            identity_notice = f"""
⚠️ CRITICAL: {identity_count} IDENTITY FACTS ALREADY AUTO-SELECTED
These {identity_count} memories are MANDATORY and automatically included in Reed's context.
You do NOT need to select them - they are already in the final set.

YOUR JOB: Select {remaining_to_select} ADDITIONAL memory indices from the list below.
TOTAL FINAL COUNT: {identity_count} (identity, auto-included) + {remaining_to_select} (your selection) = {identity_count + remaining_to_select} total
"""
            memory_selection_guidance = f"Select {remaining_to_select} ADDITIONAL memory indices (identity facts already included)"
            selection_emphasis = f"CRITICAL: {identity_count} identity facts already selected. You must select {remaining_to_select} MORE contextual memories."
        else:
            identity_notice = ""
            # Original guidance (no identity facts found)
            if is_list_query:
                memory_selection_guidance = "Select 50-80 memory indices MINIMUM (LIST/COMPREHENSIVE query - needs EXTENSIVE detail)"
                selection_emphasis = "CRITICAL: User wants comprehensive recall. Select AT LEAST 50-80 memories. Cast a WIDE net."
            else:
                memory_selection_guidance = "Select 25-40 memory indices MINIMUM (standard query - needs substantial context)"
                selection_emphasis = "Select generously - AT LEAST 25-40 memories. More is better than less."

        prompt = f"""AVAILABLE DATA:

WARNING IDENTITY MEMORY (PERMANENT - ALWAYS INCLUDE ALL):
{identity_summary}
{identity_notice}

WORKING MEMORY ({len(memories)} total):
{memory_summary}

EMOTIONS:
{emotion_summary}

RECENT CONTEXT:
{turns_summary}

DETECTED PATTERNS:
{contradictions if contradictions else "No contradictions detected"}

USER INPUT: "{user_input}"

TASK: Select the most relevant context for Reed's response. Output in glyph format only.

{selection_emphasis}

OUTPUT FORMAT (REQUIRED):
Line 1: MEM[index,index,index] - {memory_selection_guidance} from the MEMORIES list above
Line 2: Emotional state glyphs with intensity
Line 3: Contradictions if detected (omit if none)
Line 4: Identity state glyphs

Focus on:
1. Which memories directly answer the user's current question? Use their EXACT indices (e.g., [2], [7], [15])
2. SELECT GENEROUSLY - Kay needs rich context to give comprehensive responses
3. Prioritize USER memories if user asks about themselves (their dog, preferences, life, etc.)
4. Prioritize KAY memories if user asks about Reed's identity, preferences, or state
5. What is Reed's current emotional state?
6. Are there contradictions Kay needs to resolve?
7. FOR LIST/COMPREHENSIVE QUERIES: Cast a WIDE net - include many memories
8. NEVER be conservative with selection - more memories = better responses

OUTPUT GLYPHS:"""

        return prompt
    
    def _summarize_memories(self, memories: List[Dict]) -> str:
        """
        Create compact summary of available memories for filter.
        Shows ABSOLUTE indices from full memory list.

        TWO-TYPE AWARE:
        - EPISODIC (full_turn): Complete conversation turns with context
        - SEMANTIC (extracted_fact): Discrete facts extracted from conversations
        - Highlights LIST statements (3+ entities)
        """
        if not memories:
            return "No memories stored"

        # Separate by memory type (two-type system: episodic full_turn + semantic extracted_fact)
        full_turn_mems = [(i, m) for i, m in enumerate(memories) if m.get("type") == "full_turn"]
        extracted_fact_mems = [(i, m) for i, m in enumerate(memories) if m.get("type") == "extracted_fact"]

        summary_lines = []

        # === EPISODIC: FULL TURN MEMORIES (PRIORITY) ===
        # These contain complete conversation context
        if full_turn_mems:
            recent_full_turns = full_turn_mems[-10:]  # Last 10 full turns

            full_turn_previews = []
            for idx, mem in recent_full_turns:
                user_input = mem.get("user_input", "")
                is_list = mem.get("is_list", False)
                entity_count = len(mem.get("entities", []))

                # Show preview
                preview = user_input[:80]
                list_marker = f" 📋 LIST({entity_count} entities)" if is_list else ""
                full_turn_previews.append(f"[{idx}]{list_marker} {preview}...")

            summary_lines.append(f"🎯 FULL CONVERSATION TURNS ({len(recent_full_turns)} recent):\n" + "\n".join(full_turn_previews))

        # === SEMANTIC: EXTRACTED FACTS (SECONDARY) ===
        # Group extracted facts by perspective
        user_facts = [(i, m) for i, m in extracted_fact_mems if m.get("perspective") == "user"]
        kay_facts = [(i, m) for i, m in extracted_fact_mems if m.get("perspective") == "kay"]
        shared_facts = [(i, m) for i, m in extracted_fact_mems if m.get("perspective") == "shared"]

        if user_facts:
            recent_user_facts = user_facts[-10:]  # Last 10 user facts
            user_previews = []
            for idx, mem in recent_user_facts:
                fact_preview = mem.get('fact', '')[:50]
                user_previews.append(f"[{idx}] {fact_preview}...")

            summary_lines.append(f"User facts ({len(user_facts)} total): " + " | ".join(user_previews))

        if kay_facts:
            # Separate core identity from other facts
            kay_core_identity = [(i, m) for i, m in kay_facts if m.get("topic") in ["appearance", "identity", "name", "core_preferences"]]
            kay_other = [(i, m) for i, m in kay_facts if m.get("topic") not in ["appearance", "identity", "name", "core_preferences"]]

            if kay_core_identity:
                core_previews = []
                for idx, mem in kay_core_identity[-5:]:  # Last 5 core identity facts
                    fact_preview = mem.get('fact', '')[:50]
                    topic = mem.get('topic', 'identity')
                    core_previews.append(f"[{idx}] ({topic}) {fact_preview}...")
                summary_lines.append(f"Kay's core identity (always relevant): " + " | ".join(core_previews))

            if kay_other:
                recent_kay_facts = kay_other[-10:]
                kay_previews = []
                for idx, mem in recent_kay_facts:
                    fact_preview = mem.get('fact', '')[:50]
                    kay_previews.append(f"[{idx}] {fact_preview}...")

                summary_lines.append(f"Kay facts ({len(kay_other)} total): " + " | ".join(kay_previews))

        if shared_facts:
            recent_shared_facts = shared_facts[-10:]
            shared_previews = []
            for idx, mem in recent_shared_facts:
                fact_preview = mem.get('fact', '')[:50]
                shared_previews.append(f"[{idx}] {fact_preview}...")

            summary_lines.append(f"Shared facts ({len(shared_facts)} total): " + " | ".join(shared_previews))

        return "\n".join(summary_lines) if summary_lines else "Memories present but empty"

    def _format_identity_facts(self, identity_facts: List[Dict]) -> str:
        """
        Format identity facts for filter prompt.
        These are PERMANENT facts that should ALWAYS be included.
        """
        if not identity_facts:
            return "No identity established yet"

        # Separate by perspective
        re_facts = [f for f in identity_facts if f.get("perspective") == "user"]
        kay_facts = [f for f in identity_facts if f.get("perspective") == "kay"]
        entity_facts = [f for f in identity_facts if f.get("perspective") not in ["user", "kay"]]

        lines = []

        if re_facts:
            previews = [f"  * {f.get('fact', '')[:70]}" for f in re_facts[-15:]]  # Show last 15
            lines.append(f"Re (the user) - {len(re_facts)} facts:\n" + "\n".join(previews))

        if kay_facts:
            previews = [f"  * {f.get('fact', '')[:70]}" for f in kay_facts[-15:]]  # Show last 15
            lines.append(f"Kay (the AI) - {len(kay_facts)} facts:\n" + "\n".join(previews))

        if entity_facts:
            # Group by entity
            entities_by_name = {}
            for fact in entity_facts:
                for entity_name in fact.get("entities", []):
                    if entity_name not in ["Re", "Kay"]:
                        if entity_name not in entities_by_name:
                            entities_by_name[entity_name] = []
                        entities_by_name[entity_name].append(fact)

            entity_previews = []
            for entity_name, facts in list(entities_by_name.items())[:10]:  # Show first 10 entities
                fact_preview = facts[0].get('fact', '')[:60] if facts else ""
                entity_previews.append(f"  * {entity_name}: {fact_preview}")

            if entity_previews:
                lines.append(f"Entities ({len(entities_by_name)} total):\n" + "\n".join(entity_previews))

        return "\n\n".join(lines) if lines else "Identity facts present but empty"

    def _summarize_emotions(self, emotional_cocktail: Dict) -> str:
        """
        Summarize current emotional state.
        """
        if not emotional_cocktail:
            return "No active emotions"
        
        # Sort by intensity
        sorted_emotions = sorted(
            emotional_cocktail.items(),
            key=lambda x: x[1].get("intensity", 0),
            reverse=True
        )
        
        summaries = []
        for emotion_name, data in sorted_emotions[:5]:  # Top 5 only
            intensity = data.get("intensity", 0)
            age = data.get("age", 0)
            summaries.append(f"{emotion_name}({intensity:.1f}, age:{age})")
        
        return " | ".join(summaries)
    
    def _detect_contradictions(self, memories: List[Dict]) -> str:
        """
        Detect contradictory statements in Reed's memories.

        NOTE: This method is DEPRECATED. Contradiction detection is now handled by
        entity_graph with resolution tracking. Only ACTIVE (unresolved) contradictions
        will be flagged.

        This method is kept for backwards compatibility but returns empty string
        to avoid duplicate contradiction warnings.
        """
        # Contradictions are now handled by entity_graph.get_all_contradictions()
        # which includes resolution tracking. No need for separate detection here.
        return ""
    
    def _prefilter_memories_by_relevance(self, all_memories: List[Dict], user_input: str, max_count: int = 100) -> List[Dict]:
        """
        PRE-FILTER memories using fast keyword/glyph matching BEFORE sending to expensive LLM.

        Performance-critical function - must be fast!
        Uses glyph summaries, keywords, recency, and importance for scoring.

        PROTECTION RULES:
        1. Identity facts (score >= 999.0, is_identity=True) - MANDATORY, bypass keyword scoring
        2. Recently imported facts (age < 3 turns) - Protected from initial cuts
        3. All other memories - Compete via keyword scoring

        Args:
            all_memories: Full memory list
            user_input: Current user message
            max_count: Maximum memories to return

        Returns:
            Top N most relevant memories (includes protected identity facts + imports + scored memories)
        """
        import time
        start_time = time.time()

        # === STEP 1: SEPARATE PROTECTED vs FILTERABLE MEMORIES ===
        identity_facts = []      # Score >= 999.0 or is_identity=True - BYPASS keyword scoring
        protected_imports = []   # Recently imported (age < 3 turns)
        filterable = []          # Everything else - compete via keywords

        for mem in all_memories:
            # CRITICAL: Check for identity facts FIRST (highest priority)
            is_identity = (
                mem.get("is_identity", False) or
                mem.get("topic") in ["identity", "appearance", "name", "core_preferences", "relationships"] or
                "identity" in mem.get("type", "").lower() or
                mem.get("score", 0) >= 999.0  # Anything scored 999.0 is identity
            )

            if is_identity:
                identity_facts.append(mem)
            elif mem.get("protected") or (mem.get("is_imported") and mem.get("age", 999) < 3):
                # Protect recently imported facts (but lower priority than identity)
                protected_imports.append(mem)
            else:
                filterable.append(mem)

        # Log protection status
        print(f"[PRE-FILTER PROTECT] Found {len(identity_facts)} identity facts (MANDATORY - bypass keyword scoring)")
        if protected_imports:
            print(f"[PRE-FILTER PROTECT] Found {len(protected_imports)} recently imported facts (age < 3 turns)")
        print(f"[PRE-FILTER PROTECT] Scoring {len(filterable)} filterable memories via keywords")

        # === STEP 2: KEYWORD SCORE ONLY FILTERABLE MEMORIES ===
        # Extract keywords from user input (normalize)
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        keywords = {w for w in user_input.lower().split() if w not in stopwords and len(w) > 2}

        scored_memories = []

        # FIX #3: Calculate current turn for recency boost
        # Get max turn_index to determine current turn
        current_turn = max((m.get("turn_index", 0) for m in all_memories), default=0)

        for idx, mem in enumerate(filterable):
            score = 0.0

            # NOTE: Identity facts are now in separate list - don't score them here

            # Recent working memory (last 20 items) get high priority
            if idx >= len(filterable) - 20:
                score += 50.0

            # FIX #3: Add turn-based recency boost (complements position-based boost above)
            # Recent memories from last 5 turns get extra priority
            turns_old = current_turn - mem.get("turn_index", 0)
            if turns_old <= 3:
                score += 40.0  # Very recent (last 3 turns)
            elif turns_old <= 5:
                score += 25.0  # Recent (last 5 turns)
            elif turns_old <= 10:
                score += 10.0  # Somewhat recent (last 10 turns)

            # High importance memories
            importance = mem.get("importance_score", 0.3)
            score += importance * 20.0

            # === NEW: Boost emotional narrative chunks (imported memories with rich context) ===
            if mem.get("is_emotional_narrative") or mem.get("type") == "emotional_narrative":
                score += 25.0  # Narrative chunks contain rich contextual information

            # Boost by emotional intensity
            if "emotional_signature" in mem:
                intensity = mem.get("emotional_signature", {}).get("intensity", 0)
                score += intensity * 10.0  # Emotionally intense memories more salient

            # Boost by identity centrality
            identity_type = mem.get("identity_type", "")
            if identity_type in ["core_identity", "formative"]:
                score += 30.0  # Core identity memories highly prioritized
            elif identity_type in ["relationship"]:
                score += 15.0  # Relationship memories moderately prioritized

            # Keyword matching (fast!)
            mem_text = (
                mem.get("fact", "") + " " +
                mem.get("user_input", "")
            ).lower()

            # Count keyword overlaps
            keyword_hits = sum(1 for kw in keywords if kw in mem_text)
            score += keyword_hits * 10.0

            # Entity matching (if entities extracted)
            entities = mem.get("entities", [])
            entity_text = " ".join(entities).lower()
            entity_hits = sum(1 for kw in keywords if kw in entity_text)
            score += entity_hits * 15.0  # Entity matches weighted higher

            # Recency bonus (access count)
            access_count = mem.get("access_count", 0)
            score += min(access_count, 5) * 2.0  # Cap at 5 accesses

            scored_memories.append((mem, score))

        # === STEP 3: CALCULATE REMAINING SLOTS AFTER PROTECTED MEMORIES ===
        # Identity facts are MANDATORY - they don't count against the cap
        # Protected imports DO count against the cap (lower priority)
        total_protected = len(identity_facts) + len(protected_imports)
        available_slots = max_count - total_protected

        if available_slots < 0:
            # Edge case: Protected memories exceed cap
            # Keep ALL protected memories anyway (especially identity facts)
            available_slots = 0
            print(f"[PRE-FILTER WARN] {total_protected} protected memories exceeds cap of {max_count} - keeping all protected")

        # === STEP 4: TAKE TOP N SCORED MEMORIES ===
        if available_slots > 0:
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            top_scored = [mem for mem, score in scored_memories[:available_slots]]
        else:
            top_scored = []

        # === STEP 5: MERGE (IDENTITY FIRST, THEN IMPORTS, THEN SCORED) ===
        # Order matters: identity facts should appear first for glyph filter
        result = identity_facts + protected_imports + top_scored

        elapsed = (time.time() - start_time) * 1000
        print(f"[PRE-FILTER PROTECT] Final: {len(identity_facts)} identity + {len(protected_imports)} imports + {len(top_scored)} scored = {len(result)} total")
        print(f"[PERF] glyph_prefilter: {elapsed:.1f}ms - {len(all_memories)} -> {len(result)} memories")

        # === DEBUG TRACKING: Stage 2 - After PRE-FILTER ===
        from engines.memory_debug_tracker import get_tracker
        tracker = get_tracker()
        tracker.track_stage_2(result, scored_memories)

        return result

    def _get_lazy_memory_candidates(self, memory_engine, user_input: str, max_candidates: int = 100) -> List[Dict]:
        """
        Get candidate memories for filtering using lazy loading.
        Loads only relevant memories instead of entire dataset.

        Args:
            memory_engine: LazyMemoryEngine instance
            user_input: Current user message
            max_candidates: Maximum memories to load

        Returns:
            List of candidate memories (full content loaded)
        """
        # Always include working memory (already loaded)
        candidates = list(memory_engine.working_memories)

        # Search indexes for relevant IDs
        keywords = user_input.lower().split()[:5]
        candidate_ids = set()

        # Search by keywords/entities
        for keyword in keywords:
            matches = memory_engine.memory_index.search_by_entities([keyword])
            candidate_ids.update(matches[:20])

        # Add high importance
        important = memory_engine.memory_index.search_by_importance(0.7)
        candidate_ids.update(important[:20])

        # Add recent
        recent = memory_engine.memory_index.get_recent_ids(30)
        candidate_ids.update(recent)

        # Load candidates (uses cache)
        loaded = memory_engine.memory_index.get_batch(list(candidate_ids)[:max_candidates])
        candidates.extend(loaded)

        print(f"[LAZY FILTER] Loaded {len(candidates)} candidates (vs {len(memory_engine.memory_index.indexes)} total)")

        return candidates

    def _extract_entities_from_query(self, query_text: str) -> List[str]:
        """
        Intelligent entity extraction from query with context awareness.

        Extracts relevant entities using multiple strategies:
        1. Capitalized proper nouns (filtered for false positives)
        2. Category keywords (nouns likely to be entities)
        3. Noun phrases (e.g., "one-legged pigeon")
        4. Contextual references ("them", "their" → use previous entities)
        5. Known entities from semantic knowledge base
        6. Stop word filtering

        Args:
            query_text: User's question/statement

        Returns:
            List of relevant entity strings (lowercase)
        """
        import re

        # Normalize query
        query_lower = query_text.lower()
        words = query_text.split()

        entities = []

        # STEP 1: Extract capitalized proper nouns (but filter common false positives)
        stop_capitalized = {
            'hey', 'okay', 'ok', 'alright', 'tell', 'give', 'show', 'what',
            'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could',
            'would', 'should', 'may', 'might', 'will', 'shall', 'i', 'you',
            'kay'  # Kay is the agent himself, not useful for entity search
        }
        for word in words:
            if len(word) > 2 and word[0].isupper():
                clean_word = re.sub(r'[^\w]', '', word).lower()
                if clean_word and clean_word not in stop_capitalized:
                    entities.append(clean_word)

        # STEP 2: Extract category keywords (nouns that might be in semantic knowledge)
        category_patterns = [
            r'\b(pigeon|pigeons|bird|birds)\b',
            r'\b(cat|cats|kitten|kittens)\b',
            r'\b(dog|dogs|puppy|puppies)\b',
            r'\b(person|people|human|humans)\b',
            r'\b(document|doc|file|paper|text)\b',
            r'\b(name|names)\b',
            r'\b(wrapper|system|engine|archive)\b',
            r'\b(memory|memories|thought|thoughts)\b',
            r'\b(coffee|tea|drink|beverage)\b',
            r'\b(mug|cup|spiral|symbol)\b'
        ]

        for pattern in category_patterns:
            matches = re.findall(pattern, query_lower)
            entities.extend(matches)

        # STEP 3: Extract noun phrases (adjective + noun combinations)
        # e.g., "one-legged pigeon", "speckled bird", "green eyes"
        noun_phrase_pattern = r'\b([a-z]+-[a-z]+\s+\w+|[a-z]+\s+pigeon|[a-z]+\s+cat|[a-z]+\s+dog)\b'
        noun_phrases = re.findall(noun_phrase_pattern, query_lower)
        entities.extend(noun_phrases)

        # STEP 4: Handle contextual references
        # If query contains "them", "their", "it", "those" - use previous entities
        contextual_refs = ['them', 'their', 'it', 'its', 'those', 'these', 'that', 'this']
        has_context_ref = any(ref in query_lower for ref in contextual_refs)

        if has_context_ref and self.previous_query_entities:
            print(f"[ENTITY EXTRACT] Context reference detected, using previous entities: {self.previous_query_entities}")
            entities.extend(self.previous_query_entities)

        # STEP 5: Check against known entities in semantic knowledge
        # DEPRECATED: semantic_knowledge removed (documents retrieved via llm_retrieval.py)
        if hasattr(self, 'semantic_knowledge') and self.semantic_knowledge:
            # Get all entities that exist in semantic knowledge
            known_entities = self.semantic_knowledge.get_all_entity_names()

            # Filter out self-references (Kay is the agent, not a search entity)
            known_entities = known_entities - {'kay'}

            # For each word in query, check if it matches a known entity
            for word in words:
                clean_word = re.sub(r'[^\w]', '', word).lower()
                if clean_word in known_entities and len(clean_word) > 1:
                    entities.append(clean_word)
                    print(f"[ENTITY EXTRACT] Found known entity: {clean_word}")

        # STEP 6: Deduplicate and clean
        entities = list(set([e.strip().lower() for e in entities if e and len(e) > 1]))

        # STEP 7: Remove pure stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
            'give', 'tell', 'show', 'say', 'said', 'see', 'look', 'know', 'think',
            'get', 'got', 'make', 'made', 'go', 'went', 'take', 'took', 'come', 'came',
            'want', 'need', 'let', 'put', 'set', 'use', 'find', 'ask', 'call'
        }
        entities = [e for e in entities if e not in stop_words]

        return entities

    def _clean_output(self, raw_output: str) -> str:
        """
        Clean any markdown or extraneous formatting from output.
        """
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```[\w]*\n?', '', raw_output)
        cleaned = cleaned.strip()
        return cleaned


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing GlyphFilter...")
    
    # Mock agent state
    test_state = {
        "memories": [
            {
                "perspective": "user",
                "fact": "My eyes are green",
                "user_input": "My eyes are green",
                "emotion_tags": [],
            },
            {
                "perspective": "kay",
                "fact": "Your eyes are gold",
                "user_input": "Your eyes are gold",
                "emotion_tags": [],
            },
            {
                "perspective": "kay",
                "fact": "I prefer coffee to get energized",
                "user_input": "I prefer coffee to get energized",
                "emotion_tags": ["curiosity"],
            },
            {
                "perspective": "kay",
                "fact": "I'm more of a tea person actually",
                "user_input": "I'm more of a tea person actually",
                "emotion_tags": ["curiosity"],
            },
        ],
        "emotional_cocktail": {
            "curiosity": {"intensity": 0.8, "age": 5},
            "affection": {"intensity": 0.3, "age": 10},
        },
        "recent_context": [
            {"user": "Hey Kay", "kay": "Hey Re, how's it going?"},
            {"user": "Pretty good", "kay": "Glad to hear it"},
        ]
    }
    
    filter_system = GlyphFilter()
    
    # Test filtering
    user_input = "What's your favorite drink?"
    result = filter_system.filter_context(test_state, user_input)
    
    print("\n--- FILTER OUTPUT ---")
    print(result)
    print("--- END OUTPUT ---\n")
    
    # Show what was sent to filter
    print("Filter received:")
    print(f"- {len(test_state['memories'])} memories")
    print(f"- {len(test_state['emotional_cocktail'])} active emotions")
    print(f"- {len(test_state['recent_context'])} recent turns")
    print(f"- Contradiction detected: coffee vs tea")