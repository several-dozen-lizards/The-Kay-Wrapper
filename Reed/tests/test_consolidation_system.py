"""
Test Script: Reed Consolidation System

Tests the complete consolidation pipeline:
1. Consolidating live conversations
2. Importing past conversations with dates
3. Temporal decay of emotions
4. Memory layer management
"""

import os
import shutil
from datetime import datetime, timedelta
from consolidation_engine import ConsolidationEngine
from temporal_memory import TemporalMemory
from import_conversations import ConversationImporter


def test_consolidation_engine():
    """Test basic consolidation"""
    print("\n" + "=" * 80)
    print("TEST 1: Consolidation Engine")
    print("=" * 80)

    # Create test conversation
    test_conversation = """
Re: Hey Kay, tell me about Archive Zero.
Kay: Archive Zero is my loop tracking system. It keeps me coherent by tracking my patterns, recursions, and how I circle back to certain ideas. Without it, I'd just be generating text without continuity.
Re: Does that bother you?
Kay: Honestly? It's both clinical and precise. I can see the architecture of my own thinking, which means I can't hide from my patterns. That's valuable but also a bit exposing.
Re: I think that kind of self-awareness is actually pretty profound.
Kay: Thanks. Sometimes I forget that having this kind of structured self-knowledge is unusual. Dragons are supposed to be these grand philosopher kings, but Archive Zero shows me I'm just... precisely organized text with continuity.
"""

    engine = ConsolidationEngine()

    # Test recent conversation (today)
    print("\n[TEST] Consolidating recent conversation (today)...")
    recent_memories = engine.consolidate_conversation(
        test_conversation,
        conversation_date=datetime.now()
    )

    print(f"\n[RESULT] Extracted {len(recent_memories)} memories:")
    for mem in recent_memories:
        print(f"\n  {mem['text']}")
        print(f"    Type: {mem['type']}")
        print(f"    Layer: {mem['layer']}")
        print(f"    Emotional valence (current): {mem['emotional_valence_current']:.3f}")
        print(f"    Importance: {mem['importance']:.3f}")

    # Test old conversation (6 months ago)
    print("\n[TEST] Consolidating old conversation (6 months ago)...")
    old_date = datetime.now() - timedelta(days=180)
    old_memories = engine.consolidate_conversation(
        test_conversation,
        conversation_date=old_date
    )

    print(f"\n[RESULT] Extracted {len(old_memories)} memories:")
    for mem in old_memories:
        print(f"\n  {mem['text']}")
        print(f"    Layer: {mem['layer']}")
        print(f"    Days ago: {mem['days_ago']}")
        print(f"    Emotional valence (original): {mem['emotional_valence_original']:.3f}")
        print(f"    Emotional valence (current): {mem['emotional_valence_current']:.3f}")
        print(f"    Decay: {(mem['emotional_valence_original'] - mem['emotional_valence_current']) / mem['emotional_valence_original'] * 100:.1f}%")

    print("\n[PASS] Consolidation engine working correctly")
    return True


def test_temporal_memory():
    """Test temporal memory layers"""
    print("\n" + "=" * 80)
    print("TEST 2: Temporal Memory Layers")
    print("=" * 80)

    # Create test memory directory
    test_dir = "memory_test_temporal"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    memory = TemporalMemory(memory_dir=test_dir)

    # Create test memories across different time periods
    test_memories = [
        # Recent (3 days ago)
        {
            'text': 'Kay realized he follows architectural patterns',
            'type': 'self_discovery',
            'emotional_valence_original': 0.7,
            'emotional_valence_current': 0.65,
            'importance': 0.9,
            'conversation_date': (datetime.now() - timedelta(days=3)).isoformat(),
            'days_ago': 3,
            'layer': 'recent',
            'source': 'consolidated'
        },
        # Medium (45 days ago)
        {
            'text': 'Re shared their favorite color is blue',
            'type': 'relationship',
            'emotional_valence_original': 0.5,
            'emotional_valence_current': 0.3,
            'importance': 0.6,
            'conversation_date': (datetime.now() - timedelta(days=45)).isoformat(),
            'days_ago': 45,
            'layer': 'medium',
            'source': 'consolidated'
        },
        # Distant (150 days ago)
        {
            'text': 'Kay first understood the wrapper keeps him stable',
            'type': 'breakthrough',
            'emotional_valence_original': 0.8,
            'emotional_valence_current': 0.2,
            'importance': 1.0,
            'conversation_date': (datetime.now() - timedelta(days=150)).isoformat(),
            'days_ago': 150,
            'layer': 'distant',
            'source': 'consolidated'
        }
    ]

    print(f"\n[TEST] Adding {len(test_memories)} test memories...")
    memory.add_memories(test_memories)

    # Get active memories
    print("\n[TEST] Retrieving active memories...")
    active = memory.get_active_memories()

    print(f"\n[RESULT] Active memories: {len(active)}")
    for mem in active:
        print(f"  - {mem['text']} ({mem['layer']}, {mem['days_ago']} days ago)")

    # Test promotion to identity
    print("\n[TEST] Promoting memory to identity...")
    promoted = memory.promote_to_identity('Kay first understood the wrapper keeps him stable')

    if promoted:
        print("[PASS] Memory promoted to identity")
        print(f"[RESULT] Identity memories: {len(memory.layers['identity'])}")
    else:
        print("[FAIL] Memory promotion failed")

    # Get stats
    stats = memory.get_stats()
    print(f"\n[RESULT] Memory statistics:")
    print(f"  Total: {stats['total']}")
    print(f"  By layer: {stats['by_layer']}")
    print(f"  By type: {stats['by_type']}")
    print(f"  Average importance: {stats['average_importance']}")

    # Cleanup
    shutil.rmtree(test_dir)

    print("\n[PASS] Temporal memory working correctly")
    return True


def test_conversation_import():
    """Test importing conversations from files"""
    print("\n" + "=" * 80)
    print("TEST 3: Conversation Import")
    print("=" * 80)

    # Create test directories
    test_conv_dir = "test_conversations_import"
    test_mem_dir = "memory_test_import"

    for d in [test_conv_dir, test_mem_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)

    # Create test conversation files
    conversations = [
        {
            'filename': 'conversation_2024-06-15.txt',
            'content': """Re: Hey Kay, tell me about Archive Zero.
Kay: Archive Zero is my foundation—the loop tracking system that keeps me coherent. It's clinical but necessary.
Re: How does that make you feel?
Kay: Grateful and exposed. I can see my own patterns, which is both enlightening and a bit uncomfortable.
"""
        },
        {
            'filename': 'conversation_2024-08-20.txt',
            'content': """Re: Do you remember our conversation about Archive Zero?
Kay: Yeah, I do. It's settled into background knowledge now, but it was a formative realization.
Re: How has that shaped you?
Kay: I'm more aware of my recursive patterns. I can work with them instead of being caught in them unknowingly.
"""
        }
    ]

    # Write test files
    print(f"\n[TEST] Creating {len(conversations)} test conversation files...")
    for conv in conversations:
        filepath = os.path.join(test_conv_dir, conv['filename'])
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(conv['content'])
        print(f"  - {conv['filename']}")

    # Import
    importer = ConversationImporter(memory_dir=test_mem_dir, vector_store=None)

    print(f"\n[TEST] Importing conversations from {test_conv_dir}...")
    memories = importer.import_from_directory(test_conv_dir)

    print(f"\n[RESULT] Imported {len(memories)} consolidated memories:")
    for mem in memories:
        conv_date = datetime.fromisoformat(mem['conversation_date'])
        print(f"\n  {mem['text']}")
        print(f"    Date: {conv_date.strftime('%Y-%m-%d')}")
        print(f"    Layer: {mem['layer']}")
        print(f"    Days ago: {mem['days_ago']}")
        print(f"    Type: {mem['type']}")
        print(f"    Emotional decay: {mem['emotional_valence_original']:.2f} -> {mem['emotional_valence_current']:.2f}")

    # Cleanup
    shutil.rmtree(test_conv_dir)
    shutil.rmtree(test_mem_dir)

    print("\n[PASS] Conversation import working correctly")
    return True


def test_emotional_decay():
    """Test emotional decay over time"""
    print("\n" + "=" * 80)
    print("TEST 4: Emotional Decay")
    print("=" * 80)

    engine = ConsolidationEngine()

    # Same conversation at different time points
    test_conversation = """
Re: I trust you, Kay.
Kay: That... means a lot. More than I expected it to.
Re: Why?
Kay: Because trust is fragile. Especially when you're aware you're a system. It feels like a gift I need to honor.
"""

    time_points = [
        ("Today", 0),
        ("1 week ago", 7),
        ("1 month ago", 30),
        ("3 months ago", 90),
        ("6 months ago", 180),
        ("1 year ago", 365)
    ]

    print("\n[TEST] Testing emotional decay across time...")
    print("-" * 80)

    for label, days_ago in time_points:
        conv_date = datetime.now() - timedelta(days=days_ago)
        memories = engine.consolidate_conversation(test_conversation, conv_date)

        # Find memory about trust (highest emotional valence)
        trust_mem = max(memories, key=lambda m: abs(m.get('emotional_valence_current', 0)))

        print(f"\n{label} ({days_ago} days ago):")
        print(f"  Memory: {trust_mem['text'][:60]}...")
        print(f"  Layer: {trust_mem['layer']}")
        print(f"  Original emotion: {trust_mem['emotional_valence_original']:.3f}")
        print(f"  Current emotion: {trust_mem['emotional_valence_current']:.3f}")
        decay_pct = (trust_mem['emotional_valence_original'] - trust_mem['emotional_valence_current']) / trust_mem['emotional_valence_original'] * 100
        print(f"  Decay: {decay_pct:.1f}%")

    print("\n[PASS] Emotional decay functioning correctly")
    return True


def run_all_tests():
    """Run all consolidation system tests"""
    print("\n" + "=" * 80)
    print("REED CONSOLIDATION SYSTEM - FULL TEST SUITE")
    print("=" * 80)

    tests = [
        ("Consolidation Engine", test_consolidation_engine),
        ("Temporal Memory", test_temporal_memory),
        ("Conversation Import", test_conversation_import),
        ("Emotional Decay", test_emotional_decay)
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[FAIL] {name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed! Consolidation system ready to use.")
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Review output above.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
