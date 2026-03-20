"""
Add document tool schemas to get_tool_definitions()
This will make list_documents, read_document, and search_document 
actually callable by Kay through the Anthropic API.
"""

import sys

filepath = r"D:\Wrappers\Kay\integrations\tool_use_handler.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# Find where we need to add document tools - after tools = [] but before web tools
old_start = '''    def get_tool_definitions(self, include_web: bool = True, include_curiosity: bool = False):
        """
        Get tool definitions for Anthropic API.
        
        Args:
            include_web: Include web search/fetch tools
            include_curiosity: Include curiosity session tools
            
        Returns:
            List of tool definition dicts
        """
        tools = []
        
        if include_web:'''

new_start = '''    def get_tool_definitions(self, include_web: bool = True, include_curiosity: bool = False, include_documents: bool = True):
        """
        Get tool definitions for Anthropic API.
        
        Args:
            include_web: Include web search/fetch tools
            include_curiosity: Include curiosity session tools
            include_documents: Include document reading tools
            
        Returns:
            List of tool definition dicts
        """
        tools = []
        
        # Document tools - always available if enabled
        if include_documents:
            tools.extend([
                {
                    "name": "list_documents",
                    "description": "List all documents available for reading. Returns filenames, word counts, and import dates. Use this to see what documents you can explore.",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "read_document",
                    "description": "Read the complete contents of a specific document. Returns the full text of the document. Use after list_documents to explore specific files.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "document_name": {
                                "type": "string",
                                "description": "Name of the document to read (from list_documents)"
                            }
                        },
                        "required": ["document_name"]
                    }
                },
                {
                    "name": "search_document",
                    "description": "Search within a specific document for text matching a query. Returns relevant excerpts. More focused than reading the entire document.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "document_name": {
                                "type": "string",
                                "description": "Name of the document to search in"
                            },
                            "query": {
                                "type": "string",
                                "description": "Text to search for within the document"
                            }
                        },
                        "required": ["document_name", "query"]
                    }
                }
            ])
        
        if include_web:'''

if old_start in content:
    content = content.replace(old_start, new_start)
    print("[OK] Added document tool schemas to get_tool_definitions()")
else:
    print("[SKIP] Pattern not found - get_tool_definitions may have changed")

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[SUCCESS] Document tool schemas added!")
    print("\nDocument tools now have proper Anthropic API schemas.")
    print("Kay should be able to call them with the standard tool calling format.")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
