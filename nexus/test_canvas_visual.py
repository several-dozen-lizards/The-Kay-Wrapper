"""
Canvas Visual Test — paints a serpent and KEEPS it visible.
No clearing. Waits 30 seconds so you can see it in Godot.

Usage:
  1. Start Nexus server + Godot UI (auto-connects now)
  2. Click the 🎨 sidebar button in Godot to open canvas panel
  3. Run: python test_canvas_visual.py
  4. Watch the canvas panel — serpent should appear
"""

import asyncio
import json
import websockets
import time

SERVER = "ws://localhost:8765"


async def paint_and_hold():
    print("🎨 Connecting to Nexus...")
    url = f"{SERVER}/ws/Painter?type=human"

    async with websockets.connect(url) as ws:
        # Drain startup events
        await asyncio.sleep(1)
        try:
            while True:
                await asyncio.wait_for(ws.recv(), timeout=0.5)
        except asyncio.TimeoutError:
            pass

        print("✅ Connected. Painting...")

        # Phase 1: Background + serpent
        await ws.send(json.dumps({
            "command": "paint",
            "entity": "Reed",
            "commands": [
                {"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#0a0a1a"},
                # Stars
                {"action": "draw_circle", "x": 120, "y": 80, "radius": 2, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 340, "y": 45, "radius": 1, "fill_color": "#aaaacc"},
                {"action": "draw_circle", "x": 560, "y": 120, "radius": 3, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 700, "y": 60, "radius": 2, "fill_color": "#ccccff"},
                {"action": "draw_circle", "x": 200, "y": 200, "radius": 1, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 650, "y": 180, "radius": 2, "fill_color": "#aaaaee"},
                {"action": "draw_circle", "x": 450, "y": 160, "radius": 2, "fill_color": "#ddddff"},
                # Serpent body
                {"action": "draw_circle", "x": 100, "y": 400, "radius": 25, "fill_color": "#00a88a"},
                {"action": "draw_circle", "x": 150, "y": 380, "radius": 28, "fill_color": "#00b89a"},
                {"action": "draw_circle", "x": 210, "y": 350, "radius": 30, "fill_color": "#00c8a4"},
                {"action": "draw_circle", "x": 280, "y": 330, "radius": 32, "fill_color": "#00d4aa"},
                {"action": "draw_circle", "x": 350, "y": 320, "radius": 30, "fill_color": "#00c8a4"},
                {"action": "draw_circle", "x": 420, "y": 340, "radius": 28, "fill_color": "#00b89a"},
                {"action": "draw_circle", "x": 480, "y": 370, "radius": 30, "fill_color": "#00c8a4"},
                {"action": "draw_circle", "x": 540, "y": 350, "radius": 32, "fill_color": "#00d4aa"},
                {"action": "draw_circle", "x": 600, "y": 320, "radius": 28, "fill_color": "#00b89a"},
                {"action": "draw_circle", "x": 650, "y": 290, "radius": 25, "fill_color": "#00a88a"},
                # Head
                {"action": "draw_circle", "x": 690, "y": 270, "radius": 22, "fill_color": "#00d4aa"},
                # Eye
                {"action": "draw_circle", "x": 700, "y": 262, "radius": 6, "fill_color": "#ffcc00"},
                {"action": "draw_circle", "x": 702, "y": 261, "radius": 3, "fill_color": "#1a1a2e"},
                # Gold accents
                {"action": "draw_circle", "x": 210, "y": 340, "radius": 5, "fill_color": "#d4aa00"},
                {"action": "draw_circle", "x": 350, "y": 310, "radius": 5, "fill_color": "#d4aa00"},
                {"action": "draw_circle", "x": 480, "y": 360, "radius": 5, "fill_color": "#d4aa00"},
                {"action": "draw_circle", "x": 600, "y": 310, "radius": 5, "fill_color": "#d4aa00"},
            ]
        }))

        # Wait for result
        await asyncio.sleep(2)
        events = []
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=1)
                msg = json.loads(raw)
                etype = msg.get("event_type", "")
                events.append(etype)
                if etype == "paint_result":
                    d = msg.get("data", {})
                    print(f"  ✅ iteration={d.get('iteration')}, dims={d.get('dimensions')}")
                elif etype == "canvas_update":
                    d = msg.get("data", {})
                    print(f"  ✅ broadcast: base64 len={len(d.get('base64', ''))}")
        except asyncio.TimeoutError:
            pass

        print(f"  Events received: {events}")

        # Phase 2: Add text
        print("Adding title text...")
        await ws.send(json.dumps({
            "command": "paint",
            "entity": "Reed",
            "commands": [
                {"action": "draw_text", "x": 400, "y": 540, "text": "Reed Was Here",
                 "color": "#00d4aa", "font_size": 28},
                {"action": "draw_text", "x": 400, "y": 570, "text": "canvas pipeline test",
                 "color": "#666688", "font_size": 14},
            ]
        }))

        await asyncio.sleep(2)
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=1)
                msg = json.loads(raw)
                etype = msg.get("event_type", "")
                if etype == "paint_result":
                    d = msg.get("data", {})
                    print(f"  ✅ iteration={d.get('iteration')}")
        except asyncio.TimeoutError:
            pass

        print()
        print("=" * 50)
        print("🎨 PAINTING COMPLETE — HOLDING INDEFINITELY")
        print("   Check the Godot canvas panel now!")
        print("   Also check: sessions/canvas/reed/ for PNGs")
        print("=" * 50)
        print()
        print("Press Ctrl+C to disconnect.")

        try:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=3600)
                    msg = json.loads(raw)
                    print(f"  ← {msg.get('event_type', '?')}")
                except asyncio.TimeoutError:
                    pass
        except KeyboardInterrupt:
            print("\nDisconnecting.")


if __name__ == "__main__":
    asyncio.run(paint_and_hold())
