"""
Real Web Scraping Tools for the entity

Uses actual web scraping and search APIs instead of nested LLM calls.
Much cheaper and more reliable for autonomy!
"""

import os
import json
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime


class WebScrapingTools:
    """
    Real web scraping and search for the entity.
    
    Uses:
    - SerpAPI for search (optional, falls back to DuckDuckGo HTML scraping)
    - requests + BeautifulSoup for fetching pages
    """
    
    def __init__(self, serpapi_key: Optional[str] = None):
        """
        Initialize web tools.
        
        Args:
            serpapi_key: SerpAPI key (optional, falls back to free DDG scraping)
        """
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY")
        self.search_history = []
        self.fetch_history = []
        
        if self.serpapi_key:
            print("[WEB TOOLS] SerpAPI enabled")
        else:
            print("[WEB TOOLS] Using free DuckDuckGo scraping (SerpAPI not configured)")
    
    def web_search(self, query: str, max_results: int = 5) -> Dict:
        """
        Search the web for information.
        
        Uses SerpAPI if available, otherwise falls back to DuckDuckGo scraping.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            Dict with search results
        """
        print(f"[WEB SEARCH] Query: '{query}'")
        
        try:
            if self.serpapi_key:
                results = self._search_serpapi(query, max_results)
            else:
                results = self._search_duckduckgo(query, max_results)
            
            # Store in history
            self.search_history.append({
                "query": query,
                "results": results,
                "timestamp": datetime.now().isoformat(),
                "count": len(results)
            })
            
            print(f"[WEB SEARCH] Found {len(results)} results")
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            print(f"[WEB SEARCH] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def _search_serpapi(self, query: str, max_results: int) -> List[Dict]:
        """Search using SerpAPI (Google results)."""
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": max_results
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        
        return results
    
    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict]:
        """
        Search using DuckDuckGo HTML scraping (free, no API key needed).
        
        Note: This is a backup method. For heavy usage, use SerpAPI.
        """
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.post(url, data=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Parse DDG results
        for result in soup.find_all('div', class_='result')[:max_results]:
            title_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')
            
            if title_elem:
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": title_elem.get('href', ''),
                    "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                })
        
        return results
    
    def web_fetch(self, url: str, extract_text: bool = True) -> Dict:
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch
            extract_text: If True, extract clean text. If False, return raw HTML.
            
        Returns:
            Dict with page content
        """
        print(f"[WEB FETCH] URL: {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            if extract_text:
                # Parse and extract clean text
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text(separator='\n', strip=True)
                
                # Clean up excessive whitespace
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                content = '\n'.join(lines)
                
                # Truncate if too long (keep first 8000 chars)
                if len(content) > 8000:
                    content = content[:8000] + "\n\n[Content truncated - showing first 8000 characters]"
                
            else:
                content = response.text
            
            # Store in history
            self.fetch_history.append({
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "length": len(content)
            })
            
            print(f"[WEB FETCH] Retrieved {len(content)} chars")
            
            return {
                "success": True,
                "url": url,
                "content": content,
                "length": len(content)
            }
            
        except Exception as e:
            print(f"[WEB FETCH] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def get_search_history(self) -> List[Dict]:
        """Get history of all searches."""
        return self.search_history
    
    def get_fetch_history(self) -> List[Dict]:
        """Get history of all fetches."""
        return self.fetch_history
    
    def clear_history(self):
        """Clear all history."""
        self.search_history = []
        self.fetch_history = []


# Global instance
_web_tools = None

def get_web_tools() -> WebScrapingTools:
    """Get or create global web tools instance."""
    global _web_tools
    if _web_tools is None:
        _web_tools = WebScrapingTools()
    return _web_tools


# Convenience functions
def web_search(query: str, max_results: int = 5) -> Dict:
    """Search the web for information."""
    return get_web_tools().web_search(query, max_results)


def web_fetch(url: str) -> Dict:
    """Fetch content from a URL."""
    return get_web_tools().web_fetch(url)
