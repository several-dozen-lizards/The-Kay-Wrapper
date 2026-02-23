"""
Memory Continuity System for AI Persistence

A comprehensive solution for maintaining conversational and emotional continuity
in AI systems with ChromaDB vector storage.

Components:
- ThreadMomentumTracker: Track active conversation threads
- SessionBoundaryHandler: Manage session summaries and continuity
- SmartImportProcessor: Process document imports intelligently
- LayeredMemoryRetriever: Rebalance memory layer distribution
- EntityGraphCleaner: Consolidate contradictory entity attributes
- GuaranteedContextLoader: Ensure critical memories always load
"""

from .thread_momentum import ThreadMomentumTracker, ConversationThread
from .session_boundary import SessionBoundaryHandler, SessionSummary
from .smart_import import SmartImportProcessor, ImportSynthesis
from .layered_retrieval import (
    LayeredMemoryRetriever,
    RetrievalConfig,
    LayerBalancer
)
from .entity_cleanup import (
    EntityGraphCleaner,
    AttributeConflict,
    ConsolidationResult
)
from .guaranteed_context import (
    GuaranteedContextLoader,
    GuaranteedMemory
)

__version__ = "1.0.0"

__all__ = [
    # Thread momentum
    "ThreadMomentumTracker",
    "ConversationThread",

    # Session boundaries
    "SessionBoundaryHandler",
    "SessionSummary",

    # Smart imports
    "SmartImportProcessor",
    "ImportSynthesis",

    # Layered retrieval
    "LayeredMemoryRetriever",
    "RetrievalConfig",
    "LayerBalancer",

    # Entity cleanup
    "EntityGraphCleaner",
    "AttributeConflict",
    "ConsolidationResult",

    # Guaranteed context
    "GuaranteedContextLoader",
    "GuaranteedMemory",
]
