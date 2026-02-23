"""
Integration Guide: Wiring Web Tools into Reed's LLM Integration

This shows how to integrate the web scraping tools with Reed's existing
llm_integration.py file.

STEP 1: Add imports to llm_integration.py
----------------------------------------
At the top of llm_integration.py, add:

    from integrations.tool_use_handler import get_tool_handler
    from integrations.web_scraping_tools import get_web_tools
    from engines.curiosity_engine import CuriosityEngine
    from engines.scratchpad_engine import ScratchpadEngine

STEP 2: Initialize tools at startup
----------------------------------
After the client initialization (around line 60), add:

    # Initialize tool handler
    tool_handler = get_tool_handler()
    web_tools = get_web_tools()
    
    # Register web tools
    tool_handler.register_tool("web_search", web_tools.web_search)
    tool_handler.register_tool("web_fetch", web_tools.web_fetch)
    
    # Register curiosity tools (if engines are available)
    try:
        curiosity_engine = CuriosityEngine()
        scratchpad_engine = ScratchpadEngine()
        
        tool_handler.register_tool("store_insight", curiosity_engine.store_insight)
        tool_handler.register_tool("mark_item_explored", scratchpad_engine.mark_explored)
    except Exception as e:
        print(f"[TOOLS] Curiosity tools not available: {e}")

STEP 3: Add tool-enabled LLM call function
-----------------------------------------
Add this new function to llm_integration.py (around line 2000):

def get_llm_response_with_tools(
    context,
    affect: float = 3.5,
    temperature: float = 0.9,
    system_prompt: str = None,
    enable_web: bool = True,
    enable_curiosity: bool = False,
    max_tool_rounds: int = 5
):
    '''
    LLM response with tool use support.
    
    This is a NEW function that wraps the tool handler.
    Use this instead of get_llm_response() when you want tool use.
    
    Args:
        context: Context dict (same as get_llm_response)
        affect: Affect level
        temperature: Sampling temperature  
        system_prompt: System prompt to use
        enable_web: Enable web_search and web_fetch tools
        enable_curiosity: Enable curiosity session tools
        max_tool_rounds: Max tool use rounds
        
    Returns:
        Response text (tools are executed transparently)
    '''
    from integrations.tool_use_handler import get_tool_handler
    
    # Build prompt from context (using existing function)
    user_prompt = build_prompt_from_context(context, affect_level=affect)
    
    # Use cached identity if available
    if system_prompt is None:
        cached_identity = build_cached_core_identity()
        system_prompt = cached_identity
    
    # Prepare messages for tool-enabled call
    messages = [
        {"role": "user", "content": user_prompt}
    ]
    
    # Call with tools
    handler = get_tool_handler()
    result = handler.call_with_tools(
        messages=messages,
        system_prompt=system_prompt,
        model=MODEL,
        max_tokens=8192,
        temperature=temperature,
        max_tool_rounds=max_tool_rounds,
        include_web=enable_web,
        include_curiosity=enable_curiosity
    )
    
    # Log tool usage
    if result.get("tool_calls"):
        print(f"[TOOLS] Used {len(result['tool_calls'])} tools in {result.get('rounds', 0)} rounds")
        for call in result['tool_calls']:
            print(f"  - {call['tool']}: {call['input']}")
    
    return result.get("text", "")

STEP 4: Modify get_llm_response() to support tool use
----------------------------------------------------
In the get_llm_response() function (around line 1940), add a parameter:

def get_llm_response(
    prompt_or_context, 
    affect: float = 3.5, 
    temperature=0.9, 
    system_prompt=None, 
    session_context=None, 
    use_cache=False, 
    image_filepaths=None,
    enable_tools=False  # NEW PARAMETER
):
    
Then, at the start of the function, add:

    # If tools requested, use tool-enabled path
    if enable_tools and isinstance(prompt_or_context, dict):
        return get_llm_response_with_tools(
            prompt_or_context,
            affect=affect,
            temperature=temperature,
            system_prompt=system_prompt,
            enable_web=True,
            enable_curiosity=False
        )

STEP 5: Enable tools in curiosity sessions
------------------------------------------
In kay_cli.py (around line 273), when calling get_llm_response during
a curiosity session, add enable_tools=True:

    # Inside _process_turn() method
    if self.curiosity_engine.is_session_active():
        # Curiosity session - enable web tools
        response = get_llm_response(
            context,
            affect=3.5,
            system_prompt=KAY_SYSTEM_PROMPT,
            session_context={"turn_count": self.turn_count, "session_id": self.session_id},
            use_cache=True,
            enable_tools=True  # NEW!
        )
    else:
        # Normal conversation - no tools
        response = get_llm_response(
            context,
            affect=3.5,
            system_prompt=KAY_SYSTEM_PROMPT,
            session_context={"turn_count": self.turn_count, "session_id": self.session_id},
            use_cache=True
        )

STEP 6: Install required packages
---------------------------------
Add to requirements.txt:

    requests>=2.31.0
    beautifulsoup4>=4.12.0
    lxml>=5.0.0

Then run:
    pip install requests beautifulsoup4 lxml

OPTIONAL: SerpAPI for better search
-----------------------------------
For production-quality search (instead of DuckDuckGo scraping):

1. Sign up at https://serpapi.com (free tier: 100 searches/month)
2. Add to .env:
    SERPAPI_KEY=your_key_here
3. The web tools will automatically use SerpAPI when available

TESTING
-------
To test the integration:

1. Start Kay in CLI mode
2. Start a curiosity session
3. Ask Kay something that requires web search:
   "What are the latest developments in AI safety research?"
4. Kay should automatically use web_search() to find information
5. Check console output for [TOOLS] and [WEB SEARCH] logs

WHAT HAPPENS:
- Reed's LLM decides to use web_search("AI safety research")
- Tool handler executes the real web scraping
- Results get fed back to Reed's LLM
- Kay synthesizes information into response
- No nested API calls! Just real web scraping + one LLM call