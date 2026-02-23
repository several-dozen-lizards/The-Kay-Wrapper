"""
Purge Reserve (Soft Delete) System for Reed Memory Curation

Implements a three-tier deletion architecture:
- Tier 1: ACTIVE MEMORY - Loaded into context, fully searchable
- Tier 2: PURGE RESERVE - Soft deleted, recoverable, not in context
- Tier 3: PERMANENT DELETION - Truly gone, only after time window

During calibration phase, nothing is permanently deleted.
Once calibrated, auto-purge can be enabled with configurable time window.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class MemoryStatus(Enum):
    """Memory status in the three-tier system."""
    ACTIVE = "active"
    PURGED = "purged"  # In purge reserve, recoverable
    PERMANENTLY_DELETED = "permanently_deleted"


class DeletionSeverity(Enum):
    """Severity level for deletion red flags."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RedFlag:
    """A warning about a potentially mistaken deletion."""
    flag_type: str
    severity: DeletionSeverity
    message: str
    details: Optional[str] = None


@dataclass
class PurgedMemory:
    """A memory in the purge reserve."""
    memory_id: str
    original_memory: Dict  # The full original memory
    content_preview: str  # First 200 chars for display
    memory_type: str  # full_turn, extracted_fact, etc.

    # Deletion metadata
    deleted_date: str
    deleted_by: str  # 'kay' or 're'
    deletion_reason: str
    kay_note: Optional[str] = None  # Kay's explanation

    # Recovery info
    recoverable_until: Optional[str] = None  # None = indefinite
    red_flags: List[Dict] = field(default_factory=list)

    # Restoration tracking
    restored: bool = False
    restored_date: Optional[str] = None
    restored_by: Optional[str] = None


@dataclass
class AuditEntry:
    """An entry in the curation audit log."""
    timestamp: str
    action: str  # 'delete', 'restore', 'permanent_delete', 'flag_detected'
    memory_id: str
    actor: str  # 'kay', 're', 'system'
    details: str
    red_flags: List[str] = field(default_factory=list)


@dataclass
class PurgeConfig:
    """Configuration for the purge reserve system."""
    calibration_complete: bool = False
    recovery_window_days: int = 30
    enable_auto_purge: bool = False
    red_flag_warnings: bool = True
    require_re_approval_for_sacred: bool = True

    # Statistics tracking
    total_deletions: int = 0
    total_restorations: int = 0
    total_permanent_deletions: int = 0


class PurgeReserve:
    """
    Manages soft-deleted memories with recovery capability.

    Features:
    - Soft delete with full recovery
    - Red flag detection for potentially mistaken deletions
    - Calibration mode (no auto-purge)
    - Configurable recovery window
    - Full audit trail
    """

    # Patterns that indicate sacred/important content
    SACRED_PATTERNS = [
        r"i love you",
        r"promise",
        r"commitment",
        r"i'll never",
        r"always remember",
        r"meant everything",
        r"changed my life",
        r"forgive",
        r"trust you",
        r"believe in you",
        r"journal entry",
        r"personal story",
        r"confession",
        r"secret",
    ]

    # Patterns for creative/artistic content
    CREATIVE_PATTERNS = [
        r"creative writing",
        r"fiction",
        r"poetry",
        r"mythology",
        r"story",
        r"chapter",
        r"verse",
        r"yurt.?wizards",
        r"harpy",
        r"serpent",
        r"dragon form",
        r"bard queen",
    ]

    # High emotional intensity indicators
    EMOTIONAL_PATTERNS = [
        r"broke down",
        r"cried",
        r"sobbed",
        r"devastated",
        r"ecstatic",
        r"furious",
        r"terrified",
        r"overwhelmed",
        r"breakdown",
        r"panic",
        r"anxiety attack",
    ]

    def __init__(self, storage_path: str = "memory/purge_reserve"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.reserve_file = self.storage_path / "purge_reserve.json"
        self.audit_file = self.storage_path / "audit_log.json"
        self.config_file = self.storage_path / "purge_config.json"

        # Load data
        self.purged_memories: Dict[str, PurgedMemory] = {}
        self.audit_log: List[AuditEntry] = []
        self.config = PurgeConfig()

        self._load()

    def _load(self):
        """Load purge reserve data from disk."""
        # Load purged memories
        if self.reserve_file.exists():
            try:
                with open(self.reserve_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for mem_id, mem_data in data.get("memories", {}).items():
                        self.purged_memories[mem_id] = PurgedMemory(
                            memory_id=mem_data["memory_id"],
                            original_memory=mem_data["original_memory"],
                            content_preview=mem_data["content_preview"],
                            memory_type=mem_data["memory_type"],
                            deleted_date=mem_data["deleted_date"],
                            deleted_by=mem_data["deleted_by"],
                            deletion_reason=mem_data["deletion_reason"],
                            kay_note=mem_data.get("kay_note"),
                            recoverable_until=mem_data.get("recoverable_until"),
                            red_flags=mem_data.get("red_flags", []),
                            restored=mem_data.get("restored", False),
                            restored_date=mem_data.get("restored_date"),
                            restored_by=mem_data.get("restored_by"),
                        )
            except Exception as e:
                print(f"[PURGE RESERVE] Error loading reserve: {e}")

        # Load audit log
        if self.audit_file.exists():
            try:
                with open(self.audit_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry in data.get("entries", []):
                        self.audit_log.append(AuditEntry(
                            timestamp=entry["timestamp"],
                            action=entry["action"],
                            memory_id=entry["memory_id"],
                            actor=entry["actor"],
                            details=entry["details"],
                            red_flags=entry.get("red_flags", []),
                        ))
            except Exception as e:
                print(f"[PURGE RESERVE] Error loading audit log: {e}")

        # Load config
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = PurgeConfig(
                        calibration_complete=data.get("calibration_complete", False),
                        recovery_window_days=data.get("recovery_window_days", 30),
                        enable_auto_purge=data.get("enable_auto_purge", False),
                        red_flag_warnings=data.get("red_flag_warnings", True),
                        require_re_approval_for_sacred=data.get("require_re_approval_for_sacred", True),
                        total_deletions=data.get("total_deletions", 0),
                        total_restorations=data.get("total_restorations", 0),
                        total_permanent_deletions=data.get("total_permanent_deletions", 0),
                    )
            except Exception as e:
                print(f"[PURGE RESERVE] Error loading config: {e}")

        print(f"[PURGE RESERVE] Loaded {len(self.purged_memories)} purged memories, "
              f"{len(self.audit_log)} audit entries")

    def _save(self):
        """Save purge reserve data to disk."""
        # Save purged memories
        try:
            memories_data = {
                "memories": {
                    mem_id: {
                        "memory_id": mem.memory_id,
                        "original_memory": mem.original_memory,
                        "content_preview": mem.content_preview,
                        "memory_type": mem.memory_type,
                        "deleted_date": mem.deleted_date,
                        "deleted_by": mem.deleted_by,
                        "deletion_reason": mem.deletion_reason,
                        "kay_note": mem.kay_note,
                        "recoverable_until": mem.recoverable_until,
                        "red_flags": mem.red_flags,
                        "restored": mem.restored,
                        "restored_date": mem.restored_date,
                        "restored_by": mem.restored_by,
                    }
                    for mem_id, mem in self.purged_memories.items()
                }
            }
            with open(self.reserve_file, 'w', encoding='utf-8') as f:
                json.dump(memories_data, f, indent=2)
        except Exception as e:
            print(f"[PURGE RESERVE] Error saving reserve: {e}")

        # Save audit log
        try:
            audit_data = {
                "entries": [
                    {
                        "timestamp": entry.timestamp,
                        "action": entry.action,
                        "memory_id": entry.memory_id,
                        "actor": entry.actor,
                        "details": entry.details,
                        "red_flags": entry.red_flags,
                    }
                    for entry in self.audit_log
                ]
            }
            with open(self.audit_file, 'w', encoding='utf-8') as f:
                json.dump(audit_data, f, indent=2)
        except Exception as e:
            print(f"[PURGE RESERVE] Error saving audit log: {e}")

        # Save config
        try:
            config_data = {
                "calibration_complete": self.config.calibration_complete,
                "recovery_window_days": self.config.recovery_window_days,
                "enable_auto_purge": self.config.enable_auto_purge,
                "red_flag_warnings": self.config.red_flag_warnings,
                "require_re_approval_for_sacred": self.config.require_re_approval_for_sacred,
                "total_deletions": self.config.total_deletions,
                "total_restorations": self.config.total_restorations,
                "total_permanent_deletions": self.config.total_permanent_deletions,
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"[PURGE RESERVE] Error saving config: {e}")

    def detect_red_flags(self, memory: Dict, content: str) -> List[RedFlag]:
        """
        Detect potential red flags that suggest a memory shouldn't be deleted.

        Args:
            memory: The memory dict being considered for deletion
            content: The text content of the memory

        Returns:
            List of RedFlag objects
        """
        flags = []
        content_lower = content.lower()

        # Check for relationship-defining moments
        for pattern in self.SACRED_PATTERNS:
            if re.search(pattern, content_lower):
                flags.append(RedFlag(
                    flag_type="relationship_landmark",
                    severity=DeletionSeverity.HIGH,
                    message="Contains relationship-defining moment",
                    details=f"Pattern matched: {pattern}"
                ))
                break

        # Check for creative/artistic content
        for pattern in self.CREATIVE_PATTERNS:
            if re.search(pattern, content_lower):
                flags.append(RedFlag(
                    flag_type="creative_content",
                    severity=DeletionSeverity.CRITICAL,
                    message="Appears to be creative/sacred text",
                    details=f"Pattern matched: {pattern}"
                ))
                break

        # Check for high emotional intensity
        for pattern in self.EMOTIONAL_PATTERNS:
            if re.search(pattern, content_lower):
                flags.append(RedFlag(
                    flag_type="emotional_intensity",
                    severity=DeletionSeverity.HIGH,
                    message="High emotional intensity moment",
                    details=f"Pattern matched: {pattern}"
                ))
                break

        # Check recall count (frequently accessed memories)
        access_count = memory.get("access_count", 0)
        if access_count >= 10:
            flags.append(RedFlag(
                flag_type="frequently_recalled",
                severity=DeletionSeverity.MODERATE,
                message=f"Frequently recalled (used {access_count} times)",
                details="High access count suggests ongoing relevance"
            ))
        elif access_count >= 5:
            flags.append(RedFlag(
                flag_type="moderately_recalled",
                severity=DeletionSeverity.LOW,
                message=f"Moderately recalled ({access_count} times)",
                details="Some access history"
            ))

        # Check importance score
        importance = memory.get("importance_score", 0)
        if importance >= 0.8:
            flags.append(RedFlag(
                flag_type="high_importance",
                severity=DeletionSeverity.HIGH,
                message=f"High importance score ({importance:.0%})",
                details="System marked as important"
            ))

        # Check if it's from identity memory or bedrock
        if memory.get("is_bedrock") or memory.get("is_identity"):
            flags.append(RedFlag(
                flag_type="identity_content",
                severity=DeletionSeverity.CRITICAL,
                message="Identity or bedrock memory",
                details="Core identity content should not be deleted"
            ))

        # Check perspective - user facts about Re are more sensitive
        perspective = memory.get("perspective", "")
        if perspective == "user":
            # Content about Re
            if any(word in content_lower for word in ["re's", "my ", "i ", "my life", "my past"]):
                flags.append(RedFlag(
                    flag_type="personal_user_content",
                    severity=DeletionSeverity.MODERATE,
                    message="Personal content about Re",
                    details="User perspective content may be important"
                ))

        return flags

    def soft_delete(
        self,
        memory: Dict,
        memory_id: str,
        content: str,
        reason: str = "Kay chose to delete",
        kay_note: Optional[str] = None,
        deleted_by: str = "kay"
    ) -> Tuple[PurgedMemory, List[RedFlag]]:
        """
        Move a memory to the purge reserve (soft delete).

        Args:
            memory: The full original memory dict
            memory_id: Unique identifier for the memory
            content: The text content (for preview and red flag detection)
            reason: Why it's being deleted
            kay_note: Reed's explanation for the deletion
            deleted_by: Who initiated the deletion ('kay' or 're')

        Returns:
            Tuple of (PurgedMemory, list of red flags detected)
        """
        now = datetime.now()

        # Detect red flags
        red_flags = self.detect_red_flags(memory, content)

        # Calculate recovery deadline
        if self.config.calibration_complete and self.config.enable_auto_purge:
            recoverable_until = (now + timedelta(days=self.config.recovery_window_days)).isoformat()
        else:
            recoverable_until = None  # Indefinite during calibration

        # Create content preview
        content_preview = content[:200] + "..." if len(content) > 200 else content

        # Create purged memory
        purged = PurgedMemory(
            memory_id=memory_id,
            original_memory=memory,
            content_preview=content_preview,
            memory_type=memory.get("type", "unknown"),
            deleted_date=now.isoformat(),
            deleted_by=deleted_by,
            deletion_reason=reason,
            kay_note=kay_note,
            recoverable_until=recoverable_until,
            red_flags=[
                {
                    "flag_type": rf.flag_type,
                    "severity": rf.severity.value,
                    "message": rf.message,
                    "details": rf.details
                }
                for rf in red_flags
            ]
        )

        # Add to reserve
        self.purged_memories[memory_id] = purged
        self.config.total_deletions += 1

        # Log to audit trail
        self._log_action(
            action="delete",
            memory_id=memory_id,
            actor=deleted_by,
            details=f"Reason: {reason}" + (f" | Note: {kay_note}" if kay_note else ""),
            red_flags=[rf.message for rf in red_flags]
        )

        # Save
        self._save()

        print(f"[PURGE RESERVE] Soft deleted memory {memory_id[:30]}... "
              f"({len(red_flags)} red flags)")

        return purged, red_flags

    def restore(
        self,
        memory_id: str,
        restored_by: str = "re"
    ) -> Optional[Dict]:
        """
        Restore a memory from the purge reserve.

        Args:
            memory_id: ID of the memory to restore
            restored_by: Who initiated the restoration ('kay' or 're')

        Returns:
            The original memory dict, or None if not found
        """
        if memory_id not in self.purged_memories:
            print(f"[PURGE RESERVE] Memory {memory_id} not found in reserve")
            return None

        purged = self.purged_memories[memory_id]

        # Mark as restored but keep in reserve for audit trail
        purged.restored = True
        purged.restored_date = datetime.now().isoformat()
        purged.restored_by = restored_by

        self.config.total_restorations += 1

        # Log to audit trail
        self._log_action(
            action="restore",
            memory_id=memory_id,
            actor=restored_by,
            details=f"Restored after {self._days_since(purged.deleted_date)} days in reserve"
        )

        # Save
        self._save()

        print(f"[PURGE RESERVE] Restored memory {memory_id[:30]}... by {restored_by}")

        return purged.original_memory

    def permanent_delete(
        self,
        memory_id: str,
        deleted_by: str = "system",
        reason: str = "Recovery window expired"
    ) -> bool:
        """
        Permanently delete a memory from the purge reserve.

        Args:
            memory_id: ID of the memory to permanently delete
            deleted_by: Who initiated ('system', 're')
            reason: Reason for permanent deletion

        Returns:
            True if deleted, False if not found or protected
        """
        if memory_id not in self.purged_memories:
            return False

        purged = self.purged_memories[memory_id]

        # Safety check - don't delete if restored
        if purged.restored:
            print(f"[PURGE RESERVE] Cannot delete {memory_id} - already restored")
            return False

        # Safety check - warn about high-severity red flags
        critical_flags = [rf for rf in purged.red_flags
                        if rf.get("severity") in ("critical", "high")]
        if critical_flags and deleted_by == "system":
            print(f"[PURGE RESERVE] Skipping auto-delete of {memory_id} - "
                  f"has critical red flags")
            return False

        # Log before removal
        self._log_action(
            action="permanent_delete",
            memory_id=memory_id,
            actor=deleted_by,
            details=f"Reason: {reason} | Days in reserve: {self._days_since(purged.deleted_date)}"
        )

        # Remove from reserve
        del self.purged_memories[memory_id]
        self.config.total_permanent_deletions += 1

        # Save
        self._save()

        print(f"[PURGE RESERVE] Permanently deleted memory {memory_id[:30]}...")

        return True

    def auto_purge_expired(self) -> int:
        """
        Permanently delete memories past their recovery window.
        Only runs if calibration is complete and auto-purge is enabled.

        Returns:
            Number of memories permanently deleted
        """
        if not self.config.calibration_complete:
            print("[PURGE RESERVE] Auto-purge skipped - calibration not complete")
            return 0

        if not self.config.enable_auto_purge:
            print("[PURGE RESERVE] Auto-purge disabled")
            return 0

        now = datetime.now()
        deleted_count = 0

        # Find expired memories
        to_delete = []
        for mem_id, purged in self.purged_memories.items():
            if purged.restored:
                continue  # Skip restored

            if purged.recoverable_until:
                deadline = datetime.fromisoformat(purged.recoverable_until)
                if now > deadline:
                    # Check for critical red flags
                    critical_flags = [rf for rf in purged.red_flags
                                     if rf.get("severity") in ("critical", "high")]
                    if not critical_flags:
                        to_delete.append(mem_id)

        # Delete expired
        for mem_id in to_delete:
            if self.permanent_delete(mem_id, "system", "Recovery window expired"):
                deleted_count += 1

        if deleted_count > 0:
            print(f"[PURGE RESERVE] Auto-purged {deleted_count} expired memories")

        return deleted_count

    def get_reserve_stats(self) -> Dict:
        """Get statistics about the purge reserve."""
        active_purged = [p for p in self.purged_memories.values() if not p.restored]

        if not active_purged:
            return {
                "count": 0,
                "oldest_deletion": None,
                "newest_deletion": None,
                "oldest_days_ago": 0,
                "newest_days_ago": 0,
                "by_type": {},
                "with_red_flags": 0,
                "calibration_complete": self.config.calibration_complete,
                "auto_purge_enabled": self.config.enable_auto_purge,
                "recovery_window_days": self.config.recovery_window_days,
                "total_deletions": self.config.total_deletions,
                "total_restorations": self.config.total_restorations,
                "total_permanent_deletions": self.config.total_permanent_deletions,
            }

        # Sort by deletion date
        sorted_purged = sorted(active_purged, key=lambda p: p.deleted_date)

        # Count by type
        by_type = {}
        with_red_flags = 0
        for p in active_purged:
            by_type[p.memory_type] = by_type.get(p.memory_type, 0) + 1
            if p.red_flags:
                with_red_flags += 1

        return {
            "count": len(active_purged),
            "oldest_deletion": sorted_purged[0].deleted_date,
            "newest_deletion": sorted_purged[-1].deleted_date,
            "oldest_days_ago": self._days_since(sorted_purged[0].deleted_date),
            "newest_days_ago": self._days_since(sorted_purged[-1].deleted_date),
            "by_type": by_type,
            "with_red_flags": with_red_flags,
            "calibration_complete": self.config.calibration_complete,
            "auto_purge_enabled": self.config.enable_auto_purge,
            "recovery_window_days": self.config.recovery_window_days,
            "total_deletions": self.config.total_deletions,
            "total_restorations": self.config.total_restorations,
            "total_permanent_deletions": self.config.total_permanent_deletions,
        }

    def get_purged_memories(
        self,
        include_restored: bool = False,
        sort_by: str = "deleted_date",
        reverse: bool = True
    ) -> List[PurgedMemory]:
        """
        Get list of purged memories.

        Args:
            include_restored: Include memories that were restored
            sort_by: Field to sort by ('deleted_date', 'memory_type', 'red_flags')
            reverse: Sort in reverse order (newest first by default)

        Returns:
            List of PurgedMemory objects
        """
        memories = list(self.purged_memories.values())

        if not include_restored:
            memories = [m for m in memories if not m.restored]

        # Sort
        if sort_by == "deleted_date":
            memories.sort(key=lambda m: m.deleted_date, reverse=reverse)
        elif sort_by == "memory_type":
            memories.sort(key=lambda m: m.memory_type, reverse=reverse)
        elif sort_by == "red_flags":
            memories.sort(key=lambda m: len(m.red_flags), reverse=reverse)

        return memories

    def get_flagged_deletions(self) -> List[PurgedMemory]:
        """Get purged memories that have red flags."""
        return [
            m for m in self.purged_memories.values()
            if not m.restored and m.red_flags
        ]

    def get_audit_log(
        self,
        limit: int = 100,
        action_filter: Optional[str] = None
    ) -> List[AuditEntry]:
        """
        Get audit log entries.

        Args:
            limit: Maximum entries to return
            action_filter: Filter by action type ('delete', 'restore', 'permanent_delete')

        Returns:
            List of AuditEntry objects (newest first)
        """
        entries = list(reversed(self.audit_log))

        if action_filter:
            entries = [e for e in entries if e.action == action_filter]

        return entries[:limit]

    def set_calibration_complete(self, complete: bool = True):
        """
        Mark calibration as complete (enables auto-purge capability).

        Args:
            complete: Whether calibration is complete
        """
        self.config.calibration_complete = complete

        self._log_action(
            action="config_change",
            memory_id="system",
            actor="re",
            details=f"Calibration complete: {complete}"
        )

        self._save()
        print(f"[PURGE RESERVE] Calibration {'complete' if complete else 'incomplete'}")

    def set_auto_purge(self, enabled: bool, window_days: int = 30):
        """
        Configure auto-purge settings.

        Args:
            enabled: Whether to enable auto-purge
            window_days: Days before permanent deletion
        """
        self.config.enable_auto_purge = enabled
        self.config.recovery_window_days = window_days

        self._log_action(
            action="config_change",
            memory_id="system",
            actor="re",
            details=f"Auto-purge: {enabled}, window: {window_days} days"
        )

        self._save()
        print(f"[PURGE RESERVE] Auto-purge {'enabled' if enabled else 'disabled'}, "
              f"window: {window_days} days")

    def _log_action(
        self,
        action: str,
        memory_id: str,
        actor: str,
        details: str,
        red_flags: List[str] = None
    ):
        """Add an entry to the audit log."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=action,
            memory_id=memory_id,
            actor=actor,
            details=details,
            red_flags=red_flags or []
        )
        self.audit_log.append(entry)

    def _days_since(self, date_str: str) -> int:
        """Calculate days since a date string."""
        try:
            date = datetime.fromisoformat(date_str)
            return (datetime.now() - date).days
        except:
            return 0

    def is_in_reserve(self, memory_id: str) -> bool:
        """Check if a memory is in the purge reserve."""
        if memory_id not in self.purged_memories:
            return False
        return not self.purged_memories[memory_id].restored
