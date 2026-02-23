"""
Smart Import Boosting System

Replaces blanket import boosting with relevance-based boosting.
Only boosts document imports that are semantically relevant to the current query.

BEFORE (Blanket Boost):
    All recent imports get 2.0x boost regardless of relevance
    → Irrelevant document facts dominate retrieval

AFTER (Smart Boost):
    Only relevant imports get boosted based on keyword overlap
    → Document facts appear when actually relevant
"""

from typing import List, Dict, Any, Set
import re


class SmartImportBooster:
    """
    Calculate relevance-based boost for imported document memories.

    Instead of blanket 2.0x boost for all recent imports, calculates
    semantic relevance and applies proportional boost (0.0x to 2.0x).
    """

    def __init__(self,
                 max_boost: float = 2.0,
                 relevance_threshold: float = 0.3,
                 keyword_weight: float = 0.7,
                 entity_weight: float = 0.3):
        """
        Initialize smart import booster.

        Args:
            max_boost: Maximum boost multiplier (2.0 = 200%)
            relevance_threshold: Minimum relevance to apply any boost (0.3 = 30%)
            keyword_weight: Weight for keyword similarity (default 70%)
            entity_weight: Weight for entity overlap (default 30%)
        """
        self.max_boost = max_boost
        self.relevance_threshold = relevance_threshold
        self.keyword_weight = keyword_weight
        self.entity_weight = entity_weight

    def calculate_import_boost(self,
                               import_memory: Dict[str, Any],
                               query: str,
                               query_entities: Set[str] = None) -> float:
        """
        Calculate relevance-based boost for an imported memory.

        Args:
            import_memory: Memory from document import
            query: Current query/user input
            query_entities: Set of entities mentioned in query

        Returns:
            Boost multiplier (0.0 to max_boost)
        """
        # Extract keywords from query
        query_keywords = self._extract_keywords(query)

        # Extract keywords from memory
        memory_text = self._get_memory_text(import_memory)
        memory_keywords = self._extract_keywords(memory_text)

        # Calculate keyword similarity
        keyword_similarity = self._calculate_keyword_overlap(
            query_keywords,
            memory_keywords
        )

        # Calculate entity similarity
        entity_similarity = 0.0
        if query_entities:
            memory_entities = set(import_memory.get('entities', []))
            entity_similarity = self._calculate_entity_overlap(
                query_entities,
                memory_entities
            )

        # Combined relevance score
        relevance = (
            keyword_similarity * self.keyword_weight +
            entity_similarity * self.entity_weight
        )

        # Apply threshold
        if relevance < self.relevance_threshold:
            # Below threshold - no boost
            return 0.0

        # Scale boost proportional to relevance
        # relevance 0.3 -> 0.0x boost
        # relevance 1.0 -> max_boost
        normalized_relevance = (relevance - self.relevance_threshold) / (1.0 - self.relevance_threshold)
        boost = normalized_relevance * self.max_boost

        return boost

    def apply_smart_boost(self,
                         memories: List[Dict[str, Any]],
                         query: str,
                         current_turn: int,
                         import_window: int = 5,
                         query_entities: Set[str] = None) -> List[Dict[str, Any]]:
        """
        Apply smart boost to recent imports in memory list.

        Args:
            memories: List of all memories to score
            query: Current query/user input
            current_turn: Current turn number
            import_window: How many recent turns count as "recent import" (default 5)
            query_entities: Set of entities mentioned in query

        Returns:
            Memories with 'smart_import_boost' field added
        """
        boosted_count = 0
        skipped_count = 0

        for memory in memories:
            # Check if this is a recent import
            if not memory.get('is_import', False):
                memory['smart_import_boost'] = 0.0
                continue

            import_turn = memory.get('turn_index', 0)
            age = current_turn - import_turn

            if age > import_window:
                # Too old, no boost
                memory['smart_import_boost'] = 0.0
                skipped_count += 1
                continue

            # Calculate relevance-based boost
            boost = self.calculate_import_boost(
                memory,
                query,
                query_entities
            )

            memory['smart_import_boost'] = boost

            if boost > 0.0:
                boosted_count += 1
            else:
                skipped_count += 1

        if boosted_count > 0:
            print(f"[SMART BOOST] Applied to {boosted_count} imports, skipped {skipped_count} irrelevant")

        return memories

    def get_boost_stats(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about import boosting.

        Args:
            memories: List of memories with smart_import_boost field

        Returns:
            Dict with boost statistics
        """
        imports = [m for m in memories if m.get('is_import', False)]
        boosted = [m for m in imports if m.get('smart_import_boost', 0.0) > 0.0]

        if not imports:
            return {
                'total_imports': 0,
                'boosted': 0,
                'skipped': 0,
                'avg_boost': 0.0
            }

        avg_boost = sum(m.get('smart_import_boost', 0.0) for m in boosted) / len(boosted) if boosted else 0.0

        return {
            'total_imports': len(imports),
            'boosted': len(boosted),
            'skipped': len(imports) - len(boosted),
            'avg_boost': avg_boost,
            'max_boost': max((m.get('smart_import_boost', 0.0) for m in imports), default=0.0)
        }

    # Private helper methods

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extract meaningful keywords from text.

        Args:
            text: Text to extract from

        Returns:
            Set of normalized keywords
        """
        # Convert to lowercase
        text_lower = text.lower()

        # Remove punctuation
        text_clean = re.sub(r'[^\w\s]', ' ', text_lower)

        # Split into words
        words = text_clean.split()

        # Filter stopwords and short words
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'me', 'him', 'them'
        }

        keywords = {
            word for word in words
            if len(word) > 2 and word not in stopwords
        }

        return keywords

    def _calculate_keyword_overlap(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """
        Calculate keyword overlap using Jaccard similarity.

        Args:
            keywords1: First set of keywords
            keywords2: Second set of keywords

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not keywords1 or not keywords2:
            return 0.0

        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _calculate_entity_overlap(self, entities1: Set[str], entities2: Set[str]) -> float:
        """
        Calculate entity overlap using Jaccard similarity.

        Args:
            entities1: First set of entities
            entities2: Second set of entities

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not entities1 or not entities2:
            return 0.0

        # Normalize entity names (lowercase)
        entities1_norm = {e.lower() for e in entities1}
        entities2_norm = {e.lower() for e in entities2}

        intersection = entities1_norm & entities2_norm
        union = entities1_norm | entities2_norm

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _get_memory_text(self, memory: Dict[str, Any]) -> str:
        """Extract searchable text from memory."""
        text = memory.get('fact', '')
        if not text:
            text = memory.get('text', '')
        if not text:
            text = memory.get('content', '')
        return str(text)


# Backwards compatibility: Replace blanket boost with smart boost
def replace_blanket_boost_in_retrieval(memories: List[Dict[str, Any]],
                                       query: str,
                                       current_turn: int,
                                       smart_booster: SmartImportBooster,
                                       query_entities: Set[str] = None) -> List[Dict[str, Any]]:
    """
    Replace blanket import boost with smart relevance-based boost.

    Use this in memory_engine.py retrieve_biased_memories() to replace:
        if mem.get('is_import', False):
            import_boost = 2.0  # OLD: blanket boost

    With:
        memories = replace_blanket_boost_in_retrieval(
            memories, query, current_turn, smart_booster, query_entities
        )
        # Then use mem.get('smart_import_boost', 0.0) in scoring

    Args:
        memories: List of memories to process
        query: Current query
        current_turn: Current turn number
        smart_booster: SmartImportBooster instance
        query_entities: Optional set of query entities

    Returns:
        Memories with smart_import_boost field added
    """
    return smart_booster.apply_smart_boost(
        memories,
        query,
        current_turn,
        import_window=5,
        query_entities=query_entities
    )


def format_boost_report(stats: Dict[str, Any]) -> str:
    """
    Format boost statistics for logging.

    Args:
        stats: Statistics from get_boost_stats()

    Returns:
        Formatted string
    """
    if stats['total_imports'] == 0:
        return "[SMART BOOST] No recent imports"

    lines = [
        f"[SMART BOOST] Stats:",
        f"  Total imports: {stats['total_imports']}",
        f"  Boosted (relevant): {stats['boosted']}",
        f"  Skipped (irrelevant): {stats['skipped']}",
        f"  Avg boost: {stats['avg_boost']:.2f}x",
        f"  Max boost: {stats['max_boost']:.2f}x"
    ]

    return "\n".join(lines)
