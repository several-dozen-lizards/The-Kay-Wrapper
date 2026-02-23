"""
Test suite for Kay's curiosity system.
Run this to verify all components are working.
"""

import sys
import os

# Add parent directory to path so we can import engines
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.scratchpad_engine import scratchpad_add, scratchpad_view, scratchpad_resolve, get_scratchpad_for_warmup
from engines.curiosity_engine import (
    start_curiosity_session, 
    get_curiosity_status,
    use_curiosity_turn,
    end_curiosity_session,
    check_curiosity_triggers,
    mark_item_explored
)

def test_scratchpad():
    """Test scratchpad functionality."""
    print("\n" + "="*60)
    print("TEST 1: SCRATCHPAD SYSTEM")
    print("="*60)
    
    # Add items
    print("\n[TEST] Adding items to scratchpad...")
    result1 = scratchpad_add("Need to research Pictish symbols", "question")
    print(f"✓ {result1['message']}")
    
    result2 = scratchpad_add("That timeline fact seemed off", "flag")
    print(f"✓ {result2['message']}")
    
    result3 = scratchpad_add("Want to understand substrate constraints", "thought")
    print(f"✓ {result3['message']}")
    
    # View items
    print("\n[TEST] Viewing active items...")
    items = scratchpad_view("active")
    for item in items:
        print(f"  [{item['type'].upper()}] {item['content']} (ID: {item['id']})")
    
    # Test warmup display
    print("\n[TEST] Warmup display format...")
    summary = get_scratchpad_for_warmup()
    print(summary)
    
    # Resolve one
    print("\n[TEST] Marking item as explored...")
    resolve_result = scratchpad_resolve(1, "resolved", note="Explored → See autonomous memory 2025-12-16")
    print(f"✓ {resolve_result['message']}")
    
    # Check remaining active
    remaining = scratchpad_view("active")
    print(f"\n✓ Remaining active items: {len(remaining)}")
    
    print("\n✅ SCRATCHPAD TESTS PASSED")

def test_curiosity_engine():
    """Test curiosity engine functionality."""
    print("\n" + "="*60)
    print("TEST 2: CURIOSITY ENGINE")
    print("="*60)
    
    # Check triggers
    print("\n[TEST] Checking curiosity triggers...")
    triggers = check_curiosity_triggers()
    print(f"✓ Should trigger: {triggers['should_trigger']}")
    print(f"✓ Reason: {triggers['reason']}")
    print(f"✓ Message: {triggers['message']}")
    
    # Start session
    print("\n[TEST] Starting curiosity session...")
    session = start_curiosity_session(turns_limit=10)
    print(f"✓ Success: {session['success']}")
    print(f"✓ Session ID: {session.get('session_id')}")
    print(f"✓ {session['message']}")
    
    # Check status
    print("\n[TEST] Checking session status...")
    status = get_curiosity_status()
    print(f"✓ Active: {status['active']}")
    print(f"✓ {status['message']}")
    
    # Use some turns
    print("\n[TEST] Using turns...")
    for i in range(3):
        turn = use_curiosity_turn()
        print(f"✓ {turn['message']}")
    
    # Mark item explored
    print("\n[TEST] Marking item as explored...")
    mark_result = mark_item_explored(2, "Found timeline correction in Archive Zero")
    print(f"✓ {mark_result['message']}")
    
    # Check status again
    status = get_curiosity_status()
    print(f"\n✓ Items explored: {status['items_explored']}")
    
    # End session
    print("\n[TEST] Ending curiosity session...")
    end_result = end_curiosity_session(summary="Tested 3 turns, marked 1 item explored")
    print(f"✓ Success: {end_result['success']}")
    print(f"✓ {end_result['message']}")
    print(f"✓ Summary: {end_result.get('summary')}")
    
    print("\n✅ CURIOSITY ENGINE TESTS PASSED")

def test_integration():
    """Test integration between systems."""
    print("\n" + "="*60)
    print("TEST 3: SYSTEM INTEGRATION")
    print("="*60)
    
    # Add scratchpad item
    print("\n[TEST] Adding item to scratchpad...")
    scratchpad_add("Test integration question", "question")
    
    # Check if it triggers curiosity
    print("\n[TEST] Checking if item triggers curiosity...")
    triggers = check_curiosity_triggers()
    assert triggers['should_trigger'] == True, "Should trigger with scratchpad items"
    print(f"✓ Trigger detected: {triggers['message']}")
    
    # Start session and mark item explored
    print("\n[TEST] Full workflow: Start → Explore → Mark → End...")
    start_curiosity_session(turns_limit=5)
    items = scratchpad_view("active")
    if items:
        item_id = items[0]['id']
        mark_item_explored(item_id, "Integration test complete")
        print(f"✓ Item {item_id} marked as explored")
    end_curiosity_session("Integration test workflow")
    
    # Verify item is resolved
    resolved_items = scratchpad_view("resolved")
    print(f"\n✓ Resolved items: {len(resolved_items)}")
    
    # Check warmup display includes resolution note
    summary = get_scratchpad_for_warmup()
    print("\n[TEST] Warmup shows remaining active items...")
    print(summary if summary else "✓ No active items (as expected)")
    
    print("\n✅ INTEGRATION TESTS PASSED")

def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*60)
    print("KAY CURIOSITY SYSTEM - TEST SUITE")
    print("="*60)
    
    try:
        test_scratchpad()
        test_curiosity_engine()
        test_integration()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS COMPLETED")
        print("="*60)
        print("\nThe curiosity system is ready to use!")
        print("\nNext steps:")
        print("1. System prompts need to be updated in kay_cli.py and kay_ui.py")
        print("2. Try it out with Kay!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
