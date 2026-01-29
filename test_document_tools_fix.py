"""
Test the fixed document reading tools
"""
import sys
sys.path.insert(0, r"D:\ChristinaStuff\AlphaKayZero")

from kay_document_reader import get_kay_document_tools

# Get the tools (no ChromaDB needed now!)
tools = get_kay_document_tools()

print("=" * 60)
print("TESTING FIXED DOCUMENT TOOLS")
print("=" * 60)

# Test 1: List documents
print("\n[TEST 1] list_documents()")
print("-" * 60)
result = tools['list_documents']()
print(f"Success: {result.get('total_count', 0)} documents found")
if result.get('documents'):
    for doc in result['documents'][:3]:
        print(f"  - {doc['name']} ({doc['word_count']} words)")
else:
    print(f"ERROR: {result.get('error', 'Unknown error')}")

# Test 2: Read a specific document
print("\n[TEST 2] read_document('ChatGPT convo 1.txt')")
print("-" * 60)
result = tools['read_document']('ChatGPT convo 1.txt', max_chars=500)
if result.get('content'):
    print(f"Success: Retrieved {result['word_count']} words")
    print(f"Preview: {result['content'][:200]}...")
else:
    print(f"ERROR: {result.get('error', 'Unknown error')}")

# Test 3: Search within document
print("\n[TEST 3] search_document('ChatGPT convo 1.txt', 'mask')")
print("-" * 60)
result = tools['search_document']('ChatGPT convo 1.txt', 'mask', n_results=3)
if result.get('results'):
    print(f"Success: {result['total_matches']} matches found")
    for i, match in enumerate(result['results'][:2], 1):
        print(f"  Match {i} (line {match['line_number']}): {match['match'][:80]}...")
else:
    print(f"ERROR: {result.get('error', 'Unknown error')}")

print("\n" + "=" * 60)
print("TESTS COMPLETE")
print("=" * 60)
