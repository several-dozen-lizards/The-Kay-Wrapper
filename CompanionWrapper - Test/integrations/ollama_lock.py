# ollama_lock.py
"""
Shared lock for Ollama access.

Prevents moondream (vision) and dolphin-mistral (peripheral) from
fighting over the same Ollama instance. Both systems acquire this
lock before making any Ollama call.
"""

import threading

_ollama_lock = threading.Lock()


def get_ollama_lock() -> threading.Lock:
    """Get the shared Ollama access lock."""
    return _ollama_lock
