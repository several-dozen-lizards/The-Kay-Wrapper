"""
Web search engine for Reed's curiosity system.
Allows Kay to search and fetch web content during autonomous processing.
"""

import anthropic
import os
import json
from typing import Dict, List, Optional

def web_search(query: str, api_key: Optional[str] = None) -> Dict:
    """
    Perform web search using Claude's built-in web_search tool.
    
    Args:
        query: Search query string
        api_key: Anthropic API key (uses env var if not provided)
        
    Returns:
        Dict with search results
    """
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        # Use Claude to perform web search
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search"
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Search for: {query}\n\nProvide a summary of the key findings."
                }
            ]
        )
        
        # Extract search results and response
        results = {
            "query": query,
            "success": True,
            "content": [],
            "summary": ""
        }
        
        for block in message.content:
            if block.type == "text":
                results["summary"] += block.text
            elif hasattr(block, 'type') and 'search' in str(block.type):
                results["content"].append(str(block))
        
        return results
        
    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e)
        }

def web_fetch(url: str, api_key: Optional[str] = None) -> Dict:
    """
    Fetch content from a specific URL using Claude's web_fetch tool.
    
    Args:
        url: URL to fetch
        api_key: Anthropic API key (uses env var if not provided)
        
    Returns:
        Dict with page content
    """
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            tools=[
                {
                    "type": "web_fetch",
                    "name": "web_fetch"
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Fetch and summarize the content from: {url}"
                }
            ]
        )
        
        content = ""
        for block in message.content:
            if block.type == "text":
                content += block.text
        
        return {
            "url": url,
            "success": True,
            "content": content
        }
        
    except Exception as e:
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test the search (requires API key)
    print("Web search engine ready. Example usage:")
    print("  results = web_search('Pictish symbols meaning')")
    print("  content = web_fetch('https://example.com')")
