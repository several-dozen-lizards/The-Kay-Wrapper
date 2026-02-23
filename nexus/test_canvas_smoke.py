"""
Canvas Smoke Test — connects to Nexus WebSocket and fires paint commands.

Tests the full pipeline:
  Python script → WebSocket → server.py → canvas_manager.py → EntityPainter
  → broadcast → Godot canvas_panel.gd displays the image

Usage:
  1. Start Nexus server:  python server.py
  2. Open Godot UI and connect to Nexus
  3. Run this:  python test_canvas_smoke.py

You should see the canvas panel light up in Godot with a painting.
"""

import asyncio
import json
import websockets
import time

SERVER = "ws://localhost:8765"
ENTITY = "Reed"  # Paint as Reed


async def send_command(ws, command: str, data: dict):
    """Send a command message to Nexus server."""
    payload = {"command": command, **data}
    await ws.send(json.dumps(payload))
    print(f"  → sent: {command}")


async def wait_for_event(ws, event_type: str, timeout: float = 5.0):
    """Wait for a specific event from the server."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=deadline - time.time())
            msg = json.loads(raw)
            etype = msg.get("event_type", "")
            if etype == event_type:
                return msg
            # Print other events for debugging
            print(f"  ← event: {etype}")
        except asyncio.TimeoutError:
            break
    return None


async def smoke_test():
    print("=" * 60)
    print("🎨 NEXUS CANVAS SMOKE TEST")
    print("=" * 60)

    # Connect as a test participant
    url = f"{SERVER}/ws/CanvasTest?type=human"
    print(f"\n1. Connecting to {url}...")

    async with websockets.connect(url) as ws:
        # Drain initial events (participant list, history, etc.)
        await asyncio.sleep(1)
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                msg = json.loads(raw)
                print(f"  ← startup: {msg.get('event_type', '?')}")
        except asyncio.TimeoutError:
            pass

        print("\n2. Sending paint commands (Phase 1: Background + shapes)...")
        await send_command(ws, "paint", {
            "entity": ENTITY,
            "commands": [
                # Create canvas with dark background
                {"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#0a0a1a"},
                # Starfield — scattered circles
                {"action": "draw_circle", "x": 120, "y": 80, "radius": 2, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 340, "y": 45, "radius": 1, "fill_color": "#aaaacc"},
                {"action": "draw_circle", "x": 560, "y": 120, "radius": 3, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 700, "y": 60, "radius": 2, "fill_color": "#ccccff"},
                {"action": "draw_circle", "x": 200, "y": 200, "radius": 1, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 650, "y": 180, "radius": 2, "fill_color": "#aaaaee"},
                {"action": "draw_circle", "x": 80, "y": 300, "radius": 1, "fill_color": "#ffffff"},
                {"action": "draw_circle", "x": 450, "y": 160, "radius": 2, "fill_color": "#ddddff"},
                # Teal serpent body — flowing curve via overlapping circles
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
                # Gold accent scales along body
                {"action": "draw_circle", "x": 210, "y": 340, "radius": 5, "fill_color": "#d4aa00"},
                {"action": "draw_circle", "x": 350, "y": 310, "radius": 5, "fill_color": "#d4aa00"},
                {"action": "draw_circle", "x": 480, "y": 360, "radius": 5, "fill_color": "#d4aa00"},
                {"action": "draw_circle", "x": 600, "y": 310, "radius": 5, "fill_color": "#d4aa00"},
            ]
        })

        # Wait for paint result
        result = await wait_for_event(ws, "paint_result", timeout=5)
        if result:
            data = result.get("data", {})
            print(f"  ✅ Paint result: iteration={data.get('iteration')}, "
                  f"dims={data.get('dimensions')}, error={data.get('error')}")
        else:
            print("  ⚠️  No paint_result received (check server logs)")

        # Wait for broadcast (canvas_update goes to ALL clients including us)
        update = await wait_for_event(ws, "canvas_update", timeout=5)
        if update:
            data = update.get("data", {})
            b64_len = len(data.get("base64", ""))
            print(f"  ✅ Canvas broadcast received: entity={data.get('entity')}, "
                  f"base64 length={b64_len}, iteration={data.get('iteration')}")
        else:
            print("  ⚠️  No canvas_update broadcast received")

        await asyncio.sleep(1)

        print("\n3. Sending Phase 2: Title text...")
        await send_command(ws, "paint", {
            "entity": ENTITY,
            "commands": [
                {"action": "draw_text", "x": 400, "y": 550, "text": "Reed Was Here",
                 "color": "#00d4aa", "font_size": 28},
                {"action": "draw_text", "x": 400, "y": 580, "text": "🐍 canvas smoke test — pipeline ALIVE",
                 "color": "#666688", "font_size": 14},
            ]
        })

        result2 = await wait_for_event(ws, "paint_result", timeout=5)
        if result2:
            data = result2.get("data", {})
            print(f"  ✅ Phase 2: iteration={data.get('iteration')}, error={data.get('error')}")

        update2 = await wait_for_event(ws, "canvas_update", timeout=5)
        if update2:
            data = update2.get("data", {})
            print(f"  ✅ Broadcast 2: base64 length={len(data.get('base64', ''))}")

        await asyncio.sleep(1)

        # --- Test: paint via chat message with <paint> tags ---
        print("\n4. Testing <paint> tag extraction from chat message...")
        chat_msg = {
            "content": "I feel like painting something. <paint>[{\"action\": \"draw_circle\", \"x\": 400, \"y\": 300, \"radius\": 60, \"fill_color\": \"#ff6b9d\", \"outline_color\": \"#ff2266\", \"outline_width\": 3}]</paint> A pink moon rising over the serpent.",
            "msg_type": "chat",
        }
        await ws.send(json.dumps(chat_msg))
        print("  → sent chat message with embedded <paint> tag")

        # This should trigger both a message broadcast AND a canvas_update
        await asyncio.sleep(2)
        events_seen = []
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=2)
                msg = json.loads(raw)
                etype = msg.get("event_type", "")
                events_seen.append(etype)
                if etype == "canvas_update":
                    data = msg.get("data", {})
                    print(f"  ✅ Canvas update from chat: iteration={data.get('iteration')}")
                elif etype == "message":
                    content = msg.get("data", {}).get("content", "")
                    has_paint = "<paint>" in content
                    print(f"  ✅ Chat message broadcast (paint tags stripped: {not has_paint}): "
                          f"{content[:80]}...")
        except asyncio.TimeoutError:
            pass

        if not events_seen:
            print("  ⚠️  No events received from chat paint test")

        print("\n5. Testing clear...")
        await send_command(ws, "clear_canvas", {"entity": ENTITY})
        clear_evt = await wait_for_event(ws, "canvas_clear", timeout=3)
        if clear_evt:
            print(f"  ✅ Canvas cleared: {clear_evt.get('data', {})}")
        else:
            print("  ⚠️  No canvas_clear event received")

        print("\n" + "=" * 60)
        print("🎨 SMOKE TEST COMPLETE")
        print("=" * 60)
        print("\nCheck the Godot UI — you should have seen:")
        print("  • Canvas panel showing a teal serpent on dark starfield")
        print("  • 'Reed Was Here' text appearing")
        print("  • A pink moon circle added via chat message")
        print("  • Canvas clearing at the end")
        print("\nIf Godot wasn't connected, the server still processed everything.")
        print("Check sessions/canvas/reed/ for saved PNGs.")


if __name__ == "__main__":
    asyncio.run(smoke_test())
