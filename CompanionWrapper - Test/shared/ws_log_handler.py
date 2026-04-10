"""
Custom Python logging handler that broadcasts log records through WebSocket.

Used by:
- nexus_entity.py / nexus_reed.py: broadcasts through PrivateRoom
- server.py: broadcasts through ConnectionManager

Parses structured log messages to extract tags where possible.
"""
import logging
import time
import asyncio
import re
from typing import Optional, Callable

# Pattern to extract bracketed tags from log messages like "[Entity] Mode -> BETWEEN_THREADS"
_TAG_PATTERN = re.compile(r'^\[([^\]]+)\]\s*(.*)')

# Classify common log patterns into tags
_LOG_CLASSIFIERS = [
    (re.compile(r'Thread action:.*Pacer decision:', re.I), 'PACER'),
    (re.compile(r'Mode\b.*\b(BETWEEN|IDLE|ACTIVE)', re.I), 'MODE'),
    (re.compile(r'(Started|Parked|Closed) thread', re.I), 'THREAD'),
    (re.compile(r'Waking from (IDLE|DROWSY|SLEEPING)', re.I), 'WAKE'),
    (re.compile(r'(connected|disconnected)', re.I), 'CONNECTION'),
    (re.compile(r'Forwarded command', re.I), 'COMMAND'),
    (re.compile(r'Private (message|affect)', re.I), 'PRIVATE'),
    (re.compile(r'Autonomous', re.I), 'AUTO'),
    (re.compile(r'Curiosity', re.I), 'CURIOSITY'),
    (re.compile(r'Session (saved|load|tracking)', re.I), 'SESSION'),
    (re.compile(r'Replayed \d+ messages', re.I), 'HISTORY'),
]


class WebSocketLogHandler(logging.Handler):
    """
    Logging handler that sends structured log data through a WebSocket callback.

    Usage:
        handler = WebSocketLogHandler(entity="entity", sink=my_async_send, loop=asyncio.get_event_loop())
        logging.getLogger("nexus.kay").addHandler(handler)
    """

    def __init__(self, entity: str, sink: Callable, loop: asyncio.AbstractEventLoop,
                 level=logging.INFO):
        super().__init__(level)
        self.entity = entity.lower()
        self._sink = sink
        self._loop = loop

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            tag = self._classify_message(msg)

            data = {
                "type": "log",
                "entity": self.entity,
                "tag": tag,
                "message": msg,
                "ts": time.time()
            }

            self._loop.call_soon_threadsafe(
                asyncio.ensure_future,
                self._sink(data)
            )
        except Exception:
            pass  # Never crash the logger

    def _classify_message(self, msg: str) -> str:
        """Extract or classify a tag from the log message."""
        # Try to extract bracketed tag: "[Entity] Mode -> X" -> tag="MODE", msg kept as-is
        match = _TAG_PATTERN.match(msg)
        if match:
            bracket_content = match.group(1)
            # Check if it's an entity name prefix like [Entity]
            if bracket_content.lower() in ('entity', 'reed', 'nexus', 're'):
                # It's just an entity prefix, classify the rest
                rest = match.group(2)
                for pattern, tag in _LOG_CLASSIFIERS:
                    if pattern.search(rest):
                        return tag
                return 'NEXUS'
            else:
                # The bracket IS the tag
                return bracket_content.upper()

        # No bracket tag, try classifiers on full message
        for pattern, tag in _LOG_CLASSIFIERS:
            if pattern.search(msg):
                return tag

        return 'NEXUS'  # Default tag for unclassified server/nexus logs
