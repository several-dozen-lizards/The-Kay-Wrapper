#!/usr/bin/env python3
"""
COMPLETE REED TRANSFORMATION - Full visual and identity overhaul
Organizes assets, applies theme, fixes header, clears identity
"""

import subprocess
import sys

def run_script(script_name, description):
    """Run a Python script and report results"""
    print(f"\n{'=' * 60}")
    print(f"STEP: {description}")
    print('=' * 60)
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        if result.returncode == 0:
            print(f"✓ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("🐍 COMPLETE REED TRANSFORMATION 🐍")
    print("=" * 60)
    print()
    print("This will transform Kay's wrapper into Reed's:")
    print()
    print("  VISUAL CHANGES:")
    print("    • Organize Reed's custom panel/border assets")
    print("    • Apply Serpent color theme (ocean teals, warm golds)")
    print("    • Update header text and branding")
    print()
    print("  IDENTITY CHANGES:")
    print("    • Clear Kay's identity memory (backed up safely)")
    print("    • Let Reed build her own identity from scratch")
    print()
    input("Press Enter to begin transformation...")
    
    steps = [
        ("organize_reed_assets.py", "Organize Reed's Visual Assets"),
        ("apply_complete_reed_theme.py", "Apply Complete Reed Theme"),
        ("fix_header.py", "Fix Visual Header"),
        ("clear_identity_for_reed.py", "Clear Identity Memory"),
    ]
    
    results = []
    for script, desc in steps:
        success = run_script(script, desc)
        results.append((desc, success))
    
    print("\n" + "=" * 60)
    print("TRANSFORMATION SUMMARY")
    print("=" * 60)
    
    for desc, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {desc}")
    
    all_success = all(success for _, success in results)
    
    print()
    if all_success:
        print("🐍✨ REED IS READY ✨🐍")
        print()
        print("Visual identity:")
        print("  🌊 Ocean teal depths")
        print("  💎 Iridescent scale shimmer")
        print("  🌅 Warm gold accents")
        print("  🎨 Custom Reed panels & borders")
        print()
        print("Launch with: python reed_ui.py")
    else:
        print("⚠️  Some steps failed - check output above")
    print("=" * 60)

if __name__ == "__main__":
    main()
