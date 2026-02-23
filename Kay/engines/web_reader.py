"""
Web Reader for Kay Zero

Fetches and parses web pages so Kay can read links sent by Re.

Architecture:
    User message with URL
        ├─→ URL detection (regex)
        ├─→ Fetch with proper headers
        ├─→ Parse HTML to clean text (readability-lxml)
        ├─→ Token-aware truncation/summary
        └─→ Pass to Kay with context

Usage:
    reader = WebReader()
    result = reader.read_url("https://example.com/article")
    # Returns: {
    #     'url': 'https://...',
    #     'title': 'Article Title',
    #     'content': 'Cleaned text...',
    #     'word_count': 1500,
    #     'truncated': False,
    #     'error': None
    # }
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Web fetching
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[WEB_READER] Warning: requests not installed. Run: pip install requests")

# HTML parsing - try readability first (cleaner), fall back to BeautifulSoup
READABILITY_AVAILABLE = False
BS4_AVAILABLE = False

try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    print("[WEB_READER] readability-lxml not installed. Run: pip install readability-lxml")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    print("[WEB_READER] BeautifulSoup not installed. Run: pip install beautifulsoup4")

# Check if we have at least one parser
if not READABILITY_AVAILABLE and not BS4_AVAILABLE:
    print("[WEB_READER] WARNING: No HTML parser available!")


@dataclass
class WebContent:
    """Parsed web page content."""
    url: str
    title: str
    content: str
    word_count: int
    char_count: int
    truncated: bool
    error: Optional[str] = None
    fetch_time: float = 0.0  # seconds


# URL regex pattern - matches common URL formats
URL_PATTERN = re.compile(
    r'https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)',  # path
    re.IGNORECASE
)


class WebReader:
    """
    Fetches and parses web pages for Kay to read.

    Features:
    - URL detection in messages
    - Clean HTML parsing (removes nav, ads, scripts)
    - Token-aware content handling
    - Graceful error handling
    """

    def __init__(
        self,
        max_chars: int = 15000,  # ~4000 tokens
        timeout: int = 10,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ):
        """
        Initialize web reader.

        Args:
            max_chars: Maximum characters to return (truncate if longer)
            timeout: Request timeout in seconds
            user_agent: User agent string for requests
        """
        self.max_chars = max_chars
        self.timeout = timeout
        self.user_agent = user_agent

        # Check dependencies
        self.enabled = REQUESTS_AVAILABLE and (READABILITY_AVAILABLE or BS4_AVAILABLE)

        if self.enabled:
            parser = "readability-lxml" if READABILITY_AVAILABLE else "BeautifulSoup"
            print(f"[WEB_READER] Initialized (parser: {parser}, max_chars: {max_chars})")
        else:
            print("[WEB_READER] Disabled - missing dependencies")

    def find_urls(self, text: str) -> List[str]:
        """
        Find all URLs in a text message.

        Args:
            text: User message text

        Returns:
            List of URLs found
        """
        return URL_PATTERN.findall(text)

    def has_url(self, text: str) -> bool:
        """Check if text contains a URL."""
        return bool(URL_PATTERN.search(text))

    def read_url(self, url: str) -> WebContent:
        """
        Fetch and parse a URL.

        Args:
            url: URL to fetch

        Returns:
            WebContent with parsed content or error
        """
        if not self.enabled:
            return WebContent(
                url=url,
                title="",
                content="",
                word_count=0,
                char_count=0,
                truncated=False,
                error="Web reader disabled - missing dependencies"
            )

        start_time = datetime.now()

        # Fetch the page
        try:
            response = requests.get(
                url,
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                },
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

        except requests.exceptions.Timeout:
            return WebContent(
                url=url, title="", content="", word_count=0, char_count=0,
                truncated=False, error="Timeout - page took too long to load"
            )
        except requests.exceptions.TooManyRedirects:
            return WebContent(
                url=url, title="", content="", word_count=0, char_count=0,
                truncated=False, error="Too many redirects"
            )
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            if status == 404:
                error_msg = "Page not found (404)"
            elif status == 403:
                error_msg = "Access forbidden (403) - might be paywalled"
            elif status == 401:
                error_msg = "Authentication required (401)"
            elif status >= 500:
                error_msg = f"Server error ({status})"
            else:
                error_msg = f"HTTP error: {status}"
            return WebContent(
                url=url, title="", content="", word_count=0, char_count=0,
                truncated=False, error=error_msg
            )
        except requests.exceptions.RequestException as e:
            return WebContent(
                url=url, title="", content="", word_count=0, char_count=0,
                truncated=False, error=f"Request failed: {str(e)}"
            )

        # Parse HTML
        html = response.text
        title, content = self._parse_html(html, url)

        # Handle empty content
        if not content.strip():
            return WebContent(
                url=url, title=title or "Unknown", content="",
                word_count=0, char_count=0, truncated=False,
                error="Could not extract readable content (might be JavaScript-heavy or paywall)"
            )

        # Calculate stats
        char_count = len(content)
        word_count = len(content.split())
        truncated = False

        # Truncate if too long
        if char_count > self.max_chars:
            content = self._smart_truncate(content, self.max_chars)
            truncated = True

        fetch_time = (datetime.now() - start_time).total_seconds()

        return WebContent(
            url=url,
            title=title or "Unknown Title",
            content=content,
            word_count=word_count,
            char_count=char_count,
            truncated=truncated,
            error=None,
            fetch_time=fetch_time
        )

    def _parse_html(self, html: str, url: str) -> Tuple[str, str]:
        """
        Parse HTML to extract title and clean text content.

        Uses readability-lxml if available (better at removing cruft),
        falls back to BeautifulSoup.

        Args:
            html: Raw HTML string
            url: URL (for readability context)

        Returns:
            Tuple of (title, content)
        """
        if READABILITY_AVAILABLE:
            return self._parse_with_readability(html, url)
        elif BS4_AVAILABLE:
            return self._parse_with_beautifulsoup(html)
        else:
            return ("", "No parser available")

    def _parse_with_readability(self, html: str, url: str) -> Tuple[str, str]:
        """Parse using readability-lxml (Mozilla's Readability algorithm)."""
        try:
            doc = Document(html, url=url)
            title = doc.title()

            # Get the cleaned HTML content
            summary_html = doc.summary()

            # Convert to plain text using BeautifulSoup if available
            if BS4_AVAILABLE:
                soup = BeautifulSoup(summary_html, 'html.parser')
                content = soup.get_text(separator='\n', strip=True)
            else:
                # Fallback: strip HTML tags with regex
                content = re.sub(r'<[^>]+>', '', summary_html)
                content = re.sub(r'\s+', ' ', content).strip()

            # Clean up whitespace
            content = self._clean_text(content)

            return (title, content)

        except Exception as e:
            print(f"[WEB_READER] Readability parsing failed: {e}")
            # Fall back to BeautifulSoup if available
            if BS4_AVAILABLE:
                return self._parse_with_beautifulsoup(html)
            return ("", f"Parsing error: {e}")

    def _parse_with_beautifulsoup(self, html: str) -> Tuple[str, str]:
        """Parse using BeautifulSoup (simpler but less clean)."""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Remove script, style, nav, footer, header, aside elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer',
                                          'header', 'aside', 'iframe', 'noscript']):
                element.decompose()

            # Try to find main content area
            main_content = (
                soup.find('article') or
                soup.find('main') or
                soup.find(class_=re.compile(r'content|article|post|entry', re.I)) or
                soup.find('body')
            )

            if main_content:
                content = main_content.get_text(separator='\n', strip=True)
            else:
                content = soup.get_text(separator='\n', strip=True)

            # Clean up whitespace
            content = self._clean_text(content)

            return (title, content)

        except Exception as e:
            return ("", f"Parsing error: {e}")

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text."""
        # Normalize whitespace
        lines = text.split('\n')

        # Remove empty lines and excessive whitespace
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            line = line.strip()
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                    prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False

        return '\n'.join(cleaned_lines).strip()

    def _smart_truncate(self, text: str, max_chars: int) -> str:
        """
        Truncate text at a natural break point.

        Tries to end at paragraph or sentence boundary.
        """
        if len(text) <= max_chars:
            return text

        # Leave room for truncation notice
        target = max_chars - 100

        # Try to find paragraph break
        truncated = text[:target]
        last_para = truncated.rfind('\n\n')
        if last_para > target * 0.7:  # At least 70% of content
            truncated = truncated[:last_para]
        else:
            # Try sentence break
            last_sentence = max(
                truncated.rfind('. '),
                truncated.rfind('.\n'),
                truncated.rfind('? '),
                truncated.rfind('! ')
            )
            if last_sentence > target * 0.7:
                truncated = truncated[:last_sentence + 1]

        return truncated + "\n\n[Content truncated - original was longer]"

    def format_for_kay(self, result: WebContent, user_message: str = "") -> str:
        """
        Format web content for Kay's context.

        Args:
            result: WebContent from read_url
            user_message: Original user message (for context)

        Returns:
            Formatted string for Kay's prompt
        """
        if result.error:
            return (
                f"[Re shared a link: {result.url}]\n"
                f"[Could not read page: {result.error}]"
            )

        truncation_note = " (truncated)" if result.truncated else ""

        return (
            f"[Re shared a link: {result.url}]\n"
            f"[Title: {result.title}]\n"
            f"[{result.word_count} words{truncation_note}, fetched in {result.fetch_time:.1f}s]\n"
            f"\n--- Page Content ---\n"
            f"{result.content}\n"
            f"--- End Page Content ---"
        )

    def process_message_urls(self, message: str) -> Tuple[str, List[WebContent]]:
        """
        Process a user message, fetching any URLs found.

        Args:
            message: User message text

        Returns:
            Tuple of (formatted context for Kay, list of WebContent results)
        """
        urls = self.find_urls(message)

        if not urls:
            return ("", [])

        results = []
        formatted_parts = []

        for url in urls:
            print(f"[WEB_READER] Fetching: {url}")
            result = self.read_url(url)
            results.append(result)

            if result.error:
                print(f"[WEB_READER] Error: {result.error}")
            else:
                print(f"[WEB_READER] Success: {result.word_count} words from '{result.title}'")

            formatted_parts.append(self.format_for_kay(result, message))

        return ("\n\n".join(formatted_parts), results)


# Convenience function for quick URL reading
def read_url(url: str) -> WebContent:
    """Quick function to read a single URL."""
    reader = WebReader()
    return reader.read_url(url)
