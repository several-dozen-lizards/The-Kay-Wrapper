"""Shared SentenceTransformer singleton - loaded once, used everywhere.

This eliminates duplicate model loading across:
- vector_store.py (RAG embeddings)
- conversation_monitor.py (spiral detection)

Saves ~2-4s on first use when multiple modules need embeddings.
"""

_model = None
_model_name = "all-MiniLM-L6-v2"

def get_embedder():
    """
    Get the shared SentenceTransformer model (singleton pattern).

    Returns:
        SentenceTransformer model or None if unavailable
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import logging
            logging.getLogger(__name__).info(f"[EMBEDDER] Loading shared model: {_model_name}")
            print(f"[EMBEDDER] Loading shared model: {_model_name}...")
            # Force CPU mode to avoid CUDA compatibility issues with newer GPUs
            _model = SentenceTransformer(_model_name, device='cpu')
            print(f"[EMBEDDER] Model loaded (CPU mode)")
        except ImportError:
            print("[EMBEDDER] sentence-transformers not installed")
            return None
        except Exception as e:
            print(f"[EMBEDDER] Failed to load model: {e}")
            return None
    return _model


def is_embedder_available():
    """Check if sentence-transformers is available without loading the model."""
    try:
        from sentence_transformers import SentenceTransformer
        return True
    except ImportError:
        return False
