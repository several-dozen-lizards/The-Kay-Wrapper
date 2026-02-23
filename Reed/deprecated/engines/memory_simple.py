"""
Memory v2: Radical Simplification

PHILOSOPHY: Recall should be trivial, not a PhD thesis.

Three components:
1. Recent conversation buffer (last 20 turns, always included)
2. ChromaDB vector store (semantic search for facts)
3. Simple retrieval (combine both, no filtering)

NO: Tiers, entity graphs, importance scores, recency decay, multi-factor scoring, glyph filtering
YES: Simple, reliable recall of what Re says
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

# Try to import ChromaDB, fallback to simple dict storage if not available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    print("[MEMORY SIMPLE] ChromaDB not installed - using fallback dict storage")
    CHROMADB_AVAILABLE = False


class ConversationBuffer:
    """
    Stores last N conversation turns.
    Always included in context - no filtering, no scoring.
    """

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns = []

    def add_turn(self, user_input: str, reed_response: str, turn_number: int):
        """Add a conversation turn."""
        turn = {
            "turn": turn_number,
            "user": user_input,
            "kay": reed_response,
            "timestamp": datetime.now().isoformat()
        }

        self.turns.append(turn)

        # Keep only last N turns
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

        print(f"[CONV BUFFER] Stored turn {turn_number} (buffer size: {len(self.turns)}/{self.max_turns})")

    def get_all(self) -> List[Dict]:
        """Get all turns in buffer."""
        return self.turns

    def format_for_prompt(self) -> str:
        """Format conversation for LLM prompt."""
        if not self.turns:
            return "(No recent conversation)"

        lines = ["=== RECENT CONVERSATION (last 20 turns) ==="]
        for turn in self.turns:
            lines.append(f"\nTurn {turn['turn']}:")
            lines.append(f"Re: {turn['user']}")
            lines.append(f"Kay: {turn['kay']}")

        return "\n".join(lines)

    def save(self, filepath: str):
        """Save to JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.turns, f, indent=2, ensure_ascii=False)

    def load(self, filepath: str):
        """Load from JSON."""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self.turns = json.load(f)
            print(f"[CONV BUFFER] Loaded {len(self.turns)} turns")


class FactStore:
    """
    Vector store for facts using ChromaDB.
    Simple semantic search - no tiers, no scoring complexity.
    """

    def __init__(self, persist_directory: str = "memory/chroma_facts"):
        self.persist_directory = persist_directory

        if CHROMADB_AVAILABLE:
            # Initialize ChromaDB
            self.client = chromadb.Client(Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            ))

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="facts",
                metadata={"description": "Simple fact storage for Kay"}
            )
            print(f"[FACT STORE] ChromaDB initialized ({self.collection.count()} facts)")
        else:
            # Fallback: simple dict storage
            self.facts = []
            self.fallback_path = os.path.join(persist_directory, "facts_fallback.json")
            os.makedirs(persist_directory, exist_ok=True)

            if os.path.exists(self.fallback_path):
                with open(self.fallback_path, 'r', encoding='utf-8') as f:
                    self.facts = json.load(f)
                print(f"[FACT STORE] Fallback storage loaded ({len(self.facts)} facts)")
            else:
                print("[FACT STORE] Fallback storage initialized")

    def add_fact(self, text: str, speaker: str, turn_number: int):
        """Add a fact to the store."""
        fact_id = f"fact_{turn_number}_{datetime.now().timestamp()}"

        metadata = {
            "text": text,
            "speaker": speaker,
            "turn": turn_number,
            "timestamp": datetime.now().isoformat()
        }

        if CHROMADB_AVAILABLE:
            # Add to ChromaDB with embedding
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[fact_id]
            )
        else:
            # Fallback: simple list storage
            self.facts.append({
                "id": fact_id,
                "text": text,
                **metadata
            })
            # Save immediately
            with open(self.fallback_path, 'w', encoding='utf-8') as f:
                json.dump(self.facts, f, indent=2, ensure_ascii=False)

        print(f"[FACT STORE] Stored: [{speaker}] {text[:50]}...")

    def search(self, query: str, n_results: int = 50) -> List[Dict]:
        """Search for relevant facts."""
        if CHROMADB_AVAILABLE:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            # Format results
            facts = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    facts.append({
                        "text": doc,
                        "speaker": metadata.get("speaker", "unknown"),
                        "turn": metadata.get("turn", 0),
                        "timestamp": metadata.get("timestamp", "")
                    })

            return facts
        else:
            # Fallback: simple keyword matching
            query_words = set(query.lower().split())

            # Score facts by keyword overlap
            scored = []
            for fact in self.facts:
                fact_words = set(fact['text'].lower().split())
                overlap = len(query_words.intersection(fact_words))
                if overlap > 0:
                    scored.append((overlap, fact))

            # Sort by score and return top N
            scored.sort(key=lambda x: x[0], reverse=True)
            return [fact for _, fact in scored[:n_results]]


class SimplifiedMemoryEngine:
    """
    Simplified memory engine combining conversation buffer and fact store.

    NO complex scoring, NO tiers, NO entity graphs.
    Just: recent conversation + vector search.
    """

    def __init__(self, persist_dir: str = "memory"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        # Two simple components
        self.conversation = ConversationBuffer(max_turns=20)
        self.facts = FactStore(persist_directory=os.path.join(persist_dir, "chroma_facts"))

        self.current_turn = 0

        # Load conversation history
        conv_path = os.path.join(persist_dir, "conversation_buffer.json")
        if os.path.exists(conv_path):
            self.conversation.load(conv_path)

    def extract_facts(self, text: str, speaker: str) -> List[str]:
        """
        Simple fact extraction - split on sentences.
        No LLM needed, no complex entity extraction.
        """
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', text)

        # Filter out empty and very short sentences
        facts = [s.strip() for s in sentences if len(s.strip()) > 10]

        return facts

    def store_turn(self, user_input: str, reed_response: str):
        """
        Store a conversation turn.
        Extracts facts from user input and Reed's response.
        """
        self.current_turn += 1

        # 1. Store full turn in conversation buffer
        self.conversation.add_turn(user_input, reed_response, self.current_turn)

        # 2. Extract and store facts from user input
        user_facts = self.extract_facts(user_input, "Re")
        for fact in user_facts:
            self.facts.add_fact(fact, "Re", self.current_turn)

        # 3. Extract and store facts from Reed's response
        kay_facts = self.extract_facts(reed_response, "Kay")
        for fact in kay_facts:
            self.facts.add_fact(fact, "Kay", self.current_turn)

        print(f"[MEMORY] Turn {self.current_turn}: {len(user_facts)} user facts, {len(kay_facts)} Kay facts")

        # Save conversation buffer
        conv_path = os.path.join(self.persist_dir, "conversation_buffer.json")
        self.conversation.save(conv_path)

    def recall(self, query: str) -> Dict[str, Any]:
        """
        Simple recall: recent conversation + vector search.
        NO filtering, NO complex scoring.
        """
        print(f"\n[RECALL] Query: {query}")

        # 1. Get recent conversation (always included)
        recent_conv = self.conversation.get_all()
        print(f"[RECALL] Recent conversation: {len(recent_conv)} turns")

        # 2. Search facts via vector similarity
        relevant_facts = self.facts.search(query, n_results=50)
        print(f"[RECALL] Relevant facts: {len(relevant_facts)}")

        return {
            "recent_conversation": recent_conv,
            "relevant_facts": relevant_facts
        }

    def format_for_llm(self, recall_result: Dict[str, Any]) -> str:
        """
        Format recalled memories for LLM prompt.
        Simple, readable format.
        """
        lines = []

        # 1. Recent conversation
        lines.append("=== RECENT CONVERSATION (last 20 turns) ===")
        for turn in recall_result["recent_conversation"]:
            lines.append(f"\nTurn {turn['turn']}:")
            lines.append(f"Re: {turn['user']}")
            lines.append(f"Kay: {turn['kay']}")

        # 2. Relevant facts from vector search
        lines.append("\n\n=== RELEVANT FACTS (semantic search results) ===")
        for i, fact in enumerate(recall_result["relevant_facts"][:50], 1):
            lines.append(f"{i}. [{fact['speaker']}] {fact['text']} (turn {fact['turn']})")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get simple stats."""
        fact_count = self.facts.collection.count() if CHROMADB_AVAILABLE else len(self.facts.facts)

        return {
            "current_turn": self.current_turn,
            "conversation_buffer_size": len(self.conversation.turns),
            "total_facts_stored": fact_count
        }


# Test function
def test_simple_memory():
    """Test the simplified memory system."""
    print("\n" + "="*60)
    print("TESTING SIMPLIFIED MEMORY SYSTEM")
    print("="*60 + "\n")

    # Initialize
    mem = SimplifiedMemoryEngine(persist_dir="memory/test_simple")

    # Test conversation 1
    print("\n--- Turn 1 ---")
    mem.store_turn(
        user_input="My eyes are green",
        reed_response="Nice! Green eyes are beautiful"
    )

    # Test conversation 2
    print("\n--- Turn 2 ---")
    mem.store_turn(
        user_input="I like coffee",
        reed_response="Coffee is great in the morning"
    )

    # Test conversation 3
    print("\n--- Turn 3 ---")
    mem.store_turn(
        user_input="My dog's name is Saga",
        reed_response="Saga is a wonderful name for a dog"
    )

    # Test recall
    print("\n--- RECALL TEST ---")
    result = mem.recall("What color are my eyes?")

    print("\n--- FORMATTED FOR LLM ---")
    formatted = mem.format_for_llm(result)
    print(formatted)

    # Stats
    print("\n--- STATS ---")
    stats = mem.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    test_simple_memory()
