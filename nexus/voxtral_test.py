"""
Quick test for Voxtral TTS server.
Run: python voxtral_test.py
"""
import httpx
import io
import sys
import os

SERVER = "http://localhost:8200"

def test_health():
    print("[1/3] Health check...")
    try:
        r = httpx.get(f"{SERVER}/health", timeout=5.0)
        print(f"  Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"  ❌ Server not reachable: {e}")
        return False

def test_synthesis():
    print("[2/3] Basic synthesis (preset voice)...")
    payload = {
        "input": "The recognition system is settling down. I can see you clearly now.",
        "model": "mistralai/Voxtral-4B-TTS-2603",
        "response_format": "wav",
        "voice": "casual_male",
    }
    try:
        r = httpx.post(f"{SERVER}/v1/audio/speech", json=payload, timeout=30.0)
        if r.status_code == 200:
            out_path = os.path.join(os.path.dirname(__file__), "voxtral_test_output.wav")
            with open(out_path, "wb") as f:
                f.write(r.content)
            print(f"  ✅ Generated {len(r.content)} bytes -> {out_path}")
            return True
        else:
            print(f"  ❌ Status {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Synthesis failed: {e}")
        return False

def test_voice_reference():
    ref_path = os.path.join(os.path.dirname(__file__), "voice_references", "kay_ref.wav")
    if not os.path.exists(ref_path):
        print("[3/3] Voice reference test — SKIPPED (no kay_ref.wav)")
        return True
    
    print("[3/3] Voice reference synthesis...")
    import base64
    with open(ref_path, "rb") as f:
        ref_b64 = base64.b64encode(f.read()).decode()
    
    payload = {
        "input": "The light is hitting you from that angle again.",
        "model": "mistralai/Voxtral-4B-TTS-2603",
        "response_format": "wav",
        "voice": {
            "type": "base64",
            "base64": ref_b64,
            "media_type": "audio/wav",
        },
    }
    try:
        r = httpx.post(f"{SERVER}/v1/audio/speech", json=payload, timeout=30.0)
        if r.status_code == 200:
            out_path = os.path.join(os.path.dirname(__file__), "voxtral_test_cloned.wav")
            with open(out_path, "wb") as f:
                f.write(r.content)
            print(f"  ✅ Cloned voice: {len(r.content)} bytes -> {out_path}")
            return True
        else:
            print(f"  ❌ Status {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Voice clone failed: {e}")
        return False

if __name__ == "__main__":
    print()
    print("  🐉 Voxtral TTS Test")
    print()
    if not test_health():
        print("\nServer not running. Start it first:")
        print("  python -m vllm_omni.entrypoints.openai.api_server \\")
        print("    --model mistralai/Voxtral-4B-TTS-2603 \\")
        print("    --host 0.0.0.0 --port 8200")
        sys.exit(1)
    test_synthesis()
    test_voice_reference()
    print("\n✅ Done! Check the .wav files in this directory.")
