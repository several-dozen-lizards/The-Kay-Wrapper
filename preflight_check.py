import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\Wrappers')

# 1. httpx (used by ollama helper)
try:
    import httpx
    print("✅ httpx available")
except ImportError:
    print("❌ httpx NOT installed — ollama calls will fail!")

# 2. visual_presence imports
try:
    from shared.room.visual_presence import compute_visual_pressure, classify_activity, get_visual_felt_quality
    print("✅ visual_presence imports OK")
    # Quick functional test
    assert classify_activity("typing at desk") == "typing"
    assert classify_activity("sleeping") == "sleeping"
    assert classify_activity("") == "present"
    assert classify_activity("running", is_animal=True) == "cat_active"
    print("  ✅ classify_activity works")
    
    # Test with mock scene state
    class MockScene:
        people_present = {"Re": {"activity": "typing at desk"}}
        animals_present = {"Chrome": {"location": "running across room"}}
    
    p = compute_visual_pressure(MockScene())
    print(f"  ✅ compute_visual_pressure: gamma={p['gamma']:.3f} beta={p['beta']:.3f} theta={p['theta']:.3f}")
    assert p['gamma'] > 0, "Re typing should push gamma"
    
    felt = get_visual_felt_quality(MockScene())
    print(f"  ✅ get_visual_felt_quality: '{felt[:60]}...'")
except Exception as e:
    print(f"❌ visual_presence error: {e}")

# 3. attention_focus imports
try:
    from shared.room.attention_focus import AttentionFocus
    af = AttentionFocus()
    print(f"✅ attention_focus: {af}")
    
    # Test event handlers
    af.on_message_received(from_human=True)
    assert af.focus > 0.5, f"After message, focus should be outward but is {af.focus}"
    print(f"  ✅ on_message_received → focus={af.focus:.2f}")
    
    af.on_activity_started("painting")
    assert af.focus < 0.5, f"After painting, focus should be inward but is {af.focus}"
    print(f"  ✅ on_activity_started → focus={af.focus:.2f}")
    
    hint = af.get_prompt_hint()
    print(f"  ✅ get_prompt_hint: '{hint}'")
except Exception as e:
    print(f"❌ attention_focus error: {e}")

# 4. Check ollama connectivity
try:
    resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
    models = [m['name'] for m in resp.json().get('models', [])]
    if 'dolphin-mistral:7b' in models:
        print("✅ ollama running, dolphin-mistral:7b available")
    else:
        print(f"⚠️  ollama running but dolphin-mistral:7b not found. Models: {models}")
except Exception as e:
    print(f"❌ ollama not reachable: {e}")

# 5. Quick test of the ollama helper pattern
try:
    resp = httpx.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "dolphin-mistral:7b",
            "messages": [
                {"role": "system", "content": "Say 'OK' and nothing else."},
                {"role": "user", "content": "test"},
            ],
            "max_tokens": 10,
            "temperature": 0.0,
        },
        timeout=15.0,
    )
    result = resp.json()["choices"][0]["message"]["content"].strip()
    print(f"✅ ollama test call returned: '{result}'")
except Exception as e:
    print(f"❌ ollama test call failed: {e}")

print("\n" + "=" * 50)
print("  PRE-FLIGHT COMPLETE")
print("=" * 50)
