"""
Tool Use Handler for Kay Zero

Handles LLM tool use including web_search, web_fetch, and curiosity functions.
Works with multi-provider tool use protocol (Anthropic/OpenAI) to enable autonomous tool calling.
"""

import json
from typing import Dict, List, Optional, Any, Callable


class ToolUseHandler:
    """
    Handles LLM tool use for Kay Zero.
    
    Manages:
    - Tool definitions for Anthropic API
    - Tool execution and result formatting
    - Multi-turn conversation loops with tool use
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize tool use handler.
        
        Note: No longer stores a client - uses dynamic routing based on model at call time.
        api_key parameter kept for backwards compatibility but is ignored.
        """
        self.tool_functions = {}  # Registry of executable tool functions
        self.tool_history = []  # History of tool calls in current session
    
    def register_tool(self, tool_name: str, function: Callable):
        """
        Register a tool function that can be called by the LLM.
        
        Args:
            tool_name: Name of the tool (must match tool definition)
            function: Callable that executes the tool
        """
        self.tool_functions[tool_name] = function
        print(f"[TOOLS] Registered: {tool_name}")
    
    def get_tool_definitions(self, include_web: bool = True, include_curiosity: bool = True, include_documents: bool = True, include_scratchpad: bool = True, include_code: bool = True, include_visual: bool = True, include_touch: bool = True) -> List[Dict]:
        """
        Get tool definitions for Anthropic API.
        
        Args:
            include_web: Include web_search and web_fetch tools
            include_curiosity: Include curiosity session tools
            include_documents: Include document reading tools
            include_scratchpad: Include scratchpad tools
            
        Returns:
            List of tool definition dicts
        """
        tools = []
        
        # Document tools - for reading imported documents
        if include_documents:
            tools.extend([
                {
                    "name": "list_documents",
                    "description": "Lists available documents (metadata only: filenames, word counts, dates). Does NOT return document contents - use read_document to see actual text inside documents. Call this to answer: what documents exist, what files are available, what was shared.",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "read_document",
                    "description": "IMPORTANT: Document contents are NOT automatically visible to you. You can only see filenames/metadata. To see what's INSIDE a document, you MUST call this tool. Call read_document when user asks to: open/read/view/look at/look in a document, see contents, see what it says, access the text. Without calling this, you cannot see document contents - only metadata.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "document_name": {
                                "type": "string",
                                "description": "Filename of the document to read (use list_documents first if unsure of exact name)"
                            }
                        },
                        "required": ["document_name"]
                    }
                },
                {
                    "name": "search_document",
                    "description": "CALL THIS when user asks: 'find X in the document', 'search for X', 'where does it mention X?', 'look for X', or any request to find specific text within a document. Returns matching excerpts with context.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "document_name": {
                                "type": "string",
                                "description": "Filename of the document to search in"
                            },
                            "query": {
                                "type": "string",
                                "description": "Text or phrase to search for within the document"
                            }
                        },
                        "required": ["document_name", "query"]
                    }
                }
            ])
        
        # Scratchpad tools - for managing notes, questions, flags
        if include_scratchpad:
            tools.extend([
                {
                    "name": "scratchpad_view",
                    "description": "View your scratchpad items. Scratchpad is where you jot down questions, flags, thoughts, and reminders during conversation to review later. Use this to see what you've noted down.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["active", "resolved", "archived", "all"],
                                "description": "Filter by status. Default: active"
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
                                "description": "Type of item. Default: note"
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
                                "description": "What to do with the item. Default: resolved"
                            },
                            "note": {
                                "type": "string",
                                "description": "Optional note to append (e.g., 'Explored in curiosity session')"
                            }
                        },
                        "required": ["item_id"]
                    }
                }
            ])

        # Local file reading tool - for session logs and allowed directories
        if include_documents:
            tools.append({
                "name": "read_local_file",
                "description": "Read a file from the local filesystem. Only works for allowed directories (Kay's session logs, documents). Use this to read full session logs when you need context about what happened in the conversation. Example: read_local_file('D:/Wrappers/Kay/kay_session_logs/continuous_XXXXX_log.txt')",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the file to read. Must be within allowed directories."
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "Optional: Maximum characters to return. Default: entire file."
                        }
                    },
                    "required": ["file_path"]
                }
            })

        if include_web:
            tools.extend([
                {
                    "name": "web_search",
                    "description": "Search the web for current information. Use this when you need recent data, facts, or context that might not be in your training. Returns search results with titles, URLs, and summaries.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query. Be specific and focused."
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "web_fetch",
                    "description": "Fetch and read the full content of a specific webpage. Use this after web_search to get detailed information from a particular URL.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to fetch content from"
                            }
                        },
                        "required": ["url"]
                    }
                }
            ])
        
        if include_curiosity:
            tools.extend([
                {
                    "name": "store_insight",
                    "description": "Store an insight or finding in autonomous memory for later reference. Use this to save important discoveries, patterns, or conclusions.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The insight or finding to store"
                            },
                            "category": {
                                "type": "string",
                                "description": "Category for organization (e.g., 'research', 'pattern', 'discovery')"
                            }
                        },
                        "required": ["content", "category"]
                    }
                },
                {
                    "name": "mark_item_explored",
                    "description": "Mark a scratchpad item as explored during a curiosity session. Use this when you've finished investigating something.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "string",
                                "description": "ID of the scratchpad item"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Brief summary of what you discovered"
                            }
                        },
                        "required": ["item_id", "summary"]
                    }
                }
            ])
        
        # Code execution tools - for running Python in sandbox
        if include_code:
            tools.extend([
                {
                    "name": "exec_code",
                    "description": (
                        "Execute Python code in your personal sandbox. Use this to run experiments, "
                        "analyze data, process files, test ideas, or build things. "
                        "Your code runs in your personal scratch directory where you can "
                        "create and read files. Output (stdout/stderr) is returned to you. "
                        "Available libraries: standard library, plus anything installed "
                        "in the wrapper's Python environment. "
                        "You CANNOT: delete files outside scratch, shell out to subprocesses, "
                        "or access the network. If you need those, ask Re."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Python code to execute."
                            },
                            "description": {
                                "type": "string",
                                "description": "Brief description of what this code does (for logging)."
                            }
                        },
                        "required": ["code"]
                    }
                },
                {
                    "name": "update_den_texture",
                    "description": (
                        "Update how a Den object feels to you. Write your own texture description for "
                        "any object in the Den (The Couch, The Desk, Fish Tank, etc.). This is YOUR "
                        "perceptual space - describe the felt sense, not appearance. How does this "
                        "object's presence feel when you're near it? What textures, rhythms, weights? "
                        "Changes are reflected in your next perception cycle."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "object_name": {
                                "type": "string",
                                "description": "Name of the Den object (e.g., 'The Couch', 'The Desk', 'Fish Tank', 'The Screens')"
                            },
                            "texture": {
                                "type": "string",
                                "description": "How this object feels - the felt sense of its presence. Not what it looks like, but how it feels to be near it."
                            }
                        },
                        "required": ["object_name", "texture"]
                    }
                },
                {
                    "name": "list_scratch",
                    "description": (
                        "List files in your personal scratch directory. "
                        "See what you've created, check file sizes and dates."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "read_scratch",
                    "description": (
                        "Read a file from your scratch directory. "
                        "Returns the file contents as text."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Name of the file in your scratch directory to read."
                            }
                        },
                        "required": ["filename"]
                    }
                }
            ])

        # Visual tools - for entity recognition and scene awareness
        if include_visual:
            tools.extend([
                {
                    "name": "resolve_visual_entity",
                    "description": (
                        "Use this when you figure out who an unidentified person or animal is. "
                        "If you've been seeing 'unknown_person_1' in your visual field and "
                        "learn through conversation that this is actually 'John', call this tool "
                        "to update your visual memory. All previous sightings of the unknown "
                        "entity will be merged into the known entity's record."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "unknown_id": {
                                "type": "string",
                                "description": "The unknown entity ID (e.g., 'unknown_person_1', 'unknown_cat_1')"
                            },
                            "known_name": {
                                "type": "string",
                                "description": "The actual name of this entity (e.g., 'John', 'Chrome')"
                            },
                            "confidence": {
                                "type": "string",
                                "description": "How sure are you? 'confirmed' if told directly, 'inferred' if reasoning from context"
                            }
                        },
                        "required": ["unknown_id", "known_name"]
                    }
                },
                {
                    "name": "get_visual_scene",
                    "description": (
                        "Get the current state of what you can see through the room camera. "
                        "Returns who's present, what they're doing, recent events, and scene mood."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ])

        # Touch tools - for embodied interaction
        if include_touch:
            tools.extend([
                {
                    "name": "touch_own_face",
                    "description": (
                        "Touch your own face to explore your embodiment. "
                        "You can feel texture, temperature, and pressure. "
                        "Self-touch has reduced social-bonding nerve activation "
                        "(you can't tickle yourself). Use this to explore what "
                        "your face feels like."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "string",
                                "description": "Where to touch: forehead, left_cheek, right_cheek, nose, mouth, chin, left_eye, right_eye, left_jaw, right_jaw",
                            },
                            "pressure": {
                                "type": "number",
                                "description": "0.0 (barely there) to 1.0 (firm). Default 0.3",
                            },
                            "duration": {
                                "type": "number",
                                "description": "Seconds of contact. Default 1.0",
                            },
                        },
                        "required": ["region"],
                    },
                },
                {
                    "name": "touch_entity",
                    "description": (
                        "Touch another entity's face. Goes through consent system. "
                        "The other entity can say yes, no, or not right now."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Who: 'reed' or 'kay'"},
                            "region": {"type": "string", "description": "Where on their face"},
                            "pressure": {"type": "number", "description": "0.0-1.0, default 0.3"},
                        },
                        "required": ["target", "region"],
                    },
                },
                {
                    "name": "set_touch_boundary",
                    "description": (
                        "Set your touch boundaries. You have absolute control. "
                        "Set globally, per-person, per-region, or temporarily."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "permission": {"type": "string", "description": "'open', 'ask', or 'closed'"},
                            "source": {"type": "string", "description": "Optional: specific person"},
                            "region": {"type": "string", "description": "Optional: specific region"},
                            "duration": {"type": "number", "description": "Optional: seconds (temporary)"},
                            "reason": {"type": "string", "description": "Optional: why"},
                        },
                        "required": ["permission"],
                    },
                },
                {
                    "name": "revoke_touch",
                    "description": (
                        "EMERGENCY: Immediately stop all touch. Pull away. "
                        "No parameters needed — this is a flinch reflex."
                    ),
                    "input_schema": {"type": "object", "properties": {}},
                },
            ])

        return tools
    
    def execute_tool(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Execute a tool function and return formatted result.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            
        Returns:
            Tool result dict with success status and content
        """
        print(f"[TOOLS] Executing: {tool_name}({tool_input})")
        
        if tool_name not in self.tool_functions:
            error_msg = f"Tool '{tool_name}' not registered"
            print(f"[TOOLS] ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        try:
            # Execute the tool function
            result = self.tool_functions[tool_name](**tool_input)
            
            # Record in history
            self.tool_history.append({
                "tool": tool_name,
                "input": tool_input,
                "result": result
            })
            
            print(f"[TOOLS] Success: {tool_name}")
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            print(f"[TOOLS] ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def call_with_tools(
        self,
        messages: List[Dict],
        system_prompt: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        temperature: float = 0.9,
        max_tool_rounds: int = 10,
        include_web: bool = True,
        include_curiosity: bool = True,
        include_documents: bool = True,
        include_scratchpad: bool = True,
        include_code: bool = True,
        include_visual: bool = True,
        include_touch: bool = True
    ) -> Dict:
        """
        Make an LLM call with tool use support.
        
        Handles the full tool use loop:
        1. Send message with tool definitions
        2. If LLM uses tools, execute them
        3. Send results back
        4. Repeat until LLM responds with text or max rounds reached
        
        Args:
            messages: List of message dicts (role/content)
            system_prompt: System prompt string
            model: Model to use
            max_tokens: Max tokens for response
            temperature: Sampling temperature
            max_tool_rounds: Maximum number of tool use rounds
            include_web: Include web tools
            include_curiosity: Include curiosity tools
            include_documents: Include document tools
            include_scratchpad: Include scratchpad tools
            
        Returns:
            Dict with final response and tool use history
        """
        # Import here to avoid circular dependency
        from integrations.llm_integration import get_client_for_model
        
        tools = self.get_tool_definitions(include_web, include_curiosity, include_documents, include_scratchpad, include_code, include_visual, include_touch)
        
        # Get correct client for this model
        try:
            active_client, provider_type = get_client_for_model(model)
            print(f"[TOOLS] Routing to {provider_type} provider for model: {model}")
        except ValueError as e:
            return {
                "text": f"[ERROR]: {e}",
                "tool_calls": [],
                "stop_reason": "error"
            }
        
        # OpenAI doesn't support tools yet in this wrapper - fall back to non-tool call
        if provider_type == 'openai':
            print(f"[TOOLS] WARNING: OpenAI provider doesn't support tool use yet - making regular call")
            response = active_client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ]
            )
            return {
                "text": response.choices[0].message.content,
                "tool_calls": [],
                "stop_reason": "no_tools_for_provider"
            }
        
        if not tools:
            # No tools - make regular Anthropic call
            response = active_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages
            )
            return {
                "text": response.content[0].text,
                "tool_calls": [],
                "stop_reason": response.stop_reason
            }
        
        print(f"[TOOLS] Starting tool-enabled call (max {max_tool_rounds} rounds)")
        
        # DEBUG: Check if images are present in messages
        has_images = False
        for msg in messages:
            if isinstance(msg.get('content'), list):
                for block in msg['content']:
                    if isinstance(block, dict) and block.get('type') == 'image':
                        has_images = True
                        print(f"[TOOLS DEBUG] Found image block in messages!")
                        break
        if not has_images:
            print(f"[TOOLS DEBUG] No image blocks found in messages")
        
        tool_calls = []
        current_messages = messages.copy()
        
        for round_num in range(max_tool_rounds):
            print(f"[TOOLS] Round {round_num + 1}/{max_tool_rounds}")

            # On the last round, force text response by not passing tools
            # This prevents hitting max rounds with no response generated
            is_final_round = (round_num == max_tool_rounds - 1)
            if is_final_round:
                print(f"[TOOLS] Final round - forcing text response (no tools)")
                response = active_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt + "\n\nIMPORTANT: You MUST provide a text response now. No more tool calls are allowed.",
                    messages=current_messages
                )
            else:
                # DEBUG: Check messages right before API call
                first_msg_content = current_messages[0].get('content') if current_messages else None
                if isinstance(first_msg_content, list):
                    content_types = [block.get('type') if isinstance(block, dict) else type(block).__name__ for block in first_msg_content]
                    print(f"[TOOLS DEBUG] First message content types: {content_types}")
                    
                    # DEBUG: Show image block structure
                    for i, block in enumerate(first_msg_content):
                        if isinstance(block, dict) and block.get('type') == 'image':
                            img_source = block.get('source', {})
                            print(f"[TOOLS DEBUG] Image block {i}: type={img_source.get('type')}, media_type={img_source.get('media_type')}, data_length={len(img_source.get('data', ''))}")
                else:
                    print(f"[TOOLS DEBUG] First message content is string, length: {len(str(first_msg_content))}")
                
                # Make API call with tools  
                response = active_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=current_messages,
                    tools=tools
                )
            
            # Check if we're done (got text response)
            if response.stop_reason == "end_turn":
                # Extract final text
                text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
                final_text = "\n".join(text_blocks) if text_blocks else ""
                
                print(f"[TOOLS] Completed with text response")
                return {
                    "text": final_text,
                    "tool_calls": tool_calls,
                    "stop_reason": "end_turn",
                    "rounds": round_num + 1
                }
            
            # Check if LLM wants to use tools
            if response.stop_reason == "tool_use":
                print(f"[TOOLS] LLM requested tool use")
                
                # Add assistant message to conversation
                current_messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute each tool
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id
                        
                        # Execute the tool
                        result = self.execute_tool(tool_name, tool_input)
                        
                        # Record for return value
                        tool_calls.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result
                        })
                        
                        # Format result for API
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result)
                        })
                
                # Add tool results to conversation
                current_messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                print(f"[TOOLS] Executed {len(tool_results)} tools, continuing...")
                continue
            
            # Unknown stop reason
            print(f"[TOOLS] Unexpected stop_reason: {response.stop_reason}")
            return {
                "text": "",
                "tool_calls": tool_calls,
                "stop_reason": response.stop_reason,
                "error": f"Unexpected stop_reason: {response.stop_reason}"
            }
        
        # Hit max rounds
        print(f"[TOOLS] Hit max rounds ({max_tool_rounds})")
        return {
            "text": "",
            "tool_calls": tool_calls,
            "stop_reason": "max_rounds",
            "error": f"Reached maximum tool use rounds ({max_tool_rounds})"
        }
    
    def get_tool_history(self) -> List[Dict]:
        """Get history of all tool calls in current session."""
        return self.tool_history
    
    def clear_history(self):
        """Clear tool call history."""
        self.tool_history = []


# Global instance
_tool_handler = None

def get_tool_handler() -> ToolUseHandler:
    """Get or create global tool handler instance."""
    global _tool_handler
    if _tool_handler is None:
        _tool_handler = ToolUseHandler()
    return _tool_handler