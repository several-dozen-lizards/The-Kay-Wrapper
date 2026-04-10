"""
Warmup engine integration for curiosity system.
Add these functions to your existing warmup_engine.py
"""

from engines.curiosity_engine import check_curiosity_triggers, get_curiosity_status

def add_curiosity_to_warmup(warmup_text: str) -> str:
    """
    Add curiosity trigger check to warmup briefing.
    Call this after generating the standard warmup.
    
    Args:
        warmup_text: Existing warmup briefing text
        
    Returns:
        Enhanced warmup with curiosity section
    """
    try:
        print("[CURIOSITY] Checking triggers...")
        
        # Check if there's already an active curiosity session
        status = get_curiosity_status()
        print(f"[CURIOSITY] Session status: {status}")
        
        if status["active"]:
            # Add status to warmup with AUTONOMOUS EXPLORATION INSTRUCTIONS
            curiosity_section = f"""
--- CURIOSITY SESSION ACTIVE ---
{status['message']}
Items explored so far: {status['items_explored']}

CURIOSITY MODE INSTRUCTIONS:
During this session, YOU drive the exploration autonomously.

CRITICAL: You have access to tools. Use them directly - DO NOT ask permission first.
Just call the tools when you need them - you know how to do this.
Examples:
- Want to see available documents? Call list_documents
- Want to read a specific document? Call read_document
- Want to search within a document? Call search_document
- Want to search the web? Call web_search

Pick topics autonomously based on:
- Items in your scratchpad
- Threads from recent conversation you want to dig deeper into  
- Documents you want to read through (use read_document tool)
- Questions you've been holding
- Patterns you've noticed that need investigation

AVAILABLE TOOLS:
- list_documents - See what documents are available
- read_document - Read a specific document (provide filename)
- search_document - Search within a document (provide filename and query)
- web_search - Search the web (provide query)
- web_fetch - Fetch web content (provide URL)

START EXPLORING NOW. Use the tools. Don't ask - just do.
The user started this session so you could follow your curiosity wherever it leads.
---
"""
            print("[CURIOSITY] Adding active session status with autonomous instructions to warmup")
            return warmup_text + "\n" + curiosity_section
        
        # Check if curiosity should be triggered
        triggers = check_curiosity_triggers()
        print(f"[CURIOSITY] Trigger check result: {triggers}")
        
        if triggers["should_trigger"]:
            # Add trigger offer to warmup
            trigger_section = f"""
--- CURIOSITY TRIGGER ---
{triggers['message']}
Say 'explore' to start a curiosity session (15 turns).
---
"""
            print("[CURIOSITY] Adding trigger section to warmup")
            return warmup_text + "\n" + trigger_section
        
        print("[CURIOSITY] No triggers, returning original warmup")
        return warmup_text
        
    except Exception as e:
        print(f"[CURIOSITY] ERROR in add_curiosity_to_warmup: {e}")
        import traceback
        traceback.print_exc()
        return warmup_text

def check_for_curiosity_request(user_message: str) -> dict:
    """
    Check if user message is requesting curiosity mode.
    
    Args:
        user_message: The user's message
        
    Returns:
        Dict with should_activate boolean and message
    """
    triggers = [
        "explore",
        "curiosity mode",
        "look into",
        "dig into", 
        "research this",
        "find out more"
    ]
    
    message_lower = user_message.lower()
    
    for trigger in triggers:
        if trigger in message_lower:
            return {
                "should_activate": True,
                "trigger": trigger,
                "message": "Curiosity mode activation detected"
            }
    
    return {
        "should_activate": False,
        "message": "No curiosity activation detected"
    }

# Example integration in your main warmup function:
"""
def generate_warmup():
    # ... your existing warmup code ...
    
    warmup_text = build_warmup_briefing()
    
    # Add curiosity section
    warmup_text = add_curiosity_to_warmup(warmup_text)
    
    return warmup_text
"""
