"""Test Kay's actual async startup including bridge init."""
import sys, os, traceback, asyncio
sys.path.insert(0, r"D:\Wrappers\nexus")
sys.path.insert(0, r"D:\Wrappers\Kay")
sys.path.insert(0, r"D:\Wrappers")
os.chdir(r"D:\Wrappers\Kay")

async def test():
    print("=== Testing Kay async startup ===")
    try:
        from nexus_kay import KayNexusClient
        client = KayNexusClient(server_url="ws://localhost:8765")
        print("[OK] Client created")
        
        print("[...] Calling _ensure_bridge() (this is where the crash likely is)...")
        await client._ensure_bridge()
        print("[OK] Bridge initialized successfully!")
        
    except Exception as e:
        print(f"\n[FAIL] {type(e).__name__}: {e}")
        traceback.print_exc()
    
    print("\n=== Done ===")

asyncio.run(test())
