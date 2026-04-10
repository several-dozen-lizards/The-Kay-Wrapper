"""
Text sanitization utilities for the Kay wrapper.

Handles problematic unicode characters that can crash JSON encoding
when sending to APIs (especially the Anthropic API).

The main culprit is surrogate characters (U+D800 to U+DFFF) which are
invalid in UTF-8 but can appear in Python strings when improperly decoded
or when emoji characters get corrupted.
"""

import re


def sanitize_unicode(text: str) -> str:
    """
    Remove or replace problematic unicode characters that can crash JSON encoding.
    Specifically handles surrogate characters that cause 'surrogates not allowed' errors.
    
    This is more aggressive than simple regex replacement - it uses multiple
    strategies to ensure the string is safe for JSON encoding.
    
    Args:
        text: Input string that may contain problematic unicode
        
    Returns:
        Cleaned string safe for JSON encoding and API calls
    """
    if not text:
        return text
    
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    
    # Strategy 1: Use surrogatepass to handle surrogates, then re-encode cleanly
    try:
        # Encode allowing surrogates, then decode ignoring errors
        cleaned = text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='ignore')
        
        # Now do a final clean encode/decode to ensure no issues
        cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        
        # Verify it can be JSON encoded
        import json
        json.dumps(cleaned)
        return cleaned
    except (UnicodeEncodeError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    
    # Strategy 2: Manual surrogate removal with regex
    try:
        # Remove surrogate characters (U+D800 to U+DFFF)
        cleaned = re.sub(r'[\ud800-\udfff]', '', text)
        
        # Verify it works
        import json
        json.dumps(cleaned)
        return cleaned
    except (UnicodeEncodeError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    
    # Strategy 3: Character-by-character filtering (nuclear option)
    try:
        cleaned = ''.join(
            char for char in text 
            if (ord(char) < 0xD800 or ord(char) > 0xDFFF) and ord(char) < 0x110000
        )
        return cleaned
    except Exception:
        pass
    
    # Strategy 4: ASCII-only fallback (last resort)
    try:
        return text.encode('ascii', errors='ignore').decode('ascii')
    except Exception:
        return ""


def sanitize_dict(data: dict) -> dict:
    """
    Recursively sanitize all string values in a dictionary.
    Also sanitizes dictionary keys.
    
    Args:
        data: Dictionary that may contain problematic unicode in values
        
    Returns:
        Dictionary with all string values sanitized
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        # Sanitize keys too
        clean_key = sanitize_unicode(key) if isinstance(key, str) else key
        
        if isinstance(value, str):
            result[clean_key] = sanitize_unicode(value)
        elif isinstance(value, dict):
            result[clean_key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[clean_key] = sanitize_list(value)
        else:
            result[clean_key] = value
    return result


def sanitize_list(data: list) -> list:
    """
    Recursively sanitize all string values in a list.
    
    Args:
        data: List that may contain problematic unicode in values
        
    Returns:
        List with all string values sanitized
    """
    if not isinstance(data, list):
        return data
    
    result = []
    for item in data:
        if isinstance(item, str):
            result.append(sanitize_unicode(item))
        elif isinstance(item, dict):
            result.append(sanitize_dict(item))
        elif isinstance(item, list):
            result.append(sanitize_list(item))
        else:
            result.append(item)
    return result


def sanitize_for_json(data):
    """
    Sanitize any data structure for safe JSON encoding.
    
    Args:
        data: Any data structure (str, dict, list, etc.)
        
    Returns:
        Sanitized data safe for json.dumps()
    """
    if isinstance(data, str):
        return sanitize_unicode(data)
    elif isinstance(data, dict):
        return sanitize_dict(data)
    elif isinstance(data, list):
        return sanitize_list(data)
    else:
        return data
