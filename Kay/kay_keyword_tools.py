"""
Kay's Keyword Search Tools - LLM-callable wrappers for memory keyword graph

Provides tool definitions for Kay to autonomously search his memory
via the Dijkstra keyword graph. This enables self-directed memory
exploration: "where does 'lemon' live in my memory?"
"""

import os
import sys
from typing import Dict, Callable, List, Any

# Add shared to path for keyword_graph imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared"))

try:
    from keyword_graph import KeywordGraphRetriever, extract_keywords_from_context
    KEYWORD_GRAPH_AVAILABLE = True
except ImportError as e:
    print(f"[KEYWORD TOOLS] Could not import keyword_graph: {e}")
    KEYWORD_GRAPH_AVAILABLE = False


def get_kay_keyword_tools() -> Dict[str, Callable]:
    """
    Get keyword search tools formatted for LLM tool handler.

    Returns:
        Dictionary of tool name -> callable function
    """

    # Path to Kay's keyword graph storage
    keyword_graph_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "memory", "keyword_graph"
    )

    # Lazy initialization of keyword graph
    _keyword_graph = None

    def _get_graph():
        """Get or create keyword graph instance."""
        nonlocal _keyword_graph
        if _keyword_graph is None and KEYWORD_GRAPH_AVAILABLE:
            try:
                _keyword_graph = KeywordGraphRetriever(keyword_graph_dir, entity="kay")
            except Exception as e:
                print(f"[KEYWORD TOOLS] Failed to initialize graph: {e}")
        return _keyword_graph

    def search_keywords_tool(keywords: List[str], max_results: int = 5) -> Dict:
        """
        Search Kay's memory keyword graph for concepts and associations.

        Args:
            keywords: Keywords/concepts to search for (e.g., ["lemon", "mother"])
            max_results: Maximum number of memories to return (default: 5)

        Returns:
            Search results with memories and their associated keyword paths
        """
        if not KEYWORD_GRAPH_AVAILABLE:
            return {
                "success": False,
                "error": "Keyword graph not available",
                "query": keywords
            }

        graph = _get_graph()
        if not graph:
            return {
                "success": False,
                "error": "Could not initialize keyword graph",
                "query": keywords
            }

        try:
            # Clean up keywords
            clean_keywords = [k.lower().strip() for k in keywords if k and k.strip()]

            if not clean_keywords:
                return {
                    "success": False,
                    "error": "No valid keywords provided",
                    "query": keywords
                }

            # Use the recall method with loose gating (0.7) for exploration
            results = graph.recall(
                seed_keywords=clean_keywords,
                max_results=max_results,
                osc_state={"band": "alpha"}  # Neutral state for manual search
            )

            # Format results for Kay
            formatted = []
            for r in results:
                mem_id = r.get("memory_id", "")
                cost = r.get("cost", 0)
                path = r.get("path", [])

                # Get the keywords associated with this memory
                mem_keywords = list(graph.keyword_index.get_keywords_for_memory(mem_id))[:10]

                # Try to get a snippet from the memory
                # The graph itself doesn't store full memories, just IDs
                # We return what we have - the ID, keywords, and path
                formatted.append({
                    "memory_id": mem_id,
                    "keywords": mem_keywords,
                    "path": path,  # The keyword chain that led here
                    "cost": round(cost, 2),  # Graph distance
                })

            # Also return some stats about what we found
            stats = graph.get_stats()

            return {
                "success": True,
                "results": formatted,
                "total_matches": len(formatted),
                "query": clean_keywords,
                "index_stats": {
                    "total_keywords": stats.get("keyword_index", {}).get("total_keywords", 0),
                    "total_memories": stats.get("keyword_index", {}).get("total_memories", 0),
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "query": keywords
            }

    def list_keywords_tool(prefix: str = "", limit: int = 20) -> Dict:
        """
        List keywords in Kay's memory index, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keywords (e.g., "lem" for lemon-related)
            limit: Maximum keywords to return (default: 20)

        Returns:
            List of keywords with their memory counts
        """
        if not KEYWORD_GRAPH_AVAILABLE:
            return {
                "success": False,
                "error": "Keyword graph not available"
            }

        graph = _get_graph()
        if not graph:
            return {
                "success": False,
                "error": "Could not initialize keyword graph"
            }

        try:
            # Get all keywords from the index
            all_keywords = list(graph.keyword_index.keyword_to_memories.keys())

            # Filter by prefix if provided
            if prefix:
                prefix_lower = prefix.lower().strip()
                filtered = [k for k in all_keywords if k.startswith(prefix_lower)]
            else:
                filtered = all_keywords

            # Sort by memory count (most connected first)
            keyword_counts = [
                (k, graph.keyword_index.get_keyword_count(k))
                for k in filtered
            ]
            keyword_counts.sort(key=lambda x: x[1], reverse=True)

            # Limit results
            limited = keyword_counts[:limit]

            return {
                "success": True,
                "keywords": [{"keyword": k, "memory_count": c} for k, c in limited],
                "total_matching": len(filtered),
                "total_in_index": len(all_keywords),
                "prefix_filter": prefix if prefix else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"List failed: {str(e)}"
            }

    def get_keyword_connections_tool(keyword: str) -> Dict:
        """
        Get memories connected to a specific keyword and related keywords.

        Args:
            keyword: The keyword to explore

        Returns:
            Memories tagged with this keyword and other keywords they share
        """
        if not KEYWORD_GRAPH_AVAILABLE:
            return {
                "success": False,
                "error": "Keyword graph not available"
            }

        graph = _get_graph()
        if not graph:
            return {
                "success": False,
                "error": "Could not initialize keyword graph"
            }

        try:
            keyword_lower = keyword.lower().strip()

            # Get memories for this keyword
            memory_ids = graph.keyword_index.get_memories_for_keyword(keyword_lower)

            if not memory_ids:
                return {
                    "success": True,
                    "keyword": keyword_lower,
                    "memory_count": 0,
                    "memories": [],
                    "related_keywords": [],
                    "message": f"No memories found for keyword '{keyword_lower}'"
                }

            # For each memory, get its other keywords
            related_keywords = {}
            memories_info = []

            for mem_id in list(memory_ids)[:10]:  # Limit to 10 memories
                mem_keywords = list(graph.keyword_index.get_keywords_for_memory(mem_id))
                memories_info.append({
                    "memory_id": mem_id,
                    "keywords": mem_keywords[:10]
                })

                # Count co-occurring keywords
                for k in mem_keywords:
                    if k != keyword_lower:
                        related_keywords[k] = related_keywords.get(k, 0) + 1

            # Sort related keywords by co-occurrence count
            sorted_related = sorted(related_keywords.items(), key=lambda x: x[1], reverse=True)

            return {
                "success": True,
                "keyword": keyword_lower,
                "memory_count": len(memory_ids),
                "memories": memories_info,
                "related_keywords": [
                    {"keyword": k, "co_occurrences": c}
                    for k, c in sorted_related[:15]
                ]
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Exploration failed: {str(e)}",
                "keyword": keyword
            }

    # Return tool dictionary
    return {
        'search_keywords': search_keywords_tool,
        'list_keywords': list_keywords_tool,
        'get_keyword_connections': get_keyword_connections_tool
    }


# Tool definitions for the LLM (Anthropic tool schema format)
KEYWORD_TOOL_DEFINITIONS = [
    {
        "name": "search_keywords",
        "description": (
            "Search your memory keyword graph for concepts and associations. "
            "Enter keywords to find memories tagged with those concepts. "
            "Returns memories and their associated keywords, showing how "
            "concepts connect across your experience. Use this to trace "
            "associative paths like 'lemon' -> 'mother' -> 'Coney Island'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords/concepts to search for"
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum results to return"
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "list_keywords",
        "description": (
            "List keywords in your memory index. Optionally filter by prefix "
            "to find all keywords starting with certain letters (e.g., 'lem' "
            "to find 'lemon', 'lemur', etc.). Shows which keywords have the "
            "most memories attached."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "description": "Optional prefix to filter keywords"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum keywords to return"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_keyword_connections",
        "description": (
            "Explore connections for a specific keyword. Shows all memories "
            "tagged with that keyword and what OTHER keywords those memories "
            "share. Reveals the associative web around a concept."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The keyword to explore"
                }
            },
            "required": ["keyword"]
        }
    }
]
