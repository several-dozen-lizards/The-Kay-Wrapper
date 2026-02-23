#!/usr/bin/env python3
"""
Verify all Kay->Reed conversions are complete
"""
import re
from pathlib import Path

def check_file(filepath, report):
    """Check a file for remaining Kay references"""
    if not Path(filepath).exists():
        report.append(f"⚠️  {filepath} - FILE NOT FOUND")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    issues = []
    
    # Check for Kay references (case-sensitive)
    patterns = [
        (r'\bkay_document_reader\b', 'Module import: kay_document_reader'),
        (r'\bkay_scratchpad_tools\b', 'Module import: kay_scratchpad_tools'),
        (r'\bget_kay_document_tools\b', 'Function: get_kay_document_tools'),
        (r'\bget_kay_scratchpad_tools\b', 'Function: get_kay_scratchpad_tools'),
        (r'\bKAY_SYSTEM_PROMPT\b', 'Variable: KAY_SYSTEM_PROMPT'),
        (r'\bKayApp\b', 'Class: KayApp'),
        (r'\bread_document_for_kay\b', 'Function: read_document_for_kay'),
        (r'\"kay\"', 'String: "kay"'),
        (r'kay_documents', 'Collection name: kay_documents'),
    ]
    
    for pattern, description in patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"  - {description} (found {len(matches)}x)")
    
    if issues:
        report.append(f"\n❌ {filepath}:")
        report.extend(issues)
    else:
        report.append(f"✅ {filepath}")

def main():
    print("=" * 60)
    print("VERIFYING KAY->REED CONVERSION")
    print("=" * 60)
    print()
    
    report = []
    
    files_to_check = [
        'reed_ui.py',
        'reed_document_reader.py',
        'reed_scratchpad_tools.py',
        'reed_cli.py',
    ]
    
    for filepath in files_to_check:
        check_file(filepath, report)
    
    print("\n".join(report))
    print()
    print("=" * 60)
    
    # Count issues
    issue_count = sum(1 for line in report if line.startswith("❌"))
    if issue_count == 0:
        print("✅ ALL FILES VERIFIED - NO KAY REFERENCES FOUND")
    else:
        print(f"⚠️  {issue_count} FILE(S) STILL HAVE KAY REFERENCES")
    print("=" * 60)

if __name__ == "__main__":
    main()
