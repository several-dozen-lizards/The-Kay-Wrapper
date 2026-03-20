"""
Complete Example: Memory Continuity System Integration

This example shows how all components work together in a real conversation flow.
"""

import asyncio
import chromadb
from typing import Dict, List, Any
import json

# Import all continuity components
from thread_momentum import ThreadMomentumTracker
from session_boundary import SessionBoundaryHandler
from smart_import import SmartImportProcessor
from layered_retrieval import LayeredMemoryRetriever, RetrievalConfig
from entity_cleanup import EntityGraphCleaner
from guaranteed_context import GuaranteedContextLoader


# Mock implementations (replace with your actual implementations)
class MockLLMClient:
    """Mock LLM client for demonstration"""

    async def query(self, prompt: str, max_tokens: int = 150, temperature: float = 0.3) -> str:
        # In real implementation, call your LLM API
        return json.dumps({
            "consolidated_value": "example value",
            "confidence": 0.8,
            "reasoning": "Most recent value appears correct",
            "is_evolution": False,
            "discard_values": []
        })


class MockEntityGraph:
    """Mock entity graph for demonstration"""

    def __init__(self):
        self.entities = {}

    def get_entity(self, entity_id: str):
        return self.entities.get(entity_id)

    def get_all_entity_ids(self):
        return list(self.entities.keys())

    def get_top_preferences(self, limit: int = 5):
        return [
            {"description": "Prefers direct communication", "stability": 0.9},
            {"description": "Values analytical thinking", "stability": 0.85},
            {"description": "Enjoys problem-solving", "stability": 0.8}
        ]


class MockMemoryStore:
    """Adapter for memory store"""

    def __init__(self, collection):
        self.collection = collection

    def get_layer_distribution(self):
        return {
            "working": 20,
            "episodic": 150,
            "semantic": 180
        }


# Initialize ChromaDB (in-memory for example)
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="memories",
    metadata={"description": "AI entity memories"}
)


class ConversationManager:
    """
    Manages conversation flow with full memory continuity
    """

    def __init__(self):
        # Initialize all components
        self.llm = MockLLMClient()
        self.entity_graph = MockEntityGraph()

        self.thread_tracker = ThreadMomentumTracker(
            dormancy_threshold=5,
            momentum_threshold=0.3
        )

        self.session_handler = SessionBoundaryHandler(self.llm)

        self.import_processor = SmartImportProcessor(
            self.llm,
            self.session_handler
        )

        retrieval_config = RetrievalConfig(
            working_multiplier=3.0,
            episodic_multiplier=2.0,
            semantic_multiplier=0.8,
            target_working_ratio=0.20,
            target_episodic_ratio=0.50,
            target_semantic_ratio=0.30
        )

        self.retriever = LayeredMemoryRetriever(collection, retrieval_config)

        self.entity_cleaner = EntityGraphCleaner(
            self.entity_graph,
            self.llm,
            stale_threshold_turns=100,
            inactive_threshold_turns=50
        )

        self.context_loader = GuaranteedContextLoader(collection)

        # Session state
        self.current_turn = 0
        self.conversation_history = []
        self.emotional_state = {}

    async def start_session(self, session_id: str):
        """Initialize a new conversation session"""

        print(f"\n{'='*60}")
        print(f"STARTING SESSION: {session_id}")
        print(f"{'='*60}\n")

        # Load previous session if exists
        previous_summary = self.session_handler.load_summary(
            f"sessions/{session_id}_summary.json"
        )

        if previous_summary:
            print("📂 Found previous session summary!")

            # Restore thread state
            if hasattr(previous_summary, 'open_threads'):
                thread_summary = {
                    "active_threads": previous_summary.open_threads,
                    "current_turn": previous_summary.total_turns
                }
                self.thread_tracker.restore_from_summary(thread_summary)
                self.current_turn = previous_summary.total_turns

            # Load guaranteed context
            guaranteed_memories = self.context_loader.load_session_start_context(
                session_summary=previous_summary,
                current_turn=self.current_turn,
                entity_graph=self.entity_graph,
                max_guaranteed=50
            )

            print(f"\n✓ Loaded {len(guaranteed_memories)} guaranteed memories")
            print(self.context_loader.get_guaranteed_summary(guaranteed_memories))

            # Generate session start context
            session_context = self.session_handler.generate_session_start_context(
                previous_summary,
                max_length=1000
            )

            print(f"\n{'='*60}")
            print("SESSION CONTINUITY CONTEXT")
            print(f"{'='*60}")
            print(session_context)
            print(f"{'='*60}\n")

            return guaranteed_memories
        else:
            print("📝 Starting fresh session (no previous history)")
            return []

    async def process_turn(self, user_input: str, emotional_state: Dict[str, float]):
        """Process a single conversation turn"""

        self.current_turn += 1
        self.emotional_state = emotional_state

        print(f"\n--- TURN {self.current_turn} ---")
        print(f"User: {user_input}")

        # Extract entities and keywords (mock implementation)
        entities = self._extract_entities(user_input)
        keywords = self._extract_keywords(user_input)

        print(f"Extracted entities: {entities}")
        print(f"Extracted keywords: {keywords}")

        # Load guaranteed context for this turn
        guaranteed_turn_context = self.context_loader.load_turn_guaranteed_context(
            current_turn=self.current_turn,
            user_input=user_input,
            thread_tracker=self.thread_tracker,
            emotional_state=emotional_state
        )

        print(f"\n🔒 {len(guaranteed_turn_context)} guaranteed memories for this turn")

        # Retrieve memories with layer weighting
        retrieved_memories = self.retriever.retrieve(
            query=user_input,
            current_turn=self.current_turn,
            n_results=225,
            thread_tracker=self.thread_tracker,
            emotional_state=emotional_state,
            guaranteed_ids=[m.memory_id for m in guaranteed_turn_context]
        )

        # Merge guaranteed + retrieved
        final_memories = self.context_loader.merge_with_retrieved(
            guaranteed_memories=guaranteed_turn_context,
            retrieved_memories=retrieved_memories,
            max_total=225
        )

        # Analyze retrieval quality
        quality = self.retriever.analyze_retrieval_quality(final_memories, user_input)
        print(f"\n📊 Retrieval Quality:")
        print(f"   Layer distribution: "
              f"W={quality['distribution']['working_pct']:.1f}% "
              f"E={quality['distribution']['episodic_pct']:.1f}% "
              f"S={quality['distribution']['semantic_pct']:.1f}%")
        print(f"   Avg age: {quality['avg_age_turns']:.1f} turns")
        print(f"   Thread coverage: {quality['thread_coverage']} threads")

        # Generate LLM response (mock)
        agent_response = f"[Agent response to: {user_input[:50]}...]"

        # Extract questions from response (mock)
        open_questions = self._extract_questions(agent_response)

        # Update thread tracker
        self.thread_tracker.update_from_turn(
            user_input=user_input,
            agent_response=agent_response,
            extracted_entities=entities,
            extracted_keywords=keywords,
            memory_ids_referenced=[m["id"] for m in final_memories[:10]],
            open_questions=open_questions,
            emotional_intensity=max(emotional_state.values()) if emotional_state else 0.0
        )

        # Show active threads
        active_threads = self.thread_tracker.get_active_threads()
        print(f"\n🧵 Active threads: {len(active_threads)}")
        for thread in active_threads[:3]:
            print(f"   • {thread.thread_id}")
            print(f"     Momentum: {thread.momentum_score(self.current_turn):.2f}")
            print(f"     Entities: {', '.join(list(thread.entities)[:3])}")

        # Track reaction if significant
        if self._is_significant_reaction(agent_response):
            self.session_handler.track_reaction(
                trigger=user_input[:100],
                reaction=agent_response[:200]
            )

        # Store conversation
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": agent_response})

        return agent_response, final_memories

    async def import_document(self, document_content: str, document_description: str):
        """Import a document using smart processing"""

        print(f"\n{'='*60}")
        print(f"IMPORTING DOCUMENT: {document_description}")
        print(f"{'='*60}")

        # Get active threads
        active_threads = self.thread_tracker.get_active_threads()

        # Get existing knowledge
        existing_knowledge = self.retriever.retrieve(
            query=document_description,
            current_turn=self.current_turn,
            n_results=10,
            thread_tracker=None,
            emotional_state=None
        )
        existing_knowledge_text = [m["content"] for m in existing_knowledge[:5]]

        # Process through entity's perspective
        synthesis = await self.import_processor.process_document_import(
            document_content=document_content,
            document_description=document_description,
            entity_name="Kay",
            current_emotional_state=self.emotional_state,
            active_threads=[
                {
                    "thread_id": t.thread_id,
                    "entities": list(t.entities),
                    "keywords": list(t.keywords)
                }
                for t in active_threads
            ],
            existing_knowledge_sample=existing_knowledge_text
        )

        print(f"\n📝 SYNTHESIS RESULT:")
        print(f"   Personal reaction: {synthesis.personal_reaction}")
        print(f"   Emotional response: {synthesis.emotional_response}")
        print(f"   Essential facts: {len(synthesis.essential_facts)}")
        print(f"   Compression: {synthesis.original_fact_count} → {len(synthesis.essential_facts)} "
              f"({synthesis.compression_ratio:.1%})")

        # Store as episodic + semantic (limited)
        episodic_memory = self.import_processor.create_episodic_memory(
            synthesis,
            self.current_turn
        )
        semantic_memories = self.import_processor.create_semantic_memories(
            synthesis,
            self.current_turn
        )

        # Add to ChromaDB (mock - would normally do this)
        print(f"\n✓ Stored 1 episodic memory + {len(semantic_memories)} semantic facts")
        print(f"   (vs. {synthesis.original_fact_count} with raw extraction)")

        return synthesis

    async def end_session(self, session_id: str):
        """End session and generate summary"""

        print(f"\n{'='*60}")
        print(f"ENDING SESSION: {session_id}")
        print(f"{'='*60}\n")

        # Generate session summary
        summary = await self.session_handler.generate_session_end_summary(
            session_id=session_id,
            conversation_history=self.conversation_history,
            thread_tracker=self.thread_tracker,
            emotional_state=self.emotional_state,
            memory_store=MockMemoryStore(collection),
            entity_graph=self.entity_graph
        )

        # Save summary
        self.session_handler.save_summary(
            summary,
            f"sessions/{session_id}_summary.json"
        )

        print(f"📊 SESSION SUMMARY:")
        print(f"   Total turns: {summary.total_turns}")
        print(f"   Active threads: {len(summary.open_threads)}")
        print(f"   Key reactions: {len(summary.key_reactions)}")
        print(f"   Open questions: {len(summary.open_questions)}")
        print(f"   Recent imports: {len(summary.recent_imports)}")
        print(f"   Cognitive state: {summary.cognitive_state}")

        return summary

    async def run_maintenance(self):
        """Run periodic cleanup and maintenance"""

        print(f"\n{'='*60}")
        print(f"RUNNING MAINTENANCE (Turn {self.current_turn})")
        print(f"{'='*60}\n")

        # Entity graph health check
        health = self.entity_cleaner.get_cleanup_summary(self.current_turn)
        print(f"🏥 ENTITY GRAPH HEALTH: {health['health_score']:.2%}")
        print(f"   Total entities: {health['total_entities']}")
        print(f"   Contradictions: {health['total_contradictions']}")
        print(f"   High severity: {health['high_severity_contradictions']}")
        print(f"   Stale: {health['stale_entities']}")

        # Cleanup if needed
        if health['health_score'] < 0.7:
            print("\n⚠️  Health below threshold, running cleanup...")

            conflicts = self.entity_cleaner.analyze_contradictions(self.current_turn)
            for entity_id, entity_conflicts in conflicts.items():
                for conflict in entity_conflicts:
                    if conflict.severity == "high":
                        consolidation = await self.entity_cleaner.consolidate_conflict(
                            conflict,
                            self.current_turn
                        )
                        self.entity_cleaner.apply_consolidation(
                            consolidation,
                            self.current_turn
                        )
                        print(f"   ✓ Consolidated {entity_id}.{conflict.attribute_name}")

    # Helper methods (mock implementations)
    def _extract_entities(self, text: str) -> set:
        # Mock: extract capitalized words
        words = text.split()
        return {w for w in words if w and w[0].isupper()}

    def _extract_keywords(self, text: str) -> set:
        # Mock: extract longer words
        words = text.split()
        return {w.lower() for w in words if len(w) > 5}

    def _extract_questions(self, text: str) -> list:
        # Mock: extract sentences ending with ?
        return [s.strip() + "?" for s in text.split("?")[:-1] if s.strip()]

    def _is_significant_reaction(self, text: str) -> bool:
        # Mock: check for emotional indicators
        emotional_words = {"feel", "think", "realize", "understand", "interesting"}
        return any(word in text.lower() for word in emotional_words)


async def main():
    """
    Example conversation flow demonstrating all features
    """

    manager = ConversationManager()

    # Start session
    session_id = "example_session_001"
    await manager.start_session(session_id)

    # Simulate conversation
    print("\n" + "="*60)
    print("SIMULATED CONVERSATION")
    print("="*60)

    # Turn 1
    await manager.process_turn(
        user_input="I have a dog named [dog]. She's a golden retriever.",
        emotional_state={"joy": 0.7, "curiosity": 0.4}
    )

    # Turn 2
    await manager.process_turn(
        user_input="[dog] loves to play fetch in the park.",
        emotional_state={"joy": 0.8, "excitement": 0.5}
    )

    # Turn 3 - New topic (thread shift)
    await manager.process_turn(
        user_input="What do you think about machine learning?",
        emotional_state={"curiosity": 0.9, "interest": 0.7}
    )

    # Import document
    await manager.import_document(
        document_content="""
        Machine learning is a subset of artificial intelligence that focuses on
        the development of algorithms that can learn from and make predictions on data.
        Common approaches include supervised learning, unsupervised learning, and
        reinforcement learning. Neural networks are a popular ML technique inspired
        by biological neurons.
        """,
        document_description="Overview of machine learning concepts"
    )

    # Turn 4 - Back to [dog] thread
    await manager.process_turn(
        user_input="[dog] also knows several tricks!",
        emotional_state={"joy": 0.6, "pride": 0.7}
    )

    # Run maintenance
    if manager.current_turn % 5 == 0:
        await manager.run_maintenance()

    # End session
    await manager.end_session(session_id)

    print("\n" + "="*60)
    print("EXAMPLE COMPLETE")
    print("="*60)
    print("\nNext session will automatically restore:")
    print("  • Last conversation exchange")
    print("  • Active threads ([dog], Machine Learning)")
    print("  • Entity's reactions")
    print("  • Open questions")
    print("  • Cognitive/emotional state")


if __name__ == "__main__":
    asyncio.run(main())
