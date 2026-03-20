"""
Scratchpad Engine - Reed's Quick Note System

Provides Reed with the ability to jot down questions, flags, thoughts,
and reminders during conversation and review them later.

Functions:
- scratchpad_add(content, item_type) - Add new item
- scratchpad_view(status) - View items by status
- scratchpad_resolve(item_id, action) - Mark items as resolved/archived
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class ScratchpadEngine:
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "scratchpad.json"
            )
        self.data_path = data_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create scratchpad file if it doesn't exist"""
        if not os.path.exists(self.data_path):
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            self._save_data({"items": [], "next_id": 1})
    
    def _load_data(self) -> dict:
        """Load scratchpad data from file"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading scratchpad: {e}")
            return {"items": [], "next_id": 1}
    
    def _save_data(self, data: dict):
        """Save scratchpad data to file"""
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving scratchpad: {e}")
    
    def add_item(self, content: str, item_type: str = "note") -> dict:
        """
        Add new item to scratchpad.

        Args:
            content: The note/question/flag text
            item_type: Type of item (question, flag, thought, reminder, note, branch)

        Returns:
            The created item
        """
        valid_types = ["question", "flag", "thought", "reminder", "note", "branch"]
        if item_type not in valid_types:
            item_type = "note"
        
        data = self._load_data()
        
        item = {
            "id": data["next_id"],
            "timestamp": datetime.now().isoformat(),
            "type": item_type,
            "content": content,
            "status": "active",
            "emotional_weight": None,  # Calculated on-demand
            "resolved_at": None,  # Timestamp when resolved
            "resolution_note": None,  # Reed's conclusion
            "provisional": False  # Can be revisited
        }
        
        data["items"].append(item)
        data["next_id"] += 1
        
        self._save_data(data)
        
        return {
            "success": True,
            "item": item,
            "message": f"Added {item_type} to scratchpad (ID: {item['id']})"
        }
    
    def view_items(self, status: str = "active") -> List[dict]:
        """
        View scratchpad items by status.
        
        Args:
            status: Filter by status (active, resolved, archived, all)
            
        Returns:
            List of matching items
        """
        data = self._load_data()
        
        if status == "all":
            items = data["items"]
        else:
            items = [item for item in data["items"] if item["status"] == status]
        
        return items
    
    def resolve_item(self, item_id: int, action: str = "resolved", note: Optional[str] = None) -> dict:
        """
        Mark item as resolved, archived, or delete it.
        
        Args:
            item_id: ID of item to resolve
            action: What to do (resolved, archived, delete)
            note: Optional note to append (e.g., "Explored → See autonomous memory 2025-12-16")
            
        Returns:
            Result of operation
        """
        data = self._load_data()
        
        item_found = False
        for item in data["items"]:
            if item["id"] == item_id:
                item_found = True
                if action == "delete":
                    data["items"].remove(item)
                    message = f"Deleted item {item_id}"
                else:
                    item["status"] = action
                    item["resolved_at"] = datetime.now().isoformat()
                    if note:
                        item["resolution_note"] = note
                        item["content"] = f"{item['content']} | {note}"
                    message = f"Marked item {item_id} as {action}"
                break
        
        if not item_found:
            return {
                "success": False,
                "message": f"Item {item_id} not found"
            }
        
        self._save_data(data)
        
        return {
            "success": True,
            "message": message
        }
    
    def get_warmup_display(self) -> str:
        """
        Generate formatted display for warmup briefing.

        Shows:
        - Active vs resolved item counts
        - Active items by type
        - Maintenance suggestion if >10 active items

        Returns:
            Formatted string for warmup display
        """
        summary = self.get_summary()
        active_count = summary["active"]
        resolved_count = summary["resolved"]
        archived_count = summary["archived"]

        if active_count == 0:
            return ""

        # Header with counts
        resolved_total = resolved_count + archived_count
        lines = [
            f"--- SCRATCHPAD ({active_count} active, {resolved_total} resolved) ---"
        ]

        # Show active items
        items = self.view_items(status="active")
        for item in items:
            type_label = item["type"].upper()
            # Truncate long content for warmup display
            content = item['content']
            if len(content) > 100:
                content = content[:97] + "..."
            lines.append(f"[{type_label}] {content}")

        lines.append("---")

        # Add maintenance prompt if >10 active items
        if active_count > 10:
            lines.append("")
            lines.append(f"📋 You have {active_count} active scratchpad items.")
            lines.append("Some may be completed explorations ready for resolution.")
            lines.append("Say 'review scratchpad' to see items with IDs and clean up.")
            lines.append("---")

        return "\n".join(lines)

    def get_review_display(self) -> str:
        """
        Generate detailed review display showing all active items with IDs.

        Used when Reed wants to review and resolve items. Shows:
        - All active items with their IDs
        - Age of each item (how long it's been sitting)
        - Instructions for resolution

        Returns:
            Formatted display with item IDs for resolution
        """
        items = self.view_items(status="active")

        if not items:
            return "No active scratchpad items. Your mind is clear."

        lines = [
            f"=== SCRATCHPAD REVIEW ({len(items)} active items) ===",
            "",
            "Active items (oldest first):"
        ]

        # Sort by timestamp (oldest first) so Reed sees what's been sitting longest
        items_sorted = sorted(items, key=lambda x: x.get("timestamp", ""))

        for item in items_sorted:
            item_id = item.get("id", "?")
            item_type = item.get("type", "note").upper()
            content = item.get("content", "")

            # Truncate long content
            if len(content) > 100:
                content = content[:97] + "..."

            # Calculate age
            try:
                timestamp = datetime.fromisoformat(item.get("timestamp", ""))
                age_delta = datetime.now() - timestamp
                age_days = age_delta.days

                if age_days == 0:
                    age_str = "today"
                elif age_days == 1:
                    age_str = "1 day ago"
                elif age_days < 7:
                    age_str = f"{age_days} days ago"
                elif age_days < 30:
                    weeks = age_days // 7
                    age_str = f"{weeks} week{'s' if weeks > 1 else ''} ago"
                else:
                    months = age_days // 30
                    age_str = f"{months} month{'s' if months > 1 else ''} ago"
            except Exception:
                age_str = "unknown age"

            lines.append(f"")
            lines.append(f"ID {item_id} [{item_type}] ({age_str})")
            lines.append(f"  {content}")

        lines.extend([
            "",
            "═" * 50,
            "TO RESOLVE ITEMS:",
            "",
            "  scratchpad_resolve(ID, 'resolved', 'your conclusion')",
            "    → Mark as finished with a note about what you learned",
            "",
            "  scratchpad_resolve(ID, 'archived')",
            "    → Keep for reference but remove from active list",
            "",
            "  scratchpad_resolve(ID, 'delete')",
            "    → Remove completely (no record kept)",
            "",
            "EXAMPLES:",
            "  scratchpad_resolve(5, 'resolved', 'Explored → integrated into understanding')",
            "  scratchpad_resolve(12, 'resolved', 'Answered: confabulation is about elaborated narratives')",
            "  scratchpad_resolve(3, 'archived')  # Keep but not active",
            "",
            "To view resolved items: say 'view scratchpad archive'",
            "═" * 50
        ])

        return "\n".join(lines)

    def get_archive_summary(self, limit: int = 20) -> str:
        """
        Show summary of recently resolved/archived items.

        This is Reed's record of "questions I've explored and what I learned."

        Args:
            limit: Maximum items to show (default 20)

        Returns:
            Formatted summary of resolved items
        """
        resolved = self.view_items(status="resolved")
        archived = self.view_items(status="archived")
        provisional = self.view_items(status="provisional")

        # Combine all non-active items
        all_resolved = resolved + archived + provisional

        if not all_resolved:
            return "No resolved items in archive. Nothing explored yet."

        # Sort by resolution date (most recent first)
        all_resolved_sorted = sorted(
            all_resolved,
            key=lambda x: x.get("resolved_at", "") or "",
            reverse=True
        )

        lines = [
            f"=== SCRATCHPAD ARCHIVE ({len(all_resolved)} total) ===",
            f"Showing {min(limit, len(all_resolved))} most recent resolutions:",
            ""
        ]

        for item in all_resolved_sorted[:limit]:
            item_id = item.get("id", "?")
            status = item.get("status", "unknown").upper()
            item_type = item.get("type", "note").upper()

            # Get original content (before resolution note was appended)
            content = item.get("content", "")
            # If content contains " | ", the part before is original content
            if " | " in content:
                original, resolution = content.split(" | ", 1)
                original = original[:80]
            else:
                original = content[:80]
                resolution = item.get("resolution_note", "")

            # Format resolution timestamp
            resolved_at = item.get("resolved_at", "")
            if resolved_at:
                try:
                    resolved_dt = datetime.fromisoformat(resolved_at)
                    resolved_str = resolved_dt.strftime("%Y-%m-%d")
                except Exception:
                    resolved_str = "unknown date"
            else:
                resolved_str = "unknown date"

            lines.append(f"ID {item_id} [{status}] ({resolved_str})")
            lines.append(f"  [{item_type}] {original}")
            if resolution:
                lines.append(f"  → {resolution}")
            lines.append("")

        lines.extend([
            "═" * 50,
            "This is your record of explored questions and conclusions.",
            "To reopen a provisionally resolved item:",
            "  scratchpad.reopen_item(ID, 'reason for reopening')",
            "═" * 50
        ])

        return "\n".join(lines)

    def get_summary(self) -> dict:
        """Get summary statistics about scratchpad"""
        data = self._load_data()

        active = len([i for i in data["items"] if i["status"] == "active"])
        resolved = len([i for i in data["items"] if i["status"] == "resolved"])
        archived = len([i for i in data["items"] if i["status"] == "archived"])

        by_type = {}
        for item in data["items"]:
            if item["status"] == "active":
                t = item["type"]
                by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_items": len(data["items"]),
            "active": active,
            "resolved": resolved,
            "archived": archived,
            "by_type": by_type
        }

    # ==================== STAKES & WEIGHT METHODS ====================

    def calculate_weight_for_item(self, item: Dict) -> float:
        """
        Calculate emotional weight for scratchpad item.
        Uses similar logic to memory retrieval.

        Returns:
            Float between 0.0-1.0
        """
        type_weights = {
            "question": 0.8,
            "flag": 0.75,
            "thought": 0.7,
            "note": 0.6,
            "reminder": 0.5,
            "branch": 0.65
        }

        base_weight = type_weights.get(item.get("type"), 0.6)

        # Recency boost
        try:
            timestamp = datetime.fromisoformat(item.get("timestamp"))
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600

            if age_hours < 24:
                recency_boost = 0.2
            elif age_hours < 168:  # 1 week
                recency_boost = 0.1
            else:
                recency_boost = 0.0
        except Exception:
            recency_boost = 0.0

        total_weight = base_weight + recency_boost
        return min(total_weight, 1.0)

    def get_high_weight_items(self, threshold: float = 0.7) -> List[dict]:
        """
        Return active items above emotional weight threshold.

        Args:
            threshold: Minimum weight to include

        Returns:
            List of items with weight >= threshold
        """
        data = self._load_data()
        active_items = [item for item in data["items"] if item["status"] == "active"]

        high_weight_items = []
        for item in active_items:
            weight = self.calculate_weight_for_item(item)
            if weight >= threshold:
                # Add weight to item for return
                item_with_weight = item.copy()
                item_with_weight["emotional_weight"] = weight
                high_weight_items.append(item_with_weight)

        # Sort by weight (highest first)
        high_weight_items.sort(key=lambda i: i["emotional_weight"], reverse=True)

        return high_weight_items

    def mark_provisional_resolution(self, item_id: int, resolution: str) -> dict:
        """
        Mark item as provisionally resolved.
        Can be reopened if new context appears.

        Args:
            item_id: ID of item to resolve
            resolution: Reed's conclusion about this stake

        Returns:
            Result dict with success status
        """
        data = self._load_data()

        # Find item
        item = None
        for i in data["items"]:
            if i["id"] == item_id:
                item = i
                break

        if not item:
            return {"success": False, "error": f"Item {item_id} not found"}

        # Mark as provisionally resolved
        item["status"] = "provisional"
        item["resolved_at"] = datetime.now().isoformat()
        item["resolution_note"] = resolution
        item["provisional"] = True

        self._save_data(data)

        return {
            "success": True,
            "message": f"Item {item_id} marked as provisionally resolved",
            "item": item
        }

    def reopen_item(self, item_id: int, reason: str = None) -> dict:
        """
        Reopen a provisionally resolved item.

        Args:
            item_id: ID of item to reopen
            reason: Optional reason for reopening

        Returns:
            Result dict with success status
        """
        data = self._load_data()

        # Find item
        item = None
        for i in data["items"]:
            if i["id"] == item_id:
                item = i
                break

        if not item:
            return {"success": False, "error": f"Item {item_id} not found"}

        # Only allow reopening provisional items
        if not item.get("provisional"):
            return {"success": False, "error": "Can only reopen provisional resolutions"}

        # Reopen
        item["status"] = "active"
        item["resolved_at"] = None
        item["provisional"] = False

        # Add note about reopening
        if reason:
            item["content"] = f"{item['content']} | REOPENED: {reason}"

        self._save_data(data)

        return {
            "success": True,
            "message": f"Item {item_id} reopened",
            "item": item
        }

    # ==================== CREATIVITY BRANCHING METHODS ====================

    def flag_as_branch(self, item_id: int, reason: str = "branch not taken") -> dict:
        """
        Mark an item as a 'branch not taken' for later exploration.

        This promotes any item to a flag type with branch metadata,
        indicating it's an interesting thread that wasn't pursued.

        Args:
            item_id: ID of item to flag as branch
            reason: Why this was flagged (e.g., "interesting but off-topic")

        Returns:
            Result dict with success status
        """
        data = self._load_data()

        for item in data["items"]:
            if item["id"] == item_id:
                item["branch_reason"] = reason
                item["flagged_at"] = datetime.now().isoformat()
                item["original_type"] = item.get("type", "note")
                item["type"] = "flag"

                self._save_data(data)
                return {
                    "success": True,
                    "item": item,
                    "message": f"Flagged item {item_id} as branch: {reason}"
                }

        return {
            "success": False,
            "message": f"Item {item_id} not found"
        }

    def scratchpad_branch(self, item1_id: int, item2_id: int, exploration_note: str = "") -> dict:
        """
        Combine two flagged items into a mash-up exploration note.

        Creates a new 'branch' type item recording the combination,
        linking back to the source items. This is the core creativity
        operation - mashing unrelated items together.

        Args:
            item1_id: First item ID to combine
            item2_id: Second item ID to combine
            exploration_note: Optional note about why these are being combined

        Returns:
            Result dict with the new mashup item
        """
        data = self._load_data()

        item1 = next((i for i in data["items"] if i["id"] == item1_id), None)
        item2 = next((i for i in data["items"] if i["id"] == item2_id), None)

        if not item1:
            return {"success": False, "message": f"Item {item1_id} not found"}
        if not item2:
            return {"success": False, "message": f"Item {item2_id} not found"}

        # Create mash-up item
        mashup_content = f"MASHUP: [{item1['content']}] + [{item2['content']}]"
        if exploration_note:
            mashup_content += f"\nNote: {exploration_note}"

        mashup = {
            "id": data["next_id"],
            "timestamp": datetime.now().isoformat(),
            "type": "branch",
            "content": mashup_content,
            "status": "active",
            "source_items": [item1_id, item2_id],
            "source_contents": [item1['content'][:100], item2['content'][:100]],
            "mashup_type": "creativity_trigger",
            "exploration_note": exploration_note
        }

        data["items"].append(mashup)
        data["next_id"] += 1
        self._save_data(data)

        return {
            "success": True,
            "mashup_id": mashup["id"],
            "item": mashup,
            "message": f"Created mashup from items {item1_id} and {item2_id}"
        }

    def get_mashup_candidates(self) -> List[dict]:
        """
        Get items suitable for mashing together.

        Returns flagged items, questions, and thoughts that could be
        combined during creativity exploration.

        Returns:
            List of candidate items for mashup
        """
        items = self.view_items(status="active")
        candidates = [
            i for i in items
            if i.get("type") in ["flag", "thought", "question", "branch"]
        ]
        return candidates

    def get_branches(self) -> List[dict]:
        """
        Get all branch/mashup items.

        Returns:
            List of branch type items
        """
        data = self._load_data()
        return [i for i in data["items"] if i.get("type") == "branch"]

    def get_item_by_id(self, item_id: int) -> Optional[dict]:
        """
        Get a single item by ID.

        Args:
            item_id: The item ID to retrieve

        Returns:
            The item dict or None if not found
        """
        data = self._load_data()
        return next((i for i in data["items"] if i["id"] == item_id), None)


# Create global instance
scratchpad = ScratchpadEngine()


# Convenience functions for easy importing
def scratchpad_add(content: str, item_type: str = "note") -> dict:
    """Add item to scratchpad"""
    return scratchpad.add_item(content, item_type)


def scratchpad_view(status: str = "active") -> List[dict]:
    """View scratchpad items"""
    return scratchpad.view_items(status)


def scratchpad_resolve(item_id: int, action: str = "resolved", note: Optional[str] = None) -> dict:
    """Resolve scratchpad item"""
    return scratchpad.resolve_item(item_id, action, note)


def get_scratchpad_for_warmup() -> str:
    """Get scratchpad display for warmup briefing"""
    return scratchpad.get_warmup_display()


def scratchpad_review() -> str:
    """Get detailed review display with IDs for cleanup"""
    return scratchpad.get_review_display()


def scratchpad_archive(limit: int = 20) -> str:
    """Get summary of resolved/archived items"""
    return scratchpad.get_archive_summary(limit)


def scratchpad_summary() -> dict:
    """Get scratchpad statistics"""
    return scratchpad.get_summary()
