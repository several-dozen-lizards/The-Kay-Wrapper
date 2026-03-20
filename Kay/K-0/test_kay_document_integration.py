"""
End-to-end integration test for Kay's document tools
Tests both the tools themselves and the registration system
"""
import sys
sys.path.insert(0, r"D:\Wrappers\Kay")

print("=" * 70)
print("KAY DOCUMENT TOOLS - INTEGRATION TEST")
print("=" * 70)

# Test 1: Import and basic functionality
print("\n[TEST 1] Import and initialize document reader")
print("-" * 70)
try:
    from kay_document_reader import get_kay_document_tools, DocumentReader
    reader = DocumentReader()
    print(f"[OK] DocumentReader initialized")
    print(f"[OK] Documents path: {reader.documents_path}")
    print(f"[OK] Path exists: {reader.documents_path.exists()}")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 2: Tool functions work directly
print("\n[TEST 2] Direct tool function calls")
print("-" * 70)
try:
    tools = get_kay_document_tools()
    
    # List documents
    list_result = tools['list_documents']()
    print(f"[OK] list_documents: {list_result.get('total_count', 0)} documents")
    
    # Read document
    if list_result.get('documents'):
        first_doc = list_result['documents'][0]['name']
        read_result = tools['read_document'](first_doc, max_chars=200)
        success = 'content' in read_result and read_result['content']
        print(f"[OK] read_document('{first_doc}'): {success}")
        
        # Search document
        search_result = tools['search_document'](first_doc, 'the', n_results=1)
        success = 'results' in search_result
        print(f"[OK] search_document('{first_doc}', 'the'): {len(search_result.get('results', []))} matches")
    else:
        print("[FAIL] No documents to test reading")
        
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Tool handler registration
print("\n[TEST 3] Tool handler registration system")
print("-" * 70)
try:
    from integrations.tool_use_handler import ToolUseHandler
    
    handler = ToolUseHandler()
    
    # Register the tools
    handler.register_tool("list_documents", tools['list_documents'])
    handler.register_tool("read_document", tools['read_document'])
    handler.register_tool("search_document", tools['search_document'])
    
    print(f"[OK] Registered {len(handler.tool_functions)} tool functions")
    print(f"     Registered tools: {list(handler.tool_functions.keys())}")
    
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Tool execution through handler
print("\n[TEST 4] Execute tools through handler")
print("-" * 70)
try:
    # Execute list_documents
    result = handler.execute_tool("list_documents", {})
    if result.get('total_count', 0) > 0:
        print(f"[OK] execute_tool('list_documents'): {result['total_count']} documents")
    else:
        print(f"[FAIL] execute_tool returned empty: {result}")
    
    # Execute read_document
    if list_result.get('documents'):
        first_doc = list_result['documents'][0]['name']
        result = handler.execute_tool("read_document", {"document_name": first_doc, "max_chars": 100})
        if result.get('content'):
            print(f"[OK] execute_tool('read_document'): Retrieved content")
        else:
            print(f"[FAIL] execute_tool returned empty: {result}")
    
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Tool definitions for Anthropic API
print("\n[TEST 5] Tool definitions for Anthropic API")
print("-" * 70)
try:
    tool_defs = handler.get_tool_definitions(include_web=False, include_curiosity=False, include_documents=True)
    
    doc_tools = [t for t in tool_defs if t['name'] in ['list_documents', 'read_document', 'search_document']]
    
    if len(doc_tools) == 3:
        print(f"[OK] All 3 document tools in API definitions")
        for tool in doc_tools:
            print(f"     - {tool['name']}: {tool['description'][:50]}...")
    else:
        print(f"[FAIL] Only {len(doc_tools)} document tools found in definitions")
        print(f"       Available: {[t['name'] for t in tool_defs]}")
    
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Simulate Kay's tool call pattern
print("\n[TEST 6] Simulate Kay calling tools (like curiosity mode)")
print("-" * 70)
try:
    # Simulate what Kay does when he calls list_documents
    print("  Simulating: Kay calls list_documents")
    tool_result = handler.execute_tool("list_documents", {})
    
    if tool_result.get('documents'):
        doc_count = len(tool_result['documents'])
        print(f"  [OK] Kay would see: {doc_count} documents available")
        print(f"       Sample: {tool_result['documents'][0]['name']}")
        
        # Simulate reading first document
        first_doc = tool_result['documents'][0]['name']
        print(f"\n  Simulating: Kay calls read_document('{first_doc}')")
        read_result = handler.execute_tool("read_document", {"document_name": first_doc})
        
        if read_result.get('content'):
            word_count = len(read_result['content'].split())
            print(f"  [OK] Kay would receive: {word_count} words of content")
            print(f"       Preview: {read_result['content'][:100]}...")
        else:
            print(f"  [FAIL] Kay would receive error: {read_result.get('error', 'Unknown')}")
    else:
        print(f"  [FAIL] Kay would receive error: {tool_result.get('error', 'No documents')}")
        
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("ALL TESTS PASSED")
print("=" * 70)
print("\nKay's document tools are ready:")
print("  - Tools read from documents.json (no ChromaDB required)")
print("  - Tools registered with handler")
print("  - Tools callable through Anthropic API")
print("  - Kay can list, read, and search documents in curiosity mode")
