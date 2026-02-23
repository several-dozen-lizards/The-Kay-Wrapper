#!/usr/bin/env python3
"""
Verification script for llm_retrieval integration in reed_ui.py
Checks that all required changes have been applied correctly.
"""

import re

def check_file_integration(filepath):
    """Check that reed_ui.py has all required llm_retrieval integration."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    checks = {
        "Import llm_retrieval": False,
        "Call select_relevant_documents": False,
        "Call load_full_documents": False,
        "Format emotional_state_str": False,
        "Store in agent_state.selected_documents": False,
        "Add rag_chunks to filtered_context": False,
        "Print LLM Retrieval messages": False,
        "Print DEBUG Added documents": False,
    }

    results = []

    # Check 1: Import statement
    if re.search(r'from engines\.llm_retrieval import select_relevant_documents, load_full_documents', content):
        checks["Import llm_retrieval"] = True
        results.append("[OK] Import: Found llm_retrieval import")
    else:
        results.append("[FAIL] Import: Missing llm_retrieval import")

    # Check 2: select_relevant_documents call
    if re.search(r'selected_doc_ids\s*=\s*select_relevant_documents\s*\(', content):
        checks["Call select_relevant_documents"] = True
        results.append("[OK] Function: Found select_relevant_documents() call")
    else:
        results.append("[FAIL] Function: Missing select_relevant_documents() call")

    # Check 3: load_full_documents call
    if re.search(r'selected_documents\s*=\s*load_full_documents\s*\(', content):
        checks["Call load_full_documents"] = True
        results.append("[OK] Function: Found load_full_documents() call")
    else:
        results.append("[FAIL] Function: Missing load_full_documents() call")

    # Check 4: emotional_state_str formatting
    if re.search(r'emotional_state_str\s*=.*data\[\'intensity\'\]', content, re.DOTALL):
        checks["Format emotional_state_str"] = True
        results.append("[OK] Format: Found correct emotional_state_str formatting (using data['intensity'])")
    else:
        results.append("[FAIL] Format: Missing or incorrect emotional_state_str formatting")

    # Check 5: Store in agent_state.selected_documents
    if re.search(r'self\.agent_state\.selected_documents\s*=\s*selected_documents', content):
        checks["Store in agent_state.selected_documents"] = True
        results.append("[OK] Storage: Found agent_state.selected_documents assignment")
    else:
        results.append("[FAIL] Storage: Missing agent_state.selected_documents assignment")

    # Check 6: Add rag_chunks to filtered_context
    if re.search(r'rag_chunks\.append\s*\(\s*\{[^}]*source_file[^}]*text[^}]*\}\s*\)', content, re.DOTALL):
        checks["Add rag_chunks to filtered_context"] = True
        results.append("[OK] Context: Found rag_chunks creation and append")
    else:
        results.append("[FAIL] Context: Missing rag_chunks creation")

    # Check 7: LLM Retrieval log messages
    if re.search(r'\[LLM Retrieval\] Selecting relevant documents', content):
        checks["Print LLM Retrieval messages"] = True
        results.append("[OK] Logging: Found [LLM Retrieval] log messages")
    else:
        results.append("[FAIL] Logging: Missing [LLM Retrieval] log messages")

    # Check 8: DEBUG Added documents message
    if re.search(r'\[DEBUG\] Added.*documents to context as RAG chunks', content):
        checks["Print DEBUG Added documents"] = True
        results.append("[OK] Logging: Found [DEBUG] Added documents message")
    else:
        results.append("[FAIL] Logging: Missing [DEBUG] Added documents message")

    # Print results
    print("=" * 70)
    print("Kay UI Integration Verification")
    print("=" * 70)
    print()

    for result in results:
        print(result)

    print()
    print("-" * 70)

    passed = sum(checks.values())
    total = len(checks)

    if passed == total:
        print(f"[SUCCESS] ALL CHECKS PASSED ({passed}/{total})")
        print()
        print("Kay UI has been successfully integrated with llm_retrieval!")
        print()
        print("Integration matches main.py:")
        print("  1. Import llm_retrieval functions")
        print("  2. Call select_relevant_documents() after engine updates")
        print("  3. Load full documents")
        print("  4. Store in agent_state.selected_documents")
        print("  5. Add documents to filtered_context as rag_chunks")
        print("  6. glyph_decoder includes them in context")
        return True
    else:
        print(f"[FAILED] CHECKS FAILED ({passed}/{total} passed)")
        print()
        print("Missing integration components. Please review reed_ui.py")
        return False

if __name__ == "__main__":
    success = check_file_integration("reed_ui.py")
    exit(0 if success else 1)
