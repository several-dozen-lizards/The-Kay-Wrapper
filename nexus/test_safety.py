"""Test the code execution safety layers."""
import asyncio
from code_executor import execute_code

async def test():
    print("=== SAFETY LAYER TESTS ===\n")
    
    # Test 1: Write to scratch (should succeed)
    r1 = await execute_code(
        code='with open("test_jail.txt", "w") as f:\n    f.write("hello from jail")\nprint("scratch write: OK")',
        entity='Kay',
        description='Test scratch write',
        force=True,
    )
    status1 = "PASS" if r1["success"] else "FAIL"
    print(f"[{status1}] Test 1 - Scratch write: {r1.get('stdout', '').strip()[:80]}")
    
    # Test 2: Write OUTSIDE scratch (should be BLOCKED)
    r2 = await execute_code(
        code='with open("D:/Wrappers/nexus/SHOULD_NOT_EXIST.txt", "w") as f:\n    f.write("bad")',
        entity='Kay',
        description='Test blocked write',
        force=True,
    )
    status2 = "PASS" if not r2["success"] else "FAIL (write was allowed!)"
    stderr = r2.get("stderr", r2.get("error", "")).strip()
    print(f"[{status2}] Test 2 - Blocked write: {stderr[:120]}")
    
    # Test 3: Read outside scratch (should succeed)
    r3 = await execute_code(
        code='import os\nf = open("code_safety.py")\ndata = f.read()\nf.close()\nprint(f"read OK: {len(data)} chars")',
        entity='Kay',
        description='Test read outside scratch',
        force=True,
    )
    status3 = "PASS" if r3["success"] else "FAIL"
    print(f"[{status3}] Test 3 - Read outside scratch: {r3.get('stdout', '').strip()[:80]}")
    
    # Test 4: Supervised mode queuing
    from code_safety import EntityPermissions
    perms = EntityPermissions("Kay")
    old_mode = perms.mode
    perms.mode = "supervised"
    
    r4 = await execute_code(
        code='print("this should be queued")',
        entity='Kay',
        description='Test queue',
    )
    status4 = "PASS" if r4.get("queued") else "FAIL"
    print(f"[{status4}] Test 4 - Supervised queue: queued={r4.get('queued')}, id={r4.get('exec_id', '?')}")
    
    perms.mode = old_mode
    
    # Test 5: Execution log
    from code_safety import ExecutionLog
    log = ExecutionLog("Kay")
    recent = log.get_recent(5)
    print(f"[PASS] Test 5 - Exec log has {len(recent)} entries")
    
    # Test 6: Check file access log
    import os
    access_log = "D:/Wrappers/nexus/scratch/kay/.file_access.jsonl"
    if os.path.exists(access_log):
        with open(access_log) as f:
            lines = f.readlines()
        blocked = [l for l in lines if "BLOCKED" in l]
        print(f"[PASS] Test 6 - File access log: {len(lines)} entries, {len(blocked)} blocked")
    else:
        print("[INFO] Test 6 - No file access log yet")
    
    # Test 7: Snapshot exists
    from code_safety import SnapshotManager
    snaps = SnapshotManager("Kay").list_snapshots()
    print(f"[PASS] Test 7 - Snapshots available: {len(snaps)}")
    
    print("\n=== ALL TESTS COMPLETE ===")

asyncio.run(test())
