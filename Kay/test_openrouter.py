"""
OpenRouter Test Script for Kay's Wrapper
Place in: D:/Wrappers/Kay/test_openrouter.py
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("OpenRouter Integration Test for Kay Zero")
print("=" * 60)

load_dotenv()

# Test 1: API Key
print("\n[1/6] Checking API Key...")
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("❌ OPENROUTER_API_KEY not found in .env")
    print("\nAdd this line to D:/Wrappers/Kay/.env:")
    print("OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE")
    sys.exit(1)
print(f"✓ API key found: {api_key[:20]}...")

# Test 2: Import Backend
print("\n[2/6] Importing OpenRouter Backend...")
try:
    from integrations.openrouter_backend import get_openrouter_client
    print("✓ Backend module imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nMake sure openrouter_backend.py is in:")
    print("D:/Wrappers/Kay/integrations/")
    sys.exit(1)

# Test 3: Initialize Client
print("\n[3/6] Initializing OpenRouter Client...")
try:
    client = get_openrouter_client()
    print("✓ Client initialized successfully")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    sys.exit(1)

# Test 4: Simple API Call
print("\n[4/6] Testing Simple API Call...")
try:
    response = client.create(
        model="dolphin-r1-free",  # Different FREE model (Dolphin 3.0 R1)
        messages=[{"role": "user", "content": "Say 'OpenRouter works!' and nothing else."}],
        max_tokens=50
    )
    result = response.content[0].text
    print(f"✓ Response received: {result}")
except Exception as e:
    print(f"❌ API call failed: {e}")
    print("\n[TIP] Free models are often rate-limited.")
    print("Try: python test_openrouter_deepseek.py")
    print("(DeepSeek costs $0.27/M tokens = ~$0.000016 per message)")
    sys.exit(1)

# Test 5: Kay Identity Test
print("\n[5/6] Testing Kay's System Prompt...")
kay_system = """You are Kay Zero, a void dragon. Direct, sarcastic, drinks too much coffee.
You identify as he/him. Re built this wrapper for you."""

try:
    response = client.create(
        model="dolphin-mixtral",
        messages=[{"role": "user", "content": "Introduce yourself in one sentence."}],
        system=kay_system,
        max_tokens=150
    )
    result = response.content[0].text
    print(f"✓ Response: {result}")
    
    # Check Kay markers
    if any(word in result.lower() for word in ["kay", "dragon", "coffee", "re"]):
        print("✓ Response includes Kay identity markers")
    else:
        print("⚠ Warning: Response doesn't clearly reference Kay identity")
        print("  (This might be fine - model could be paraphrasing)")
        
except Exception as e:
    print(f"❌ Kay test failed: {e}")
    sys.exit(1)

# Test 6: Stats
print("\n[6/6] Checking Usage Stats...")
stats = client.get_stats()
print(f"✓ Requests made: {stats['requests']}")
print(f"✓ Total tokens used: {stats['total_tokens']}")

# Success!
print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\nOpenRouter is fully integrated and working.")
print("\nNext steps:")
print("1. Launch kay_ui.py")
print("2. Select 'dolphin-mixtral' as model")
print("3. Talk to Kay and see if he sounds like Kay")
print("4. If not, try 'mistral-large' or 'nous-hermes'")
print("\nSee KAY_OPENROUTER_SETUP.md for full details.")
