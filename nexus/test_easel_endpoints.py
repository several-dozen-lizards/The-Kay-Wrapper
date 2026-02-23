"""Quick test of easel REST endpoints — latest, history, load."""
import asyncio
import json
import httpx

SERVER = "http://127.0.0.1:8765"

async def main():
    async with httpx.AsyncClient() as client:
        print("=== Testing Easel Endpoints ===\n")

        # 1. Get latest canvas for Reed
        print("1. GET /canvas/reed/latest")
        r = await client.get(f"{SERVER}/canvas/reed/latest")
        data = r.json()
        print(f"   has_canvas: {data.get('has_canvas')}")
        if data.get("has_canvas"):
            print(f"   filename: {data.get('filename')}")
            print(f"   dimensions: {data.get('dimensions')}")
            print(f"   base64 length: {len(data.get('base64', ''))}")
        print()

        # 2. Get history
        print("2. GET /canvas/reed/history")
        r = await client.get(f"{SERVER}/canvas/reed/history")
        data = r.json()
        saves = data.get("saves", [])
        print(f"   {len(saves)} saved iterations")
        for s in saves[-5:]:  # show last 5
            print(f"   - {s['filename']} ({s['size']} bytes)")
        print()

        # 3. Load the first save (if any)
        if saves:
            fname = saves[0]["filename"]
            print(f"3. POST /canvas/reed/load/{fname}")
            r = await client.post(f"{SERVER}/canvas/reed/load/{fname}")
            data = r.json()
            print(f"   loaded: {data.get('loaded')}")
            print(f"   dimensions: {data.get('dimensions')}")
            if data.get("error"):
                print(f"   ERROR: {data['error']}")
        else:
            print("3. (no saves to load)")

        print("\n✅ Done")

asyncio.run(main())
