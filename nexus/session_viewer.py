"""
Session Viewer API
REST endpoints for browsing, searching, and exporting session logs.
Imported into the main nexus server.

Usage in server.py:
    from session_viewer import mount_viewer
    mount_viewer(app, session_log)
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from session_logger import INDEX_PATH, SESSIONS_DIR


def mount_viewer(app: FastAPI, session_log):
    """Mount all session viewer endpoints onto the FastAPI app."""

    @app.get("/sessions")
    async def list_sessions():
        """List all sessions from the index, enriched with private room info."""
        if INDEX_PATH.exists():
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                index = json.load(f)
            # Enrich with private room log detection
            for entry in index:
                sid = entry.get("session_id", "")
                priv_files = list(SESSIONS_DIR.glob(f"private_*_{sid}.jsonl"))
                entry["private_rooms"] = [p.stem.split("_")[1] for p in priv_files]
            return {"sessions": list(reversed(index))}
        # Fallback: scan sessions dir for JSONL files
        sessions = []
        for p in sorted(SESSIONS_DIR.glob("nexus_*.jsonl"), reverse=True):
            sid = p.stem.replace("nexus_", "")
            sessions.append({"session_id": sid, "files": {"jsonl": str(p)}})
        return {"sessions": sessions}

    @app.get("/sessions/{session_id}/messages")
    async def get_session_messages(session_id: str, offset: int = 0, limit: int = 500):
        """Read all messages for a session — merges nexus + private room logs."""
        all_messages = []
        
        # 1. Nexus group chat JSONL
        jsonl_path = SESSIONS_DIR / f"nexus_{session_id}.jsonl"
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        msg = json.loads(line)
                        msg["_source"] = "nexus"
                        all_messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        
        # 2. Private room JSONLs (private_kay_*, private_reed_*)
        for priv_path in SESSIONS_DIR.glob(f"private_*_{session_id}.jsonl"):
            entity = priv_path.stem.split("_")[1]  # e.g. "kay" from "private_kay_20260404"
            with open(priv_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        msg = json.loads(line)
                        msg["_source"] = f"private_{entity}"
                        all_messages.append(msg)
                    except json.JSONDecodeError:
                        continue
        
        # Sort by timestamp (all entries should have one)
        def sort_key(m):
            ts = m.get("timestamp", "")
            if not ts:
                return ""
            return ts
        all_messages.sort(key=sort_key)
        
        # Apply pagination
        page = all_messages[offset:offset + limit]
        return {"session_id": session_id, "messages": page, "offset": offset, "total": len(all_messages)}

    @app.get("/sessions/{session_id}/log")
    async def get_session_log_content(session_id: str, source: str = "server"):
        """Read a log file for a session.
        source: "server" (nexus .log), "kay" (Kay terminal .log)
        """
        if source == "server":
            log_path = SESSIONS_DIR / f"nexus_{session_id}.log"
        elif source == "kay":
            log_path = _find_kay_log(session_id)
            if not log_path:
                return {"error": f"No Kay log for session {session_id}", "lines": []}
        else:
            return {"error": f"Unknown source: {source}", "lines": []}

        if not log_path or not log_path.exists():
            return {"error": f"Log not found: {log_path}", "lines": []}

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"session_id": session_id, "source": source, "lines": lines, "total": len(lines)}

    @app.get("/sessions/{session_id}/search")
    async def search_session(session_id: str, q: str = ""):
        """Search across all log files for a session."""
        if not q:
            return {"results": []}

        results = []
        q_lower = q.lower()

        # Search JSONL messages
        jsonl_path = SESSIONS_DIR / f"nexus_{session_id}.jsonl"
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if q_lower in line.lower():
                        try:
                            msg = json.loads(line)
                            results.append({
                                "source": "messages", "line": i,
                                "content": msg.get("content", line.strip())[:300],
                                "sender": msg.get("sender", ""),
                                "timestamp": msg.get("timestamp", ""),
                            })
                        except json.JSONDecodeError:
                            results.append({"source": "messages", "line": i, "content": line.strip()[:300]})

        # Search server log
        server_log = SESSIONS_DIR / f"nexus_{session_id}.log"
        if server_log.exists():
            with open(server_log, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if q_lower in line.lower():
                        results.append({"source": "server_log", "line": i, "content": line.strip()[:300]})

        # Search Kay terminal log
        kay_path = _find_kay_log(session_id)
        if kay_path and kay_path.exists():
            with open(kay_path, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if q_lower in line.lower():
                        results.append({"source": "kay_log", "line": i, "content": line.strip()[:300]})

        # Search private room logs
        for priv_path in SESSIONS_DIR.glob(f"private_*_{session_id}.jsonl"):
            entity = priv_path.stem.split("_")[1]
            with open(priv_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if q_lower in line.lower():
                        try:
                            msg = json.loads(line)
                            results.append({
                                "source": f"private_{entity}", "line": i,
                                "content": msg.get("content", line.strip())[:300],
                                "sender": msg.get("sender", ""),
                                "timestamp": msg.get("timestamp", ""),
                            })
                        except json.JSONDecodeError:
                            results.append({"source": f"private_{entity}", "line": i, "content": line.strip()[:300]})

        return {"session_id": session_id, "query": q, "results": results[:200]}

    @app.get("/viewer", response_class=HTMLResponse)
    async def session_viewer_page():
        """Serve the session viewer HTML page."""
        viewer_path = Path(__file__).parent / "session_viewer.html"
        if viewer_path.exists():
            return HTMLResponse(viewer_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Viewer not found</h1><p>Place session_viewer.html next to session_viewer.py</p>")


def _find_kay_log(session_id: str):
    """Look up Kay's terminal log path from the sessions index."""
    if not INDEX_PATH.exists():
        return None
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index = json.load(f)
        for entry in index:
            if entry.get("session_id") == session_id:
                kay_path = entry.get("files", {}).get("kay_log")
                if kay_path:
                    return Path(kay_path)
        return None
    except Exception:
        return None
