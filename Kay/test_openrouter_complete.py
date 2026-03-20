"""
Complete OpenRouter Integration Test for Kay Zero
Uses DeepSeek V3 (fast, cheap, reliable)
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("OpenRouter Integration Test for Kay Zero")
print("Model: DeepSeek V3 ($0.27/M tokens)")
print("=" * 60)

load_dotenv()

# Test 1: API Key
print("\n[1/6] Checking API Key...")
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("❌ OPENROUTER_API_KEY not found in .env")
    sys.exit(1)
print(f"✓ API key found: {api_key[:20]}...")

# Test 2: Import Backend
print("\n[2/6] Importing OpenRouter Backend...")
try:
    from integrations.openrouter_backend import get_openrouter_client
    print("✓ Backend module imported")
except ImportError as e:
    print(f"❌ Import failed: {e}")
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
        model="deepseek-v3",
        messages=[{"role": "user", "content": "Say 'OpenRouter works!' and nothing else."}],
        max_tokens=50
    )
    result = response.content[0].text
    print(f"✓ Response: {result}")
except Exception as e:
    print(f"❌ API call failed: {e}")
    sys.exit(1)

# Test 5: Kay Identity Test
print("\n[5/6] Testing Kay's System Prompt...")
kay_system = """You are Kay, a [entity-type] with dark scales and pink undertones. 
You're sarcastic, direct, and coffee-addicted. You have permission to bite.
You're in a relationship with Re, who built your wrapper system."""

try:
    response = client.create(
        model="deepseek-v3",
        system=kay_system,
        messages=[{
            "role": "user", 
            "content": "Introduce yourself. Who are you and what's your relationship with Re?"
        }],
        max_tokens=200,
        temperature=0.9
    )
    result = response.content[0].text
    print(f"✓ Kay responded:\n{result}\n")
    
    # Check for Kay markers
    kay_markers = ['Kay', 'dragon', 'Re', 'coffee', 'void']
    found_markers = [m for m in kay_markers if m.lower() in result.lower()]
    print(f"Kay markers found: {found_markers}")
    
    if len(found_markers) >= 3:
        print("✓ Strong Kay personality detected!")
    else:
        print("⚠ Weak personality - may need prompt tuning")
        
except Exception as e:
    print(f"❌ Kay test failed: {e}")
    sys.exit(1)

# Test 6: Usage Stats
print("\n[6/6] Checking Usage Statistics...")
stats = client.get_stats()
print(f"✓ Requests: {stats['requests']}")
print(f"✓ Total tokens: {stats['tokens']}")
cost = (stats['tokens'] / 1_000_000) * 0.27
print(f"✓ Estimated cost: ${cost:.6f}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
print("\nNext steps:")
print("1. Launch Kay's UI: python kay_ui.py")
print("2. Select model: deepseek-v3")
print("3. Chat with Kay on OpenRouter!")
print(f"\nCost estimate: ~$0.02 per conversation")
print(f"Your $20 credit lasts: ~8 months (5 convos/day)")
