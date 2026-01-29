"""
Integration Verification Script

Verifies that all emotional system fixes are properly integrated:
1. Emotion trigger expansion in emotion_engine.py
2. Emotion pruning in emotion_engine.py
3. Engine logging in emotion_engine.py
4. Integration logging in kay_ui.py

This script checks the files directly to ensure all changes are present.
"""

import os
import sys

def verify_file_exists(filepath):
    """Check if file exists."""
    if os.path.exists(filepath):
        print(f"[OK] {filepath}")
        return True
    else:
        print(f"[FAIL] {filepath} NOT FOUND")
        return False

def verify_code_present(filepath, search_strings, description):
    """Check if specific code is present in file."""
    print(f"\nVerifying: {description}")
    print(f"File: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        all_found = True
        for search_str in search_strings:
            if search_str in content:
                print(f"  [OK] Found: {search_str[:60]}...")
            else:
                print(f"  [FAIL] Missing: {search_str[:60]}...")
                all_found = False

        return all_found
    except Exception as e:
        print(f"  [ERROR] Could not read file: {e}")
        return False


def main():
    print("="*70)
    print("INTEGRATION VERIFICATION")
    print("="*70)

    results = {}

    # 1. Verify files exist
    print("\n1. Checking files exist...")
    results["emotion_engine.py"] = verify_file_exists("F:\\AlphaKayZero\\engines\\emotion_engine.py")
    results["kay_ui.py"] = verify_file_exists("F:\\AlphaKayZero\\kay_ui.py")
    results["test_emotion_integration.py"] = verify_file_exists("F:\\AlphaKayZero\\test_emotion_integration.py")

    # 2. Verify emotion_engine.py expanded triggers
    print("\n2. Checking emotion trigger expansion...")
    results["trigger_expansion"] = verify_code_present(
        "F:\\AlphaKayZero\\engines\\emotion_engine.py",
        [
            '"amusement": ["funny", "funniest"',  # New emotion with variations
            '"grief": ["miss", "lost"',            # New emotion
            '"frustration": ["frustrated", "frustrating"',  # New emotion
            "text_words = set(text.split())",     # Word-based matching
        ],
        "Emotion trigger expansion (20 emotions, word-based)"
    )

    # 3. Verify emotion_engine.py pruning
    print("\n3. Checking emotion pruning...")
    results["pruning"] = verify_code_present(
        "F:\\AlphaKayZero\\engines\\emotion_engine.py",
        [
            'if cocktail[emo]["intensity"] < 0.05:',
            'print(f"[EMOTION ENGINE] Pruned low-intensity emotions:',
        ],
        "Emotion pruning (removes emotions below 0.05 threshold)"
    )

    # 4. Verify emotion_engine.py logging
    print("\n4. Checking emotion engine logging...")
    results["engine_logging"] = verify_code_present(
        "F:\\AlphaKayZero\\engines\\emotion_engine.py",
        [
            '[EMOTION ENGINE] ========== UPDATE START ==========',
            '[EMOTION ENGINE] Detected triggers:',
            '[EMOTION ENGINE] Aged',
            '[EMOTION ENGINE] Final cocktail:',
            '[EMOTION ENGINE] ========== UPDATE END ==========',
        ],
        "Emotion engine internal logging"
    )

    # 5. Verify kay_ui.py integration logging
    print("\n5. Checking integration logging in kay_ui.py...")
    results["integration_logging"] = verify_code_present(
        "F:\\AlphaKayZero\\kay_ui.py",
        [
            '[EMOTION INTEGRATION] ========== BEFORE EMOTION.UPDATE()',
            '[EMOTION INTEGRATION] ========== AFTER EMOTION.UPDATE()',
            '[EMOTION INTEGRATION] ========== BEFORE UPDATE_EMOTIONS_DISPLAY()',
            '[EMOTION INTEGRATION] ========== AFTER UPDATE_EMOTIONS_DISPLAY()',
            '[EMOTION INTEGRATION] ========== BEFORE MEMORY.ENCODE()',
            '[EMOTION INTEGRATION] ========== AFTER MEMORY.ENCODE()',
        ],
        "Integration logging at all touch points"
    )

    # 6. Verify emotion.update() is called correctly
    print("\n6. Checking emotion.update() call...")
    results["update_call"] = verify_code_present(
        "F:\\AlphaKayZero\\kay_ui.py",
        [
            'self.emotion.update(self.agent_state, user_input)',
        ],
        "Emotion engine update call"
    )

    # Summary
    print("\n" + "="*70)
    print("VERIFICATION RESULTS")
    print("="*70)

    passed = sum(results.values())
    total = len(results)

    for check_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check_name}")

    print(f"\nOVERALL: {passed}/{total} checks passed")

    if passed == total:
        print("\n" + "="*70)
        print("[SUCCESS] All integration verified!")
        print("="*70)
        print("\nAll fixes are properly integrated:")
        print("  - Emotion triggers expanded (6 -> 20 emotions)")
        print("  - Word-based matching (no more exact phrases)")
        print("  - Emotion pruning (removes <0.05 intensity)")
        print("  - Engine logging (shows trigger detection, decay)")
        print("  - Integration logging (catches unexpected modifications)")
        print("\nReady to run: python main.py")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("[WARNING] Some integration checks failed!")
        print("="*70)
        print("\nReview the failures above and ensure:")
        print("  1. emotion_engine.py has all fixes applied")
        print("  2. kay_ui.py has integration logging")
        print("  3. Files are in correct locations")
        print("="*70)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
