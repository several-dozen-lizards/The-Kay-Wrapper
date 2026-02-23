"""
Curiosity engine - manages autonomous exploration sessions for Reed.
Provides triggers, turn tracking, and coordination between scratchpad and autonomous memory.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

CURIOSITY_STATE_FILE = "memory/curiosity_state.json"

def init_curiosity_state():
    """Initialize curiosity state file if it doesn't exist."""
    if not os.path.exists(CURIOSITY_STATE_FILE):
        os.makedirs(os.path.dirname(CURIOSITY_STATE_FILE), exist_ok=True)
        state = {
            "active": False,
            "session_id": None,
            "turns_used": 0,
            "turns_limit": 15,
            "started_at": None,
            "items_explored": []
        }
        with open(CURIOSITY_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return state
    
    with open(CURIOSITY_STATE_FILE, 'r') as f:
        return json.load(f)

def reset_curiosity_state():
    """Reset curiosity state to inactive. Called on startup to clear any stuck sessions."""
    if os.path.exists(CURIOSITY_STATE_FILE):
        state = {
            "active": False,
            "session_id": None,
            "turns_used": 0,
            "turns_limit": 15,
            "started_at": None,
            "items_explored": []
        }
        with open(CURIOSITY_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

def start_curiosity_session(turns_limit: int = 15) -> Dict:
    """
    Start a new curiosity exploration session.
    
    Args:
        turns_limit: Maximum turns allowed for this session
        
    Returns:
        Dict with session info
    """
    state = init_curiosity_state()
    
    if state["active"]:
        return {
            "success": False,
            "error": "Curiosity session already active",
            "turns_remaining": state["turns_limit"] - state["turns_used"]
        }
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    state["active"] = True
    state["session_id"] = session_id
    state["turns_used"] = 0
    state["turns_limit"] = turns_limit
    state["started_at"] = datetime.now().isoformat()
    state["items_explored"] = []
    
    with open(CURIOSITY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    return {
        "success": True,
        "session_id": session_id,
        "turns_limit": turns_limit,
        "message": f"🔍 CURIOSITY MODE ACTIVATED - {turns_limit} turns available"
    }

def use_curiosity_turn() -> Dict:
    """
    Register that a turn was used in curiosity mode.
    
    Returns:
        Dict with remaining turns info
    """
    state = init_curiosity_state()
    
    if not state["active"]:
        return {"success": False, "error": "No active curiosity session"}
    
    state["turns_used"] += 1
    
    with open(CURIOSITY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    turns_remaining = state["turns_limit"] - state["turns_used"]
    
    return {
        "success": True,
        "turns_used": state["turns_used"],
        "turns_remaining": turns_remaining,
        "message": f"Turn {state['turns_used']}/{state['turns_limit']} - {turns_remaining} remaining"
    }

def end_curiosity_session(summary: Optional[str] = None) -> Dict:
    """
    End the current curiosity session.
    
    Args:
        summary: Optional summary of what was explored
        
    Returns:
        Dict with session summary
    """
    state = init_curiosity_state()
    
    if not state["active"]:
        return {"success": False, "error": "No active curiosity session"}
    
    turns_used = state["turns_used"]
    turns_remaining = state["turns_limit"] - turns_used
    items_explored = state["items_explored"]
    
    # Reset state
    state["active"] = False
    state["session_id"] = None
    state["turns_used"] = 0
    state["started_at"] = None
    
    with open(CURIOSITY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    return {
        "success": True,
        "turns_used": turns_used,
        "turns_saved": turns_remaining,
        "items_explored": len(items_explored),
        "summary": summary,
        "message": f"🔍 CURIOSITY MODE ENDED - Used {turns_used} turns, explored {len(items_explored)} items"
    }

def track_explored_item(item_type: str, item_name: str) -> Dict:
    """
    Track that Kay explored an item during curiosity mode.
    
    Args:
        item_type: Type of item (e.g., 'document', 'url', 'search')
        item_name: Name or identifier of the item
        
    Returns:
        Dict with success status
    """
    state = init_curiosity_state()
    
    if not state["active"]:
        return {"success": False, "error": "No active curiosity session"}
    
    # Add to explored items if not already there
    item_id = f"{item_type}:{item_name}"
    if item_id not in state["items_explored"]:
        state["items_explored"].append(item_id)
        
        with open(CURIOSITY_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        print(f"[CURIOSITY] Tracked exploration: {item_id} ({len(state['items_explored'])} total)")
    
    return {
        "success": True,
        "items_explored": len(state["items_explored"])
    }

def get_curiosity_status() -> Dict:
    """Get current curiosity session status."""
    state = init_curiosity_state()
    
    if not state["active"]:
        return {
            "active": False,
            "message": "No active curiosity session"
        }
    
    turns_remaining = state["turns_limit"] - state["turns_used"]
    
    return {
        "active": True,
        "session_id": state["session_id"],
        "turns_used": state["turns_used"],
        "turns_remaining": turns_remaining,
        "turns_limit": state["turns_limit"],
        "items_explored": len(state["items_explored"]),
        "message": f"Turn {state['turns_used']}/{state['turns_limit']} - {turns_remaining} remaining"
    }

def check_curiosity_triggers() -> Dict:
    """
    Check if curiosity mode should be triggered.
    Returns dict with trigger status and reason.
    """
    # Import here to avoid circular dependencies
    try:
        from engines.scratchpad_engine import scratchpad_view
        
        # Check scratchpad for items
        scratchpad_items = scratchpad_view(status="active")
        
        # Handle both dict with "items" key and direct list
        if isinstance(scratchpad_items, dict):
            items = scratchpad_items.get("items", [])
        else:
            items = scratchpad_items if isinstance(scratchpad_items, list) else []
        
        item_count = len(items)
        
        if item_count > 0:
            return {
                "should_trigger": True,
                "reason": "scratchpad_items",
                "count": item_count,
                "message": f"You have {item_count} item{'s' if item_count != 1 else ''} flagged in your scratchpad. Want processing time to explore?"
            }
    except Exception as e:
        print(f"[CURIOSITY] Error checking scratchpad: {e}")
    
    return {
        "should_trigger": False,
        "reason": "no_triggers",
        "message": "No curiosity triggers detected"
    }

def mark_item_explored(item_id: int, insight_summary: str) -> Dict:
    """
    Mark a scratchpad item as explored and link to autonomous memory.
    
    Args:
        item_id: Scratchpad item ID
        insight_summary: Brief summary to add to scratchpad
        
    Returns:
        Dict with success status
    """
    state = init_curiosity_state()
    
    # Update curiosity state
    state["items_explored"].append({
        "item_id": item_id,
        "explored_at": datetime.now().isoformat(),
        "summary": insight_summary
    })
    
    with open(CURIOSITY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    # Update scratchpad item
    date_ref = datetime.now().strftime("%Y-%m-%d")
    resolution_note = f"Explored → See autonomous memory {date_ref}"
    
    try:
        from engines.scratchpad_engine import scratchpad_resolve
        scratchpad_resolve(item_id, action="resolve", note=resolution_note)
        return {
            "success": True,
            "message": f"Marked item {item_id} as explored"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test functions
    print("Testing curiosity engine...")
    
    # Check triggers
    triggers = check_curiosity_triggers()
    print(f"Triggers: {triggers}")
    
    # Start session
    session = start_curiosity_session(turns_limit=10)
    print(f"Session: {session}")
    
    # Check status
    status = get_curiosity_status()
    print(f"Status: {status}")
    
    # Use a turn
    turn = use_curiosity_turn()
    print(f"Turn: {turn}")
    
    # End session
    end = end_curiosity_session(summary="Test exploration complete")
    print(f"End: {end}")
