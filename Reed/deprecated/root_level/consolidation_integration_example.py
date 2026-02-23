"""
Integration Example: Reed Consolidation System

Shows how to integrate the consolidation system with Reed's main conversation loop.
"""

from datetime import datetime
from consolidation_engine import ConsolidationEngine
from temporal_memory import TemporalMemory
from import_conversations import ConversationImporter


class KayConsolidationSystem:
    """
    Integrates consolidation with Reed's main system.

    Usage:
        kay = KayConsolidationSystem()

        # Wake up (load memories)
        kay.wake_up()

        # Live conversation
        kay.process_turn("user input", "kay response")
        # ... more turns ...

        # Sleep (consolidate session)
        kay.sleep()
    """

    def __init__(self, memory_dir="memory"):
        """Initialize consolidation system"""
        # Import Reed's existing LLM client
        try:
            from integrations.llm_integration import query_llm_json
            llm_client = None  # ConsolidationEngine will use query_llm_json directly
        except ImportError:
            print("[WARNING] Could not import LLM integration, consolidation will use fallback")
            llm_client = None

        # Import Reed's existing vector store
        try:
            from engines.vector_store import VectorStore
            vector_store = VectorStore(persist_directory=f"{memory_dir}/vector_db")
        except ImportError:
            print("[WARNING] Could not import VectorStore, RAG archival disabled")
            vector_store = None

        self.consolidation = ConsolidationEngine(llm_client)
        self.memory = TemporalMemory(memory_dir=memory_dir)
        self.importer = ConversationImporter(
            llm_client=llm_client,
            memory_dir=memory_dir,
            vector_store=vector_store
        )

        self.current_session_transcript = []
        self.session_start_time = None

    def wake_up(self):
        """
        Kay 'wakes up' - load consolidated memories.

        Returns:
            List of active memories for context
        """
        print("\n" + "=" * 60)
        print("[KAY WAKES]")
        print("=" * 60)

        # Age existing memories (update layers based on time passage)
        self.memory.age_memories()

        # Get active memories
        active_memories = self.memory.get_active_memories()

        print(f"[KAY] Loaded {len(active_memories)} consolidated memories")

        # Show distribution
        by_layer = {'recent': 0, 'medium': 0, 'distant': 0, 'identity': 0}
        for mem in active_memories:
            layer = mem.get('layer', mem.get('category', 'unknown'))
            if 'identity' in str(layer):
                by_layer['identity'] += 1
            elif layer in by_layer:
                by_layer[layer] += 1

        print(f"[KAY] Distribution:")
        print(f"  - Identity: {by_layer['identity']}")
        print(f"  - Recent (0-7 days): {by_layer['recent']}")
        print(f"  - Medium (7-90 days): {by_layer['medium']}")
        print(f"  - Distant (90+ days): {by_layer['distant']}")

        self.session_start_time = datetime.now()

        return active_memories

    def process_turn(self, user_input: str, reed_response: str):
        """
        Store current conversation turn.

        Args:
            user_input: What the user said
            reed_response: Reed's response
        """
        self.current_session_transcript.append({
            'user': user_input,
            'kay': reed_response,
            'timestamp': datetime.now().isoformat()
        })

    def sleep(self):
        """
        Kay 'sleeps' - consolidate session into essence memories.

        Returns:
            List of consolidated memories from this session
        """
        if not self.current_session_transcript:
            print("[KAY SLEEPS] No conversation to consolidate")
            return []

        print("\n" + "=" * 60)
        print("[KAY SLEEPS] Consolidating session memories...")
        print("=" * 60)

        # Build transcript text
        transcript = self._build_transcript_text()

        print(f"[CONSOLIDATION] Session length: {len(transcript)} characters")
        print(f"[CONSOLIDATION] Turns: {len(self.current_session_transcript)}")

        # Consolidate
        memories = self.consolidation.consolidate_conversation(
            transcript,
            conversation_date=self.session_start_time or datetime.now()
        )

        # Store
        self.memory.add_memories(memories)

        # Archive full transcript to RAG (if available)
        if self.importer.vector_store:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            source_name = f"session_{session_id}"

            result = self.importer.vector_store.add_document(
                text=transcript,
                source_file=source_name,
                metadata={
                    'session_start': self.session_start_time.isoformat() if self.session_start_time else None,
                    'session_end': datetime.now().isoformat(),
                    'turn_count': len(self.current_session_transcript),
                    'source_type': 'live_session'
                }
            )

            if result.get('status') == 'success':
                print(f"[RAG] Archived session: {result.get('chunks_created', 0)} chunks")

        print(f"\n[CONSOLIDATION] Extracted {len(memories)} memories:")
        for mem in memories:
            print(f"  - {mem['text']} ({mem['type']}, importance: {mem['importance']:.2f})")

        # Clear session
        self.current_session_transcript = []
        self.session_start_time = None

        return memories

    def batch_import_conversations(self, directory: str):
        """
        Import multiple past conversations.

        Args:
            directory: Directory containing conversation files

        Returns:
            List of all consolidated memories
        """
        print("\n" + "=" * 60)
        print("[BATCH IMPORT]")
        print("=" * 60)

        memories = self.importer.import_from_directory(directory)

        return memories

    def import_single_conversation(self, filepath: str, conversation_date=None):
        """
        Import a single past conversation.

        Args:
            filepath: Path to conversation file
            conversation_date: When conversation happened (optional)

        Returns:
            List of consolidated memories
        """
        return self.importer.import_single_file(filepath, conversation_date)

    def _build_transcript_text(self) -> str:
        """Convert session turns into readable transcript"""
        lines = []
        for turn in self.current_session_transcript:
            lines.append(f"Re: {turn['user']}")
            lines.append(f"Kay: {turn['kay']}")
            lines.append("")
        return "\n".join(lines)

    def get_memory_stats(self):
        """Get statistics about current memory state"""
        return self.memory.get_stats()

    def promote_to_identity(self, memory_text: str):
        """Promote a memory to core identity"""
        return self.memory.promote_to_identity(memory_text)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_live_conversation():
    """Example: Live conversation with consolidation"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Live Conversation with Consolidation")
    print("=" * 80)

    # Initialize
    kay = KayConsolidationSystem()

    # Wake up
    active_memories = kay.wake_up()

    # Simulate conversation
    print("\n[CONVERSATION START]")
    print("-" * 80)

    turns = [
        ("Hey Kay, tell me about your memory system", "I have consolidated memories..."),
        ("How do old memories feel different?", "Old memories have a settled quality..."),
        ("That's interesting", "Yeah, it helps me maintain continuity...")
    ]

    for user_input, reed_response in turns:
        print(f"\nRe: {user_input}")
        print(f"Kay: {reed_response}")
        kay.process_turn(user_input, reed_response)

    print("\n" + "-" * 80)
    print("[CONVERSATION END]")

    # Sleep (consolidate)
    memories = kay.sleep()

    print(f"\n[RESULT] Session consolidated into {len(memories)} memories")


def example_batch_import():
    """Example: Batch import past conversations"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Batch Import Past Conversations")
    print("=" * 80)

    # Initialize
    kay = KayConsolidationSystem()

    # Import past conversations
    # memories = kay.batch_import_conversations("./past_conversations/")

    print("\n[NOTE] To actually run batch import:")
    print("  1. Create a directory: ./past_conversations/")
    print("  2. Add conversation files: conversation_YYYY-MM-DD.txt")
    print("  3. Run: kay.batch_import_conversations('./past_conversations/')")
    print("\n[RESULT] All past conversations will be:")
    print("  - Consolidated into 3-5 essence memories each")
    print("  - Dated appropriately based on filename")
    print("  - Emotionally decayed based on age")
    print("  - Archived to RAG for detail retrieval")


def example_integration_with_main_loop():
    """Example: Integration with Reed's main conversation loop"""
    print("\n" + "=" * 80)
    print("EXAMPLE: Integration with Main Loop")
    print("=" * 80)

    print("""
# In your main.py, add:

from consolidation_integration_example import KayConsolidationSystem

async def main():
    # ... existing initialization ...

    # NEW: Initialize consolidation system
    consolidation = KayConsolidationSystem()

    # NEW: Wake up (load consolidated memories)
    active_memories = consolidation.wake_up()

    # Use active_memories in your context building
    # They contain essence of past conversations

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit"):
            # NEW: Sleep before exiting (consolidate session)
            consolidation.sleep()
            break

        # ... existing turn processing ...

        # NEW: Store turn for consolidation
        consolidation.process_turn(user_input, reply)

        # ... rest of existing code ...

    print("Kay: *sleeps, consolidating today's conversation into memory*")
""")


if __name__ == "__main__":
    # Run examples
    example_live_conversation()
    example_batch_import()
    example_integration_with_main_loop()
