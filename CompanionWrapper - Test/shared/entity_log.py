"""
Process-level entity log prefix + broadcast sink.

Since entities run as separate processes, a module-global
entity name is safe and avoids threading issues.

Usage:
    from shared.entity_log import set_entity, etag, elog, register_sink
    set_entity("entity")
    print(f"{etag('MEMORY')} loaded 50 items")  # -> [ENTITY:MEMORY] loaded 50 items
    elog('MEMORY', 'loaded 50 items')  # prints AND broadcasts to UI
"""
import time
import asyncio
from typing import Callable, Optional

_ENTITY = ""
_SINK: Optional[Callable] = None
_LOOP: Optional[asyncio.AbstractEventLoop] = None


def set_entity(name: str):
    """Set the entity name for this process. Called once at startup."""
    global _ENTITY
    _ENTITY = name.upper()


def register_sink(callback: Callable, loop: asyncio.AbstractEventLoop = None):
    """
    Register an async callback that receives structured log data.
    Called once at startup after PrivateRoom is created.

    callback signature: async def sink(data: dict)
    loop: the asyncio event loop to schedule the callback on
    """
    global _SINK, _LOOP
    _SINK = callback
    _LOOP = loop


def etag(tag: str) -> str:
    """Return entity-prefixed tag string: [ENTITY:TAG] or [REED:TAG]."""
    if _ENTITY:
        return f"[{_ENTITY}:{tag}]"
    return f"[{tag}]"


def elog(tag: str, msg: str):
    """Print entity-prefixed log AND broadcast to UI sink if registered."""
    print(f"{etag(tag)} {msg}")

    if _SINK and _LOOP:
        data = {
            "type": "log",
            "entity": _ENTITY.lower(),
            "tag": tag,
            "message": msg,
            "ts": time.time()
        }
        try:
            _LOOP.call_soon_threadsafe(
                asyncio.ensure_future,
                _SINK(data)
            )
        except Exception:
            pass  # Never let log broadcasting crash the wrapper
