"""
OpenRouter Test with DeepSeek (fast, cheap paid model)
Use this if free models are too slow
"""

import os
import sys
from dotenv import load_dotenv

print("=" * 60)
print("OpenRouter Test - DeepSeek V3 ($0.27/M tokens)")
print("=" * 60)

load_dotenv()

# Import
from integrations.openrouter_backend import get_openrouter_client

print("\nInitializing...")
client = get_openrouter_client()

# Simple test
print("\nTesting with DeepSeek V3 (should be fast)...")
try:
    response = client.create(
        model="deepseek-v3",  # Cheap paid model
        messages=[{"role": "user", "content": "Say 'DeepSeek works!' and nothing else."}],
        max_tokens=50
    )
    result = response.content[0].text
    print(f"\n✓ SUCCESS: {result}")
    print(f"\nCost: ~$0.000016 (less than 2 cents per 1000 messages)")
except Exception as e:
    print(f"\n❌ FAILED: {e}")
