#!/usr/bin/env python
"""
exec_admin.py — Control panel for entity code execution.

Usage:
    python exec_admin.py status [entity]       Show entity status
    python exec_admin.py pending [entity]      Show pending approvals
    python exec_admin.py approve <entity> <id> Approve a pending execution
    python exec_admin.py approve-all <entity>  Approve all pending for entity
    python exec_admin.py deny <entity> <id> [reason]  Deny execution
    python exec_admin.py run <entity> <id>     Execute an approved item
    python exec_admin.py mode <entity> <mode>  Set supervised/autonomous
    python exec_admin.py grant <entity> <path> Grant write access
    python exec_admin.py revoke <entity> <path> Revoke write access
    python exec_admin.py log <entity> [n]      Show execution log
    python exec_admin.py access <entity> [n]   Show file access log
    python exec_admin.py snapshots <entity>    List snapshots
    python exec_admin.py revert <entity> <id>  Revert to snapshot
"""

import sys
import os
import json
import asyncio

# Add nexus dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_safety import (
    EntityPermissions, ExecutionLog, ApprovalQueue, SnapshotManager,
    entity_status, set_entity_mode, grant_write, revoke_write,
    get_exec_log, get_file_access_log, get_pending_approvals,
    approve_exec, deny_exec, approve_all_pending,
    revert_exec, list_snapshots,
)


def cmd_status(args):
    entity = args[0] if args else None
    if entity:
        print(entity_status(entity))
    else:
        for e in ["Kay", "Reed"]:
            print(entity_status(e))
            print()

def cmd_pending(args):
    entity = args[0] if args else None
    if entity:
        print(get_pending_approvals(entity))
    else:
        for e in ["Kay", "Reed"]:
            print(get_pending_approvals(e))

def cmd_approve(args):
    if len(args) < 2:
        print("Usage: approve <entity> <exec_id>")
        return
    print(approve_exec(args[0], args[1]))

def cmd_approve_all(args):
    if not args:
        print("Usage: approve-all <entity>")
        return
    print(approve_all_pending(args[0]))

def cmd_deny(args):
    if len(args) < 2:
        print("Usage: deny <entity> <exec_id> [reason]")
        return
    reason = " ".join(args[2:]) if len(args) > 2 else ""
    print(deny_exec(args[0], args[1], reason))

def cmd_run(args):
    """Execute an approved queued item."""
    if len(args) < 2:
        print("Usage: run <entity> <exec_id>")
        return
    from code_executor import execute_approved
    result = asyncio.run(execute_approved(args[0], args[1]))
    if result.get("success"):
        print(f"OK: Executed successfully in {result.get('execution_time', '?')}s")
        if result.get("stdout"):
            print(f"Output:\n{result['stdout'][:2000]}")
        if result.get("files_created"):
            print(f"Files created: {', '.join(result['files_created'])}")
    elif result.get("queued"):
        print(f"Still pending approval: {result.get('exec_id')}")
    else:
        print(f"FAIL: {result.get('error', 'unknown')}")

def cmd_mode(args):
    if len(args) < 2:
        print("Usage: mode <entity> <supervised|autonomous>")
        return
    print(set_entity_mode(args[0], args[1]))

def cmd_grant(args):
    if len(args) < 2:
        print("Usage: grant <entity> <path>")
        return
    print(grant_write(args[0], args[1]))

def cmd_revoke(args):
    if len(args) < 2:
        print("Usage: revoke <entity> <path>")
        return
    print(revoke_write(args[0], args[1]))

def cmd_log(args):
    entity = args[0] if args else "Kay"
    n = int(args[1]) if len(args) > 1 else 20
    print(get_exec_log(entity, n))

def cmd_access(args):
    entity = args[0] if args else "Kay"
    n = int(args[1]) if len(args) > 1 else 50
    entries = get_file_access_log(entity, n)
    if not entries:
        print(f"No file access log for {entity}.")
        return
    for e in entries:
        allowed = "✓" if e.get("allowed") else "✗ BLOCKED"
        print(f"  {allowed} [{e.get('timestamp', '?')[:19]}] "
              f"{e.get('action', '?')}: {e.get('path', '?')}")

def cmd_snapshots(args):
    entity = args[0] if args else "Kay"
    snaps = list_snapshots(entity)
    if not snaps:
        print(f"No snapshots for {entity}.")
        return
    print(f"=== Snapshots for {entity} ({len(snaps)}) ===")
    for s in snaps:
        print(f"  {s['exec_id']} — {s['file_count']} files ({s['created']})")

def cmd_revert(args):
    if len(args) < 2:
        print("Usage: revert <entity> <exec_id>")
        return
    result = revert_exec(args[0], args[1])
    if result.get("success"):
        print(f"OK: Reverted {args[0]} to snapshot {args[1]}")
        print(f"  Removed: {result.get('removed', [])}")
        print(f"  Restored: {result.get('restored', [])}")
    else:
        print(f"FAIL: {result.get('error', 'Failed')}")


COMMANDS = {
    "status": cmd_status,
    "pending": cmd_pending,
    "approve": cmd_approve,
    "approve-all": cmd_approve_all,
    "deny": cmd_deny,
    "run": cmd_run,
    "mode": cmd_mode,
    "grant": cmd_grant,
    "revoke": cmd_revoke,
    "log": cmd_log,
    "access": cmd_access,
    "snapshots": cmd_snapshots,
    "revert": cmd_revert,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        return

    COMMANDS[cmd](args)

if __name__ == "__main__":
    main()
