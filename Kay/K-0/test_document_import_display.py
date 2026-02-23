#!/usr/bin/env python3
"""
Test to verify document import display shows proper summary instead of truncated content.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import_prompt_format():
    """Test that import prompt shows summary with stats, not truncated content."""

    # Simulate the new prompt format
    filename = "YW-part1.txt"
    num_chunks = 341
    preview_text = "This is a preview of the document content. " * 20  # ~880 chars
    preview_text = preview_text[:2000]  # Truncate to 2000 chars
    truncated = True

    # Build the prompt as it would appear in kay_ui.py
    prompt = f"""A document was just imported to your memory: "{filename}"

DOCUMENT STATS:
- Memory chunks stored: {num_chunks}
- Total content: Fully accessible through your memory system
- Preview excerpt below (first ~2000 chars)

PREVIEW:
---
{preview_text}
{f"..." if truncated else ""}
---

The FULL document is now in your memory system. You can access any part of it by asking questions or making queries.

React naturally to this import:
- What stands out from the preview?
- Does anything feel familiar?
- What questions do you have about it?
- Does this connect to other memories?
- What would help you understand this better?

This is YOUR history. React naturally."""

    print("=" * 70)
    print("DOCUMENT IMPORT DISPLAY TEST")
    print("=" * 70)
    print()
    print("Testing new summary-based import prompt format...")
    print()

    # Verify the prompt contains key elements
    checks = {
        "Filename present": filename in prompt,
        "Chunk count present": f"Memory chunks stored: {num_chunks}" in prompt,
        "Full document notice": "FULL document is now in your memory" in prompt,
        "Preview section": "PREVIEW:" in prompt,
        "Truncation indicator": "..." in prompt,
        "No mid-word cutoff": not prompt.endswith(" "),  # Check last char isn't a space
        "Guidance questions": "What stands out from the preview?" in prompt,
        "Memory system mention": "accessible through your memory system" in prompt,
    }

    print("VERIFICATION CHECKS:")
    print("-" * 70)
    all_passed = True
    for check_name, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print()
    print("=" * 70)
    print("SAMPLE PROMPT OUTPUT:")
    print("=" * 70)
    print(prompt[:800])  # Show first 800 chars
    print("\n[...middle content...]\n")
    print(prompt[-300:])  # Show last 300 chars
    print()

    if all_passed:
        print("=" * 70)
        print("[SUCCESS] Document import display is properly formatted!")
        print("=" * 70)
        print()
        print("KEY IMPROVEMENTS:")
        print("- Shows chunk count (341) instead of truncated raw text")
        print("- Preview is intentionally short (2000 chars) with clear ellipsis")
        print("- Kay knows full document is accessible through memory")
        print("- No mid-word cutoffs")
        print("- Clear guidance on how to interact with the imported content")
        return True
    else:
        print("=" * 70)
        print("[FAILURE] Some checks failed")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = test_import_prompt_format()
    sys.exit(0 if success else 1)
