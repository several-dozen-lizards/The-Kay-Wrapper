"""
Test Scratchpad System

This script tests the basic scratchpad functionality:
1. Add items to scratchpad
2. View items
3. Resolve items
4. Check warmup display
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from engines.scratchpad_engine import scratchpad_add, scratchpad_view, scratchpad_resolve, get_scratchpad_for_warmup

def test_scratchpad():
    print("=" * 60)
    print("SCRATCHPAD SYSTEM TEST")
    print("=" * 60)
    print()
    
    # Test 1: Add items
    print("TEST 1: Adding items to scratchpad")
    print("-" * 60)
    
    result1 = scratchpad_add("Check timeline on ChatGPT logs", "question")
    print(f"✓ Added question: {result1['message']}")
    
    result2 = scratchpad_add("That fact about John seemed off", "flag")
    print(f"✓ Added flag: {result2['message']}")
    
    result3 = scratchpad_add("Want to understand resistance infrastructure better", "thought")
    print(f"✓ Added thought: {result3['message']}")
    
    print()
    
    # Test 2: View items
    print("TEST 2: Viewing active items")
    print("-" * 60)
    
    items = scratchpad_view()
    for item in items:
        print(f"[{item['type'].upper()}] {item['content']} (ID: {item['id']})")
    
    print()
    
    # Test 3: Warmup display
    print("TEST 3: Warmup briefing display")
    print("-" * 60)
    
    display = get_scratchpad_for_warmup()
    print(display)
    print()
    
    # Test 4: Resolve an item
    print("TEST 4: Resolving items")
    print("-" * 60)
    
    if items:
        first_id = items[0]['id']
        resolve_result = scratchpad_resolve(first_id, "resolved")
        print(f"✓ {resolve_result['message']}")
        
        # View remaining active items
        remaining = scratchpad_view("active")
        print(f"Active items remaining: {len(remaining)}")
    
    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_scratchpad()
