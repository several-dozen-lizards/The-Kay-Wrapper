"""
Token-budget-based context building.

NO arbitrary limits. Only constraint is token budget.
"""

from typing import Dict, List, Any, Optional
import json
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return len(text) // 4


class ContextBuilder:
    """
    Build context from current session + past sessions + identity + documents.

    RULES:
    - Current session: ALWAYS include 100%
    - Identity facts: ALWAYS include
    - Past sessions: Include until token budget exhausted
    - Documents: Include if relevant
    """

    TOKEN_BUDGET = 180000  # Leave 20k for response

    def __init__(self, session_memory, vector_store=None):
        self.session_memory = session_memory
        self.vector_store = vector_store

        print(f"[CONTEXT] Initialized with token budget: {self.TOKEN_BUDGET}")

    def build_context(
        self,
        query: str,
        current_emotional_state: Dict,
        include_documents: bool = True
    ) -> Dict:
        """
        Build complete context for Kay's response.

        Priority order:
        1. Current session (100%, always)
        2. Identity facts (always)
        3. Relevant documents (if query references them)
        4. Past sessions (by emotional/semantic similarity until budget exhausted)
        """
        context = {
            "current_session": None,
            "identity": None,
            "documents": [],
            "past_sessions": [],
            "total_tokens": 0
        }

        tokens_used = 0

        # 1. ENTIRE current session (priority #1)
        current_session = self.session_memory.get_current_session()
        session_tokens = estimate_tokens(json.dumps(current_session))

        context["current_session"] = current_session
        tokens_used += session_tokens

        print(f"[CONTEXT] Current session: {len(current_session['turns'])} turns, {session_tokens} tokens")

        # 2. Identity facts (always include)
        identity = self.session_memory.identity_facts
        identity_tokens = estimate_tokens(json.dumps(identity))

        context["identity"] = identity
        tokens_used += identity_tokens

        print(f"[CONTEXT] Identity facts: {len(identity)} entities, {identity_tokens} tokens")

        # 3. Documents (if referenced in query)
        if include_documents and self.vector_store:
            doc_tokens = self._add_relevant_documents(
                context,
                query,
                remaining_budget=self.TOKEN_BUDGET - tokens_used
            )
            tokens_used += doc_tokens

        # 4. Past sessions (fill remaining budget)
        remaining = self.TOKEN_BUDGET - tokens_used
        if remaining > 10000:  # Only if meaningful space left
            past_tokens = self._add_past_sessions(
                context,
                query,
                current_emotional_state,
                max_tokens=remaining
            )
            tokens_used += past_tokens

        context["total_tokens"] = tokens_used
        print(f"[CONTEXT] Total: {tokens_used} tokens (budget: {self.TOKEN_BUDGET})")

        return context

    def _add_relevant_documents(self, context: Dict, query: str, remaining_budget: int) -> int:
        """Add relevant document chunks if query references documents."""
        if not self.vector_store:
            return 0

        # Check if query references documents
        query_lower = query.lower()
        doc_indicators = ["document", "story", "read", "yw", "file", "pigeon", "delia", "mattie", "tell me about"]

        if not any(ind in query_lower for ind in doc_indicators):
            return 0

        try:
            # Retrieve relevant chunks (adaptive based on query)
            results = self.vector_store.query(query_text=query, n_results=50)

            # Handle different return formats from vector store
            if isinstance(results, dict):
                # ChromaDB format
                chunks = []
                if 'documents' in results and results['documents']:
                    for doc_list in results['documents']:
                        for doc in doc_list:
                            chunks.append({"text": doc})
                elif 'metadatas' in results and results['metadatas']:
                    for metadata_list in results['metadatas']:
                        for metadata in metadata_list:
                            if 'text' in metadata:
                                chunks.append({"text": metadata['text']})
            elif isinstance(results, list):
                chunks = results
            else:
                chunks = []

            tokens_used = 0
            for chunk in chunks:
                chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                chunk_tokens = estimate_tokens(chunk_text)

                if tokens_used + chunk_tokens <= remaining_budget:
                    context["documents"].append({"text": chunk_text})
                    tokens_used += chunk_tokens
                else:
                    break

            if chunks:
                print(f"[CONTEXT] Documents: {len(context['documents'])} chunks, {tokens_used} tokens")

            return tokens_used

        except Exception as e:
            print(f"[CONTEXT] Warning: Document retrieval failed: {e}")
            return 0

    def _add_past_sessions(
        self,
        context: Dict,
        query: str,
        current_emotional_state: Dict,
        max_tokens: int
    ) -> int:
        """
        Add past sessions ranked by emotional/semantic similarity.

        Continue adding until token budget exhausted.
        """
        # Load all past sessions
        try:
            past_sessions = self.session_memory.load_past_sessions()
        except Exception as e:
            print(f"[CONTEXT] Warning: Failed to load past sessions: {e}")
            return 0

        if not past_sessions:
            return 0

        # Score by emotional + semantic similarity
        scored_sessions = []
        for session in past_sessions:
            # Emotional similarity (compare to current state)
            emotional_score = self._emotional_similarity(
                current_emotional_state,
                session.get("emotional_arc", {}).get("current", {})
            )

            # Semantic similarity (simple keyword matching for now)
            semantic_score = self._semantic_similarity(query, session)

            total_score = (emotional_score * 0.6) + (semantic_score * 0.4)
            scored_sessions.append((total_score, session))

        # Sort by relevance
        scored_sessions.sort(reverse=True, key=lambda x: x[0])

        # Add sessions until budget exhausted
        tokens_used = 0
        for score, session in scored_sessions:
            session_tokens = estimate_tokens(json.dumps(session))
            if tokens_used + session_tokens <= max_tokens:
                context["past_sessions"].append(session)
                tokens_used += session_tokens
            else:
                break

        if context["past_sessions"]:
            print(f"[CONTEXT] Past sessions: {len(context['past_sessions'])} sessions, {tokens_used} tokens")

        return tokens_used

    def _emotional_similarity(self, state1: Dict, state2: Dict) -> float:
        """Calculate emotional similarity (0-1)."""
        if not state1 or not state2:
            return 0.0

        primary1 = state1.get("primary", "")
        primary2 = list(state2.keys())[0] if state2 else ""

        if not primary1 or not primary2:
            return 0.0

        # Exact match = high similarity
        if primary1 == primary2:
            return 1.0

        # Related emotions = medium similarity
        related_emotions = {
            "curiosity": ["intrigue", "interest", "wonder"],
            "intrigue": ["curiosity", "fascination"],
            "joy": ["happiness", "excitement", "delight"],
            "sadness": ["melancholy", "grief", "sorrow"],
            "anger": ["frustration", "irritation", "rage"],
            "fear": ["anxiety", "worry", "panic"]
        }

        if primary1 in related_emotions:
            if primary2 in related_emotions[primary1]:
                return 0.6

        # No match
        return 0.3

    def _semantic_similarity(self, query: str, session: Dict) -> float:
        """Calculate semantic similarity (0-1)."""
        query_words = set(query.lower().split())

        if not query_words:
            return 0.0

        session_text = " ".join([
            turn.get("user_input", "") + " " + turn.get("kay_response", "")
            for turn in session.get("turns", [])
        ]).lower()

        session_words = set(session_text.split())

        if not session_words:
            return 0.0

        overlap = len(query_words.intersection(session_words))
        return min(1.0, overlap / len(query_words))

    def format_for_llm(self, context: Dict, include_past_sessions: bool = True) -> str:
        """Format context as natural language for LLM prompt."""
        sections = []

        # Identity facts (at top for visibility)
        if context["identity"]:
            identity_text = "=== IDENTITY ===\n\n"
            for entity, facts in context["identity"].items():
                if facts:  # Only show entities with facts
                    identity_text += f"{entity}:\n"
                    for attr, value in facts.items():
                        identity_text += f"  {attr}: {value}\n"
                    identity_text += "\n"
            sections.append(identity_text)

        # Current session
        if context["current_session"]:
            session = context["current_session"]
            conv_text = "=== CURRENT SESSION ===\n\n"

            if not session["turns"]:
                conv_text += "(No turns yet in this session)\n"
            else:
                for turn in session["turns"]:
                    turn_type = turn.get("type", "conversation")

                    conv_text += f"[Turn {turn.get('turn_id', 0)}]\n"
                    conv_text += f"You: {turn.get('user_input', '')}\n"
                    conv_text += f"Kay: {turn.get('kay_response', '')}\n"

                    if turn_type == "document_reading":
                        doc_name = turn.get('document_filename', 'unknown')
                        conv_text += f"  [Kay read document: {doc_name}]\n"

                    # Show emotional state
                    emotion = turn.get("emotional_state", {})
                    if emotion:
                        conv_text += f"  [Emotion: {emotion.get('primary', 'neutral')} ({emotion.get('intensity', 0):.1f})]\n"

                    conv_text += "\n"

            sections.append(conv_text)

        # Documents (if any)
        if context["documents"]:
            doc_text = "=== RELEVANT DOCUMENTS ===\n\n"
            for i, chunk in enumerate(context["documents"][:20]):  # Limit to avoid overwhelming
                doc_text += f"[Chunk {i+1}]\n{chunk.get('text', '')}\n\n"
            sections.append(doc_text)

        # Past sessions (if any and requested)
        if include_past_sessions and context["past_sessions"]:
            past_text = f"=== PAST SESSIONS ({len(context['past_sessions'])} relevant) ===\n\n"
            for session in context["past_sessions"][:3]:  # Show summary of top 3
                session_id = session.get('session_id', 'unknown')
                started = session.get('started', '')[:10]  # Just date
                turn_count = len(session.get('turns', []))

                past_text += f"Session {session_id} from {started} ({turn_count} turns):\n"

                # Show first 5 turns as summary
                for turn in session["turns"][:5]:
                    user_input = turn.get('user_input', '')
                    if len(user_input) > 100:
                        user_input = user_input[:97] + "..."
                    past_text += f"  - {user_input}\n"

                if turn_count > 5:
                    past_text += f"  ... and {turn_count - 5} more turns\n"

                past_text += "\n"

            sections.append(past_text)

        return "\n\n".join(sections)
