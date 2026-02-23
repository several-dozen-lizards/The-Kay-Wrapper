#!/usr/bin/env python3
"""
Clear Reed's identity memory and prepare for Reed
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

def backup_and_clear():
    memory_dir = Path("memory")
    
    # Files to clear/reset
    identity_files = [
        "identity_memory.json",
        "identity.json",
        "identity_index.json"
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in identity_files:
        filepath = memory_dir / filename
        if not filepath.exists():
            print(f"⚠️  {filename} doesn't exist, skipping")
            continue
        
        # Backup
        backup_path = memory_dir / f"{filename}.kay_backup_{timestamp}"
        shutil.copy(filepath, backup_path)
        print(f"✓ Backed up {filename} → {backup_path.name}")
        
        # Read current
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clear Reed's identity
        if filename == "identity_memory.json":
            # Keep structure but clear Kay facts
            data = {
                "re": [],
                "kay": [],  # Clear Kay's facts
                "reed": []  # Add Reed section
            }
        elif filename == "identity.json":
            # Clear all identity data
            data = {}
        elif filename == "identity_index.json":
            # Clear index
            data = {}
        
        # Write cleared version
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Cleared {filename}")
    
    print()
    print("=" * 60)
    print("✅ IDENTITY MEMORY CLEARED")
    print("=" * 60)
    print()
    print("Kay's identity has been backed up and cleared.")
    print("Reed will now build her own identity from scratch.")
    print()
    print("Backups saved with timestamp:", timestamp)
    print()
    print("Now launch Reed: python reed_ui.py")

if __name__ == "__main__":
    backup_and_clear()
