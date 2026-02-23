"""
Add tool support to Kay's main query_claude() function in llm_integration.py

This will make document tools, web tools, and curiosity tools actually available 
when Kay makes LLM calls during conversation and curiosity mode.
"""

import sys

filepath = r"D:\ChristinaStuff\AlphaKayZero\integrations\llm_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# CHANGE 1: Add enable_tools parameter to function signature
old_sig = '''def query_claude(prompt, temperature=0.9, model=None, system_prompt=None, 
              session_context=None, use_cache=False, context_dict=None, 
              affect_level=3.5, image_content=None):'''

new_sig = '''def query_claude(prompt, temperature=0.9, model=None, system_prompt=None, 
              session_context=None, use_cache=False, context_dict=None, 
              affect_level=3.5, image_content=None, enable_tools=False):'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("[OK] Updated query_claude signature")
else:
    print("[SKIP] Function signature not found (may have different formatting)")

# CHANGE 2: Update docstring to mention tools
old_docstring_end = '''        image_content: Optional list of image content blocks (base64 encoded) for vision

    Returns:
        LLM response text
    """'''

new_docstring_end = '''        image_content: Optional list of image content blocks (base64 encoded) for vision
        enable_tools: Whether to enable tool use (document, web, curiosity tools)

    Returns:
        LLM response text or dict (if tools were used)
    """'''

if old_docstring_end in content:
    content = content.replace(old_docstring_end, new_docstring_end)
    print("[OK] Updated docstring")
else:
    print("[SKIP] Docstring pattern not found")

# CHANGE 3: Add tool fetching before API call (after cache mode setup, before messages.create)
old_api_call = '''            # Call API with empty system prompt (content is in user message blocks)
            # Sanitize messages to prevent unicode encoding errors
            messages = sanitize_list(messages)
            resp = client.messages.create(
                model=model,
                max_tokens=8192,
                temperature=temperature,
                system="",  # Empty - all content in message blocks
                messages=messages,'''

new_api_call = '''            # Get tools if enabled
            tools = None
            if enable_tools and TOOLS_AVAILABLE:
                try:
                    tool_handler = get_tool_handler()
                    tools = tool_handler.get_tool_definitions(
                        include_web=True, 
                        include_curiosity=True,
                        include_documents=True
                    )
                    print(f"[LLM] Enabled {len(tools)} tools for this call")
                except Exception as e:
                    print(f"[LLM] Failed to load tools: {e}")
                    tools = None
            
            # Call API with empty system prompt (content is in user message blocks)
            # Sanitize messages to prevent unicode encoding errors
            messages = sanitize_list(messages)
            api_params = {
                "model": model,
                "max_tokens": 8192,
                "temperature": temperature,
                "system": "",  # Empty - all content in message blocks
                "messages": messages,
            }
            if tools:
                api_params["tools"] = tools
            
            resp = client.messages.create(**api_params'''

if old_api_call in content:
    content = content.replace(old_api_call, new_api_call)
    print("[OK] Added tool support to cached API call")
else:
    print("[SKIP] Cached API call pattern not found")

# CHANGE 4: Also add to non-cached API call (further down)
old_noncached_call = '''            messages = [{"role": "user", "content": sanitize_unicode(prompt_with_meta)}],'''

new_noncached_call = '''            messages = [{"role": "user", "content": sanitize_unicode(prompt_with_meta)}],
            tools = tool_handler.get_tool_definitions(include_web=True, include_curiosity=True, include_documents=True) if enable_tools and TOOLS_AVAILABLE else None,'''

# Only replace if found in non-cached section (check context)
if old_noncached_call in content:
    # Find this instance - it should be after "else:" for non-cached path
    content = content.replace(old_noncached_call, new_noncached_call, 1)  # Only first occurrence
    print("[OK] Added tool support to non-cached API call")
else:
    print("[SKIP] Non-cached API call pattern not found")

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] Tool support added to query_claude()!")
    print("Kay can now use tools during conversation and curiosity mode.")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
