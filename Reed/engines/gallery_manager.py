# engines/gallery_manager.py
"""
Gallery Manager for ReedZero
Tracks all images uploaded to Reed with metadata and emotional context.
"""

import json
import os
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


class GalleryManager:
    """
    Manages gallery of images shared with Reed.

    Features:
    - Tracks image metadata (filename, path, timestamp, size)
    - Links to visual memory (Reed's emotional response)
    - Stores copies in gallery folder for persistence
    - Supports re-sending images to conversation
    """

    def __init__(self, memory_engine=None):
        self.memory_engine = memory_engine
        self.gallery_items: List[Dict[str, Any]] = []

        # Compute absolute paths
        wrapper_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.GALLERY_DIR = os.path.join(wrapper_root, "memory", "gallery")
        self.GALLERY_DATA_FILE = os.path.join(wrapper_root, "memory", "gallery.json")

        # Ensure gallery directory exists
        os.makedirs(self.GALLERY_DIR, exist_ok=True)

        # Load existing gallery
        self._load_gallery()

    def _load_gallery(self):
        """Load gallery data from JSON."""
        try:
            if os.path.exists(self.GALLERY_DATA_FILE):
                with open(self.GALLERY_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.gallery_items = data.get("items", [])
                print(f"[GALLERY] Loaded {len(self.gallery_items)} images")
        except Exception as e:
            print(f"[GALLERY] Error loading gallery: {e}")
            self.gallery_items = []

    def _save_gallery(self):
        """Save gallery data to JSON."""
        os.makedirs(os.path.dirname(self.GALLERY_DATA_FILE), exist_ok=True)

        data = {
            "items": self.gallery_items,
            "last_updated": datetime.now().isoformat()
        }

        try:
            with open(self.GALLERY_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[GALLERY] Error saving gallery: {e}")

    def add_image(
        self,
        original_path: str,
        turn_number: int = 0,
        conversation_context: str = "",
        reed_response: str = "",
        emotional_response: Optional[List[str]] = None,
        copy_to_gallery: bool = True
    ) -> Dict[str, Any]:
        """
        Add an image to the gallery.

        Args:
            original_path: Path to the original image file
            turn_number: Conversation turn when image was shared
            conversation_context: User's message when sharing the image
            reed_response: Reed's response to the image
            emotional_response: List of emotions Reed expressed
            copy_to_gallery: If True, copy image to gallery folder

        Returns:
            Gallery entry dict
        """
        original = Path(original_path)

        if not original.exists():
            print(f"[GALLERY] Image not found: {original_path}")
            return None

        # Generate unique gallery filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        gallery_filename = f"{timestamp}_{original.name}"
        gallery_path = os.path.join(self.GALLERY_DIR, gallery_filename)

        # Copy to gallery folder
        if copy_to_gallery:
            try:
                shutil.copy2(original_path, gallery_path)
            except Exception as e:
                print(f"[GALLERY] Error copying image: {e}")
                gallery_path = original_path  # Use original path as fallback
        else:
            gallery_path = original_path

        # Get file info
        file_size = os.path.getsize(original_path)

        # Create gallery entry
        entry = {
            "id": f"img_{timestamp}",
            "filename": original.name,
            "original_path": str(original_path),
            "gallery_path": gallery_path,
            "timestamp": datetime.now().isoformat(),
            "timestamp_display": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "size_bytes": file_size,
            "size_display": self._format_size(file_size),
            "turn_number": turn_number,
            "conversation_context": conversation_context[:200] if conversation_context else "",
            "reed_response": reed_response[:500] if reed_response else "",
            "emotional_response": emotional_response or [],
            "seen_count": 1,  # First viewing
            "last_seen": datetime.now().isoformat()
        }

        # Add to gallery
        self.gallery_items.append(entry)
        self._save_gallery()

        print(f"[GALLERY] Added: {original.name} ({entry['size_display']})")
        return entry

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f}MB"

    def get_all_images(self, sort_by: str = "date", reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Get all gallery images.

        Args:
            sort_by: "date", "name", or "seen_count"
            reverse: If True, sort descending (newest/most seen first)

        Returns:
            List of gallery entries
        """
        items = self.gallery_items.copy()

        if sort_by == "date":
            items.sort(key=lambda x: x.get("timestamp", ""), reverse=reverse)
        elif sort_by == "name":
            items.sort(key=lambda x: x.get("filename", "").lower(), reverse=reverse)
        elif sort_by == "seen_count":
            items.sort(key=lambda x: x.get("seen_count", 0), reverse=reverse)

        return items

    def get_image_by_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific gallery image by ID."""
        for item in self.gallery_items:
            if item.get("id") == image_id:
                return item
        return None

    def search_images(self, query: str) -> List[Dict[str, Any]]:
        """
        Search gallery images by filename or context.

        Args:
            query: Search string

        Returns:
            List of matching gallery entries
        """
        query_lower = query.lower()
        results = []

        for item in self.gallery_items:
            # Search in filename
            if query_lower in item.get("filename", "").lower():
                results.append(item)
                continue
            # Search in conversation context
            if query_lower in item.get("conversation_context", "").lower():
                results.append(item)
                continue
            # Search in Reed's response
            if query_lower in item.get("reed_response", "").lower():
                results.append(item)
                continue
            # Search in emotional response
            if any(query_lower in e.lower() for e in item.get("emotional_response", [])):
                results.append(item)

        return results

    def mark_as_seen(self, image_id: str):
        """Mark an image as viewed (increments seen_count)."""
        for item in self.gallery_items:
            if item.get("id") == image_id:
                item["seen_count"] = item.get("seen_count", 0) + 1
                item["last_seen"] = datetime.now().isoformat()
                self._save_gallery()
                return

    def update_image_entry(
        self,
        image_id: str,
        reed_response: str = None,
        emotional_response: List[str] = None
    ):
        """
        Update an existing gallery entry with Reed's response.

        Used when re-showing an image to Reed to record the new response.
        """
        for item in self.gallery_items:
            if item.get("id") == image_id:
                if reed_response:
                    # Append new response if different
                    existing = item.get("reed_response", "")
                    if reed_response not in existing:
                        item["reed_response"] = f"{existing}\n---\n{reed_response[:500]}" if existing else reed_response[:500]

                if emotional_response:
                    # Merge emotional responses
                    existing_emotions = set(item.get("emotional_response", []))
                    existing_emotions.update(emotional_response)
                    item["emotional_response"] = list(existing_emotions)

                item["seen_count"] = item.get("seen_count", 0) + 1
                item["last_seen"] = datetime.now().isoformat()
                self._save_gallery()
                print(f"[GALLERY] Updated entry: {item.get('filename')}")
                return

    def delete_image(self, image_id: str, delete_file: bool = True) -> bool:
        """
        Delete an image from the gallery.

        Args:
            image_id: ID of the image to delete
            delete_file: If True, also delete the file from gallery folder

        Returns:
            True if deleted, False if not found
        """
        for i, item in enumerate(self.gallery_items):
            if item.get("id") == image_id:
                # Delete file from gallery folder
                if delete_file:
                    gallery_path = item.get("gallery_path", "")
                    if gallery_path and os.path.exists(gallery_path):
                        try:
                            os.remove(gallery_path)
                            print(f"[GALLERY] Deleted file: {gallery_path}")
                        except Exception as e:
                            print(f"[GALLERY] Error deleting file: {e}")

                # Remove from list
                del self.gallery_items[i]
                self._save_gallery()
                print(f"[GALLERY] Removed from gallery: {item.get('filename')}")
                return True

        return False

    def get_image_path(self, image_id: str) -> Optional[str]:
        """
        Get the file path for a gallery image.

        Prefers gallery_path, falls back to original_path.
        """
        item = self.get_image_by_id(image_id)
        if not item:
            return None

        # Try gallery path first
        gallery_path = item.get("gallery_path", "")
        if gallery_path and os.path.exists(gallery_path):
            return gallery_path

        # Fall back to original path
        original_path = item.get("original_path", "")
        if original_path and os.path.exists(original_path):
            return original_path

        return None

    def get_visual_memory_for_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the visual memory entry associated with a gallery image.

        Links gallery to the memory system.
        """
        if not self.memory_engine:
            return None

        item = self.get_image_by_id(image_id)
        if not item:
            return None

        filename = item.get("filename", "")

        # Search for visual memory with matching filename
        for mem in self.memory_engine.all_memories:
            if mem.get("type") == "visual" and mem.get("source_file") == filename:
                return mem

        return None

    def get_gallery_stats(self) -> Dict[str, Any]:
        """Get statistics about the gallery."""
        if not self.gallery_items:
            return {
                "total_images": 0,
                "total_size": "0B",
                "most_viewed": None,
                "oldest": None,
                "newest": None
            }

        total_size = sum(item.get("size_bytes", 0) for item in self.gallery_items)

        # Sort by different criteria
        by_views = sorted(self.gallery_items, key=lambda x: x.get("seen_count", 0), reverse=True)
        by_date = sorted(self.gallery_items, key=lambda x: x.get("timestamp", ""))

        return {
            "total_images": len(self.gallery_items),
            "total_size": self._format_size(total_size),
            "most_viewed": by_views[0].get("filename") if by_views else None,
            "oldest": by_date[0].get("filename") if by_date else None,
            "newest": by_date[-1].get("filename") if by_date else None
        }
