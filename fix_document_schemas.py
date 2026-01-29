"""
Add document tool schemas to get_tool_definitions() - CORRECTED
"""

import sys

filepath = r"D:\ChristinaStuff\AlphaKayZero\integrations\tool_use_handler.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# Correct pattern with actual defaults
old_def = '''    def get_tool_definitions(self, include_web: bool = True, include_curiosity: bool = True) -> List[Dict]:'''

new_def = '''    def get_tool_definitions(self, include_web: bool = True, include_curiosity: bool = True, include_documents: bool = True) -> List[Dict]:'''

if old_def in content:
    content = content.replace(old_def, new_def)
    print("[OK] Updated method signature")
else:
    print("[SKIP] Method signature not found")

# Now add document tools after tools = []
old_tools_start = '''        """
        tools = []
        
        if include_web:'''

new_tools_start = '''        """
        tools = []
        
        # Document tools - for reading imported documents
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
                            "filename": {
                                "type": "string",
                                "description": "Name of the document to read (from list_documents)"
                            }
                        },
                        "required": ["filename"]
                    }
                },
                {
                    "name": "search_document",
                    "description": "Search within a specific document for text matching a query. Returns relevant excerpts. More focused than reading the entire document.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name of the document to search in"
                            },
                            "query": {
                                "type": "string",
                                "description": "Text to search for within the document"
                            }
                        },
                        "required": ["filename", "query"]
                    }
                }
            ])
        
        if include_web:'''

if old_tools_start in content:
    content = content.replace(old_tools_start, new_tools_start)
    print("[OK] Added document tool schemas")
else:
    print("[SKIP] tools initialization not found")

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] Document tools now have proper Anthropic API schemas!")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
