"""
Simplified memory engine - keyword matching only.
No emotional biasing, no motif weighting, no momentum boosts.
Just store memories and retrieve by keyword overlap.
"""
import json
import os
import re
from typing import List, Dict


class SimpleMemoryEngine:
    def __init__(self, file_path: str = "memory/memories_simple.json"):
        self.file_path = file_path
        self.memories: List[Dict] = []

        # Load existing memories
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
            except Exception:
                self.memories = []

    def _save(self):
        """Save memories to disk."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2)

    def _detect_perspective(self, text: str) -> str:
        """
        Simple perspective detection:
        - "I/my/me" = user
        - "you/your" = kay
        - "we/us" = shared
        """
        text = text.lower()

        if re.search(r'\b(i|my|me)\b', text):
            return "user"
        elif re.search(r'\b(you|your)\b', text):
            return "kay"
        elif re.search(r'\b(we|us|our)\b', text):
            return "shared"

        return "user"  # default

    def store(self, user_input: str, kay_response: str):
        """Store a memory - just user input, response, perspective, timestamp."""
        import time

        perspective = self._detect_perspective(user_input)

        memory = {
            "user_input": user_input,
            "response": kay_response,
            "perspective": perspective,
            "timestamp": time.time()
        }

        self.memories.append(memory)
        self._save()

    def retrieve(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Retrieve memories by keyword overlap only.
        No fancy scoring - just count matching words.
        """
        if not self.memories:
            return []

        # Extract keywords from query
        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return []

        # Score each memory by keyword overlap
        scored = []
        for mem in self.memories:
            text = (mem.get("user_input", "") + " " + mem.get("response", "")).lower()
            overlap = sum(1 for word in query_words if word in text)

            if overlap > 0:
                scored.append((overlap, mem))

        # Sort by score and return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:limit]]

    def get_all(self) -> List[Dict]:
        """Get all memories (for debugging)."""
        return self.memories

    def clear(self):
        """Clear all memories."""
        self.memories = []
        self._save()
