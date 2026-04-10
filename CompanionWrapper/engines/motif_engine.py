# engines/motif_engine.py
import json
import os
import re
from collections import Counter
from typing import Dict, List, Set


class MotifEngine:
    """
    Tracks recurring entities (people, places, concepts) across conversations
    and weights their importance based on frequency and recency.
    """

    def __init__(self, motif_file: str = None):
        if motif_file is None:
            motif_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "motifs.json"
            )
        self.motif_file = motif_file
        self.entity_counts: Counter = Counter()
        self.entity_last_seen: Dict[str, int] = {}
        self.turn_counter = 0
        self._load_motifs()

    def _load_motifs(self):
        """Load saved motif data from disk."""
        if os.path.exists(self.motif_file):
            try:
                with open(self.motif_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entity_counts = Counter(data.get("counts", {}))
                    self.entity_last_seen = data.get("last_seen", {})
                    self.turn_counter = data.get("turn_counter", 0)
            except Exception as e:
                print(f"(Motif load error: {e})")

    def _save_motifs(self):
        """Save motif data to disk."""
        os.makedirs(os.path.dirname(self.motif_file), exist_ok=True)
        try:
            with open(self.motif_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "counts": dict(self.entity_counts),
                        "last_seen": self.entity_last_seen,
                        "turn_counter": self.turn_counter,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            print(f"(Motif save error: {e})")

    def _extract_entities(self, text: str) -> Set[str]:
        """
        Extract potential entities from text.
        Simple heuristic: capitalized words, proper nouns, quoted phrases.
        """
        entities = set()

        # Find capitalized words (potential proper nouns)
        # Exclude common sentence starters
        words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        exclude = {"I", "The", "A", "An", "This", "That", "What", "Why", "How", "When", "Where"}
        for word in words:
            if word not in exclude:
                entities.add(word.lower())

        # Find quoted phrases (explicit references)
        quoted = re.findall(r'"([^"]+)"', text)
        for phrase in quoted:
            if len(phrase.split()) <= 4:  # Only short phrases
                entities.add(phrase.lower())

        # Find possessive constructs (e.g., "the entity's", "Re's", "mom's")
        possessives = re.findall(r"\b([A-Z][a-z]+)'s\b", text)
        for poss in possessives:
            entities.add(poss.lower())

        return entities

    def update(self, agent_state, user_input: str):
        """
        Extract entities from user input and update tracking.
        Runs in parallel with other engines.
        """
        self.turn_counter += 1
        entities = self._extract_entities(user_input)

        for entity in entities:
            self.entity_counts[entity] += 1
            self.entity_last_seen[entity] = self.turn_counter

        # Store top motifs in agent state for use by other systems
        top_motifs = self.get_top_motifs(n=10)
        agent_state.meta["motifs"] = top_motifs

        self._save_motifs()

    def get_entity_weight(self, entity: str) -> float:
        """
        Calculate weight for an entity based on frequency and recency.
        Returns 0.0-1.0 score.
        """
        if entity.lower() not in self.entity_counts:
            return 0.0

        entity_key = entity.lower()
        frequency = self.entity_counts[entity_key]
        last_seen = self.entity_last_seen.get(entity_key, 0)
        recency = self.turn_counter - last_seen

        # Frequency component (normalized by log to prevent dominance)
        freq_score = min(1.0, frequency / 10.0)

        # Recency component (decay over turns)
        recency_score = max(0.0, 1.0 - (recency / 50.0))

        # Weighted combination
        return 0.6 * freq_score + 0.4 * recency_score

    def get_top_motifs(self, n: int = 10) -> List[Dict[str, any]]:
        """Return top N entities by weight."""
        motifs = []
        for entity, count in self.entity_counts.most_common(n * 2):  # Get more to filter
            weight = self.get_entity_weight(entity)
            if weight > 0.1:  # Minimum threshold
                motifs.append(
                    {
                        "entity": entity,
                        "count": count,
                        "weight": round(weight, 3),
                        "last_seen": self.entity_last_seen.get(entity, 0),
                    }
                )
        motifs.sort(key=lambda x: x["weight"], reverse=True)
        return motifs[:n]

    def score_memory_by_motifs(self, memory_text: str) -> float:
        """
        Score a memory based on how many important motifs it contains.
        Returns accumulated weight from all contained entities.
        """
        entities = self._extract_entities(memory_text)
        total_weight = 0.0

        for entity in entities:
            total_weight += self.get_entity_weight(entity)

        return total_weight
