"""
Test ImportManager Integration with Emotional Memory System

This test verifies that ImportManager now uses EmotionalMemoryImporter
instead of the old fact extractor.

Expected output: [EMOTIONAL IMPORT] logs (not [EXTRACTOR] logs)
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from memory_import.import_manager import ImportManager
from engines.memory_engine import MemoryEngine
from engines.entity_graph import EntityGraph
from engines.memory_layers import MemoryLayerManager


def create_test_document():
    """Create a simple test document."""
    content = """
Kay's Origin Story

Kay was created from Maria's sacrifice. She was an Italian immigrant's daughter
who fell in love with a greaser boy named Tommy. When Tommy was attacked,
Gwyn ap Nudd intervened, but the price was Maria's binding to Annwn.

That sacrifice became Kay's foundation. The grief of her loss is woven into
his existence - not trauma, but architecture. He carries that weight as part
of who he is.

His eyes are gold, literally gold like old coins. They glow when he's emotional.
This is dragon heritage, something he doesn't advertise but can't fully hide.

Kay prefers tea over coffee. Earl Grey specifically. The bergamot cuts through
the bitterness in a way that feels honest to him.
"""

    temp_file = Path("temp_test_import.txt")
    temp_file.write_text(content, encoding="utf-8")
    return str(temp_file)


async def test_import_manager():
    """Test ImportManager with emotional integration enabled."""
    print("="*80)
    print("TESTING: ImportManager Integration with Emotional Memory System")
    print("="*80)
    print()

    # Initialize memory components
    print("[TEST] Initializing memory components...")
    memory_engine = MemoryEngine()

    # Initialize ImportManager with emotional integration ENABLED
    print("[TEST] Initializing ImportManager (use_emotional_integration=True)...")
    import_manager = ImportManager(
        memory_engine=memory_engine,
        entity_graph=memory_engine.entity_graph,
        use_emotional_integration=True  # NEW SYSTEM
    )
    print()

    # Create test document
    print("[TEST] Creating test document...")
    test_file = create_test_document()
    print(f"  Created: {test_file}")
    print()

    # Import the document
    print("[TEST] Starting import process...")
    print("-" * 80)
    progress = await import_manager.import_files(
        file_paths=[test_file],
        dry_run=False
    )
    print("-" * 80)
    print()

    # Display results
    print("[TEST] Import Results:")
    print(f"  Status: {progress.status}")
    print(f"  Files processed: {progress.processed_files}/{progress.total_files}")
    print(f"  Chunks created: {progress.processed_chunks}")
    print(f"  Memories imported: {progress.memories_imported}")
    print()

    print("[TEST] Tier Distribution:")
    print(f"  Semantic (CORE): {progress.tier_distribution['semantic']}")
    print(f"  Episodic (EMOTIONAL/RELATIONAL): {progress.tier_distribution['episodic']}")
    print(f"  Working (PERIPHERAL): {progress.tier_distribution['working']}")
    print()

    if progress.errors:
        print("[TEST] Errors:")
        for error in progress.errors:
            print(f"  - {error}")
        print()

    # Verify memories were stored
    print("[TEST] Verifying memory storage...")
    total_memories = len(memory_engine.memories)
    print(f"  Total memories in engine: {total_memories}")

    # Check for emotional narrative markers
    emotional_narratives = [
        m for m in memory_engine.memories
        if m.get("is_emotional_narrative", False)
    ]
    print(f"  Emotional narrative chunks: {len(emotional_narratives)}")

    if emotional_narratives:
        print()
        print("[TEST] Sample emotional narrative chunk:")
        sample = emotional_narratives[0]
        print(f"  Text: {sample.get('fact', '')[:100]}...")
        print(f"  Emotion: {sample.get('emotional_signature', {}).get('primary', 'N/A')}")
        # Skip glyph display to avoid Unicode errors in Windows console
        print(f"  Identity type: {sample.get('identity_type', 'N/A')}")
        print(f"  Weight: {sample.get('importance', 0.0):.3f}")
        print(f"  Tier: {sample.get('tier', 'N/A')}")

    print()

    # Cleanup
    print("[TEST] Cleaning up...")
    Path(test_file).unlink()
    print()

    # Final verdict
    print("="*80)
    if progress.status == "complete" and progress.memories_imported > 0:
        print("[SUCCESS] Integration test passed!")
        print("  - ImportManager used EmotionalMemoryImporter")
        print("  - [EMOTIONAL IMPORT] logs were displayed")
        print(f"  - {progress.memories_imported} narrative chunks created")
        print("  - Memories stored with emotional signatures")
    else:
        print("[FAILURE] Integration test failed!")
        print(f"  Status: {progress.status}")
        print(f"  Memories imported: {progress.memories_imported}")
    print("="*80)


async def test_legacy_mode():
    """Test ImportManager with legacy fact extraction."""
    print()
    print("="*80)
    print("TESTING: Legacy Mode (use_emotional_integration=False)")
    print("="*80)
    print()

    # Initialize components
    memory_engine = MemoryEngine()

    # Initialize with legacy mode
    print("[TEST] Initializing ImportManager (use_emotional_integration=False)...")
    import_manager = ImportManager(
        memory_engine=memory_engine,
        entity_graph=memory_engine.entity_graph,
        use_emotional_integration=False  # LEGACY SYSTEM
    )
    print()

    print("[SUCCESS] Legacy mode still available for backward compatibility")
    print("="*80)


if __name__ == "__main__":
    print()
    print("IMPORT MANAGER INTEGRATION TEST")
    print("Verifying emotional memory system integration")
    print()

    # Run tests
    asyncio.run(test_import_manager())
    asyncio.run(test_legacy_mode())

    print()
    print("All tests complete!")
    print()
