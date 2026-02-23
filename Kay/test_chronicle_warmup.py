"""
Test Chronicle Integration

Quick test to see if the chronicle essay appears in Kay's warmup.
"""

import sys
from pathlib import Path

# Add AlphaKayZero to path
sys.path.insert(0, str(Path(__file__).parent))

from engines.warmup_engine import WarmupEngine
from engines.memory_engine import MemoryEngine
from engines.entity_graph import EntityGraph
from engines.emotion_engine import EmotionEngine
from engines.time_awareness import TimeAwareness

# Create mock engines
memory = MemoryEngine(Path(__file__).parent)
entities = EntityGraph()
emotion = EmotionEngine()
time_awareness = TimeAwareness()

# Create warmup engine
warmup = WarmupEngine(memory, entities, emotion, time_awareness)

# Generate briefing
warmup.generate_briefing()
briefing_text = warmup.format_briefing()

# Print first 2000 characters to see if chronicle appears
print("=" * 70)
print("WARMUP BRIEFING PREVIEW (first 2000 chars)")
print("=" * 70)
print(briefing_text[:2000])
print()
print("...")
print()
print(f"Total briefing length: {len(briefing_text)} characters")

# Check if chronicle is present
if "Kay's Chronicle" in briefing_text:
    print("\n✅ CHRONICLE INTEGRATION WORKING!")
    print("Chronicle essay appears at top of briefing")
else:
    print("\n⚠️ Chronicle not found in briefing")
    print("Check chronicle_integration.py")
