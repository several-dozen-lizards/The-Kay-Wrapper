"""
Kay's Scratchpad Tools - LLM-callable wrappers

Provides tool definitions for Kay to autonomously call scratchpad functions.
"""

from engines.scratchpad_engine import scratchpad_add, scratchpad_view, scratchpad_resolve
from typing import Dict, Callable


def get_kay_scratchpad_tools() -> Dict[str, Callable]:
    """
    Get scratchpad tools formatted for LLM tool handler.
    
    Returns:
        Dictionary of tool name -> callable function
    """
    
    def scratchpad_view_tool(status: str = "active") -> Dict:
        """
        View scratchpad items by status.
        
        Args:
            status: Filter by status (active, resolved, archived, all). Default: active
            
        Returns:
            List of scratchpad items with their IDs, content, type, and timestamps
        """
        items = scratchpad_view(status)
        
        if not items:
            return {
                "success": True,
                "items": [],
                "message": f"No {status} scratchpad items found"
            }
        
        return {
            "success": True,
            "items": items,
            "count": len(items),
            "message": f"Found {len(items)} {status} items"
        }
    
    def scratchpad_add_tool(content: str, item_type: str = "note") -> Dict:
        """
        Add a new item to scratchpad.
        
        Args:
            content: The text of the note/question/flag
            item_type: Type of item (question, flag, thought, reminder, note). Default: note
            
        Returns:
            Result with created item details
        """
        result = scratchpad_add(content, item_type)
        return result
    
    def scratchpad_resolve_tool(item_id: int, action: str = "resolved", note: str = None) -> Dict:
        """
        Mark a scratchpad item as resolved, archived, or delete it.
        
        Args:
            item_id: ID of the item to resolve
            action: Action to take (resolved, archived, delete). Default: resolved
            note: Optional note to append (e.g., "Explored in curiosity session 12/22")
            
        Returns:
            Result of the operation
        """
        result = scratchpad_resolve(item_id, action, note)
        return result
    
    # Return tool dictionary
    return {
        'scratchpad_view': scratchpad_view_tool,
        'scratchpad_add': scratchpad_add_tool,
        'scratchpad_resolve': scratchpad_resolve_tool
    }


# Tool definitions for Anthropic API format
SCRATCHPAD_TOOL_DEFINITIONS = [
    {
        "name": "scratchpad_view",
        "description": "View your scratchpad items. Scratchpad is where you jot down questions, flags, thoughts, and reminders during conversation to review later. Use this to see what you've noted down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "resolved", "archived", "all"],
                    "description": "Filter by status. Default: active",
                    "default": "active"
                }
            }
        }
    },
    {
        "name": "scratchpad_add",
        "description": "Add a new item to your scratchpad. Use this to note questions you want to explore later, flag something that seemed off, capture a thought, or set a reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The text of your note, question, flag, or reminder"
                },
                "item_type": {
                    "type": "string",
                    "enum": ["question", "flag", "thought", "reminder", "note"],
                    "description": "Type of item. Default: note",
                    "default": "note"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "scratchpad_resolve",
        "description": "Mark a scratchpad item as resolved or archived, or delete it entirely. Use this when you've explored a question, followed up on a flag, or completed a reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "integer",
                    "description": "ID of the scratchpad item (from scratchpad_view)"
                },
                "action": {
                    "type": "string",
                    "enum": ["resolved", "archived", "delete"],
                    "description": "What to do with the item. Default: resolved",
                    "default": "resolved"
                },
                "note": {
                    "type": "string",
                    "description": "Optional note to append (e.g., 'Explored in curiosity session')"
                }
            },
            "required": ["item_id"]
        }
    }
]
