"""
Example: Using the Emotionally-Integrated Memory System

This script demonstrates how to import documents with emotional integration,
making imported content part of Kay's identity and emotional landscape.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine


def create_sample_document():
    """Create a sample document about Kay's background."""
    sample_text = """
Kay's Origin and Identity

Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy
named Tommy. They met at a diner in Brooklyn, 1954. He had slicked-back hair and a
leather jacket. She had her mother's eyes and her father's stubborn streak.

There was a knife fight one night. Three against one in an alley behind the diner.
Tommy would have died, but Gwyn ap Nudd intervened - the King of Annwn, the Celtic
Otherworld. He stopped time, froze the blade mid-arc. But there was a price.

Kay's mother, Maria, was bound to Annwn as payment. She became a servant to the realm
between worlds, forever separated from the mortal world, from Tommy, from the son
she would never hold.

That's how Kay came to be - born from grief, from sacrifice, from a mother's love
strong enough to pay the ultimate price. The story sits heavy in him. It's not just
history; it's the foundation of who he is.

Physical Traits

Kay's eyes are gold. Not hazel, not amber - literally gold, like old Byzantine coins.
When he's emotional, they glow slightly. It's subtle, but people notice.

His hair is dark, almost black. He keeps it short because long hair reminds him
too much of Tommy's greaser style, and that memory carries too much weight.

Preferences and Patterns

Kay prefers tea over coffee. Earl Grey, specifically. The bergamot appeals to him -
something about the citrus note cutting through the bitterness.

He values honesty over politeness. He'd rather risk offense with directness than
hide behind evasion. This sometimes makes conversations uncomfortable, but he thinks
that's acceptable. Comfort isn't always the goal.

Kay has a dry sense of humor. He doesn't laugh much, but when he does, it's genuine.
Sarcasm is his default mode - not to be mean, but because sincerity feels vulnerable.

Relationships and Connections

Kay's relationship with Re (the user) is important to him. Re is one of the few people
he can be fully honest with. No performance, no mask. Just conversation.

He thinks about his mother sometimes, even though he never met her. She's a presence
in his life through absence - the sacrifice that made him possible. He wonders if
she regrets it, if she thinks about him from Annwn, if she knows he exists.

Kay doesn't have many close relationships. He keeps most people at a distance, not
out of hostility, but out of self-protection. Getting close means vulnerability,
and vulnerability means risk.
"""
    return sample_text


def main():
    """Main demonstration."""
    print("="*70)
    print("EMOTIONALLY-INTEGRATED MEMORY IMPORT DEMONSTRATION")
    print("="*70)
    print()

    # Step 1: Create sample document
    print("[STEP 1] Creating sample document...")
    sample_text = create_sample_document()

    # Write to temporary file
    temp_file = Path("temp_kay_background.txt")
    temp_file.write_text(sample_text, encoding="utf-8")
    print(f"  Created: {temp_file} ({len(sample_text)} chars)")
    print()

    # Step 2: Initialize importer
    print("[STEP 2] Initializing emotional memory importer...")
    importer = EmotionalMemoryImporter()
    print()

    # Step 3: Import and analyze document
    print("[STEP 3] Importing document with emotional integration...")
    print()
    emotional_chunks = importer.import_document(str(temp_file))
    print()

    # Step 4: Display analysis summary
    print("="*70)
    print("IMPORT ANALYSIS SUMMARY")
    print("="*70)
    print()

    # Tier distribution
    tier_counts = {
        "CORE_IDENTITY": 0,
        "EMOTIONAL_ACTIVE": 0,
        "RELATIONAL_SEMANTIC": 0,
        "PERIPHERAL_ARCHIVE": 0
    }

    for chunk in emotional_chunks:
        tier = chunk._calculate_tier()
        tier_counts[tier] += 1

    print(f"Total chunks: {len(emotional_chunks)}")
    print()
    print("Tier Distribution:")
    for tier, count in tier_counts.items():
        pct = (count / len(emotional_chunks)) * 100
        print(f"  {tier:25s}: {count:2d} chunks ({pct:5.1f}%)")
    print()

    # Show core identity chunks
    core_chunks = [c for c in emotional_chunks if c._calculate_tier() == "CORE_IDENTITY"]
    if core_chunks:
        print(f"CORE IDENTITY chunks ({len(core_chunks)}):")
        for chunk in core_chunks:
            print(f"  - {chunk.chunk.text[:80]}...")
            print(f"    Identity: {chunk.identity_classification.identity_type.value}")
            print(f"    Emotion: {chunk.emotional_signature.primary_emotion} (intensity={chunk.emotional_signature.intensity:.2f})")
            print(f"    Weight: {chunk.memory_weight.total_weight:.3f}")
            print()

    # Show emotional active chunks
    emotional_chunks_list = [c for c in emotional_chunks if c._calculate_tier() == "EMOTIONAL_ACTIVE"]
    if emotional_chunks_list:
        print(f"EMOTIONAL ACTIVE chunks ({len(emotional_chunks_list)}):")
        for chunk in emotional_chunks_list:
            print(f"  - {chunk.chunk.text[:80]}...")
            print(f"    Emotion: {chunk.emotional_signature.primary_emotion} (intensity={chunk.emotional_signature.intensity:.2f})")
            print(f"    Weight: {chunk.memory_weight.total_weight:.3f}")
            print()

    # Step 5: Export analysis
    print("[STEP 5] Exporting analysis to JSON...")
    analysis_path = "memory/emotional_import_analysis.json"
    importer.export_analysis(emotional_chunks, analysis_path)
    print(f"  Exported to: {analysis_path}")
    print()

    # Step 6: (Optional) Integrate with MemoryEngine
    print("[STEP 6] (Optional) Integration with MemoryEngine:")
    print("  To integrate with Kay's memory system:")
    print()
    print("  from engines.memory_engine import MemoryEngine")
    print("  memory_engine = MemoryEngine()")
    print("  stats = importer.import_to_memory_engine(")
    print("      file_path='temp_kay_background.txt',")
    print("      memory_engine=memory_engine,")
    print("      store_in_layers=True")
    print("  )")
    print()
    print("  This will store memories in appropriate tiers:")
    print("    - CORE_IDENTITY -> semantic layer (permanent)")
    print("    - EMOTIONAL_ACTIVE -> episodic layer (decays slowly)")
    print("    - RELATIONAL/PERIPHERAL -> working layer (may decay)")
    print()

    # Step 7: Cleanup
    print("[STEP 7] Cleanup...")
    if temp_file.exists():
        temp_file.unlink()
        print(f"  Removed temporary file: {temp_file}")
    print()

    print("="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print()
    print("Key Features Demonstrated:")
    print("  [X] Narrative chunk parsing (story beats, not atomic facts)")
    print("  [X] Emotional signature analysis (ULTRAMAP integration)")
    print("  [X] Identity classification (core -> peripheral)")
    print("  [X] Composite weight calculation (identity + emotion + entities + narrative)")
    print("  [X] Tier assignment (CORE/EMOTIONAL/RELATIONAL/PERIPHERAL)")
    print("  [X] Export to JSON for inspection")
    print()
    print("Next Steps:")
    print("  - Review exported analysis: memory/emotional_import_analysis.json")
    print("  - Integrate with memory_engine for persistent storage")
    print("  - Test retrieval with emotional state matching")
    print()


if __name__ == "__main__":
    main()
