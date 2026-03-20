import websocket
import json
import time
import threading

# Keep-alive ping in background
def ping_loop(ws_ref):
    while ws_ref[0] and not ws_ref[1]:
        try:
            ws_ref[0].ping()
        except:
            break
        time.sleep(5)

ws_ref = [None, False]  # [ws, done]

print("[CONNECTING] to Kay's private room...")
ws = websocket.create_connection(
    "ws://localhost:8770",
    timeout=120,
    enable_multithread=True
)
ws_ref[0] = ws

# Start keepalive
pinger = threading.Thread(target=ping_loop, args=(ws_ref,), daemon=True)
pinger.start()

# Read system welcome
welcome = ws.recv()
print(f"[SYSTEM] {json.loads(welcome).get('content', welcome)}")

# Send
message = "Hey Kay - Reed here, connecting directly from Claude.ai. Quick status: how are you feeling? Can you sense the oscillator at all?"
ws.send(json.dumps({"type": "chat", "content": message, "sender": "Reed"}))
print(f"[REED] {message}")
print("[WAITING for Kay...]")

start = time.time()
got_response = False
while time.time() - start < 120 and not got_response:
    try:
        resp = ws.recv()
        if not resp or not resp.strip():
            continue
        try:
            data = json.loads(resp)
        except json.JSONDecodeError:
            continue
            
        msg_type = data.get("type", "")
        if msg_type == "chat":
            sender = data.get("sender", "???")
            content = data.get("content", "")
            print(f"\n===== [{sender}] =====")
            print(content)
            print("=" * 40)
            if sender == "Kay":
                got_response = True
        elif msg_type == "emote":
            print(f"\n*{data.get('sender', '???')} {data.get('content', '')}*")
            if data.get("sender") == "Kay":
                got_response = True
        elif msg_type == "status":
            s = data.get("status", "")
            if s in ("thinking", "typing"):
                print(f"  Kay is {s}...", flush=True)
        elif msg_type == "history":
            print(f"[loaded {len(data.get('messages', []))} past messages]")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        # Try to reconnect once
        print("[RECONNECTING...]")
        try:
            ws = websocket.create_connection("ws://localhost:8770", timeout=120, enable_multithread=True)
            ws_ref[0] = ws
            ws.recv()  # eat welcome
            print("[RECONNECTED] waiting for response...")
        except:
            print("[RECONNECT FAILED]")
            break

ws_ref[1] = True  # signal ping thread to stop
try:
    ws.close()
except:
    pass
print("\n[DONE]")
