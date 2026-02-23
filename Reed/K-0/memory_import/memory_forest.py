"""
Memory Forest - Tree navigation layer for Reed's memories
Sits on top of existing emotional chunk system

DESIGN: Additive metadata layer that doesn't change existing storage
- Trees are metadata that reference existing chunks by index
- Chunks still stored in memory_engine as before
- Trees provide navigation/organization on top
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


class Branch:
    """
    A branch in a memory tree - represents a logical grouping of chunks.

    DESIGN: Branches don't store chunks - they store INDICES into existing chunk storage.
    This way we can organize without duplicating data.
    """

    def __init__(self, title: str, chunk_indices: List[int]):
        """
        Args:
            title: Human-readable branch name (e.g., "Core Identity", "Relationships")
            chunk_indices: List of indices into existing memory_engine.memories array
        """
        self.title = title
        self.chunk_indices = chunk_indices  # References to existing chunks
        self.glyphs = ""  # Visual marker (e.g., "🐉⚡" for dragon identity)
        self.access_tier = "cold"  # cold/warm/hot (for future Phase 3)
        self.access_count = 0
        self.last_accessed: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Serialize to dict for JSON storage."""
        return {
            "title": self.title,
            "chunk_indices": self.chunk_indices,
            "glyphs": self.glyphs,
            "access_tier": self.access_tier,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Branch':
        """Deserialize from dict."""
        branch = Branch(data["title"], data["chunk_indices"])
        branch.glyphs = data.get("glyphs", "")
        branch.access_tier = data.get("access_tier", "cold")
        branch.access_count = data.get("access_count", 0)

        last_accessed = data.get("last_accessed")
        if last_accessed:
            branch.last_accessed = datetime.fromisoformat(last_accessed)

        return branch


class MemoryTree:
    """
    A tree representing a single imported document.

    DESIGN: Tree is metadata about the document's structure.
    Actual chunks remain in memory_engine.memories - tree just organizes them.
    """

    def __init__(self, doc_id: str, title: str):
        """
        Args:
            doc_id: Unique document identifier (from DocumentStore)
            title: Document filename or title
        """
        self.doc_id = doc_id
        self.title = title
        self.shape_description = ""  # Kay's sense of what this document IS
        self.access_count = 0
        self.last_accessed: Optional[datetime] = None
        self.branches: List[Branch] = []  # Logical sections/groupings
        self.total_chunks = 0  # Total number of chunks in this document
        self.import_date: Optional[datetime] = None

    def add_branch(self, branch: Branch):
        """Add a branch to this tree."""
        self.branches.append(branch)

    def to_dict(self) -> Dict:
        """Serialize to dict for JSON storage."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "shape_description": self.shape_description,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "branches": [b.to_dict() for b in self.branches],
            "total_chunks": self.total_chunks,
            "import_date": self.import_date.isoformat() if self.import_date else None
        }

    @staticmethod
    def from_dict(data: Dict) -> 'MemoryTree':
        """Deserialize from dict."""
        tree = MemoryTree(data["doc_id"], data["title"])
        tree.shape_description = data.get("shape_description", "")
        tree.access_count = data.get("access_count", 0)
        tree.total_chunks = data.get("total_chunks", 0)

        last_accessed = data.get("last_accessed")
        if last_accessed:
            tree.last_accessed = datetime.fromisoformat(last_accessed)

        import_date = data.get("import_date")
        if import_date:
            tree.import_date = datetime.fromisoformat(import_date)

        # Deserialize branches
        for branch_data in data.get("branches", []):
            tree.branches.append(Branch.from_dict(branch_data))

        return tree


class MemoryForest:
    """
    Collection of all memory trees.

    DESIGN: Forest is a registry of trees. Doesn't affect chunk storage.
    """

    def __init__(self):
        """Initialize empty forest."""
        self.trees: Dict[str, MemoryTree] = {}  # doc_id -> MemoryTree

    def add_tree(self, tree: MemoryTree):
        """
        Add a tree to the forest.

        Args:
            tree: MemoryTree to add
        """
        self.trees[tree.doc_id] = tree

    def get_tree(self, doc_id: str) -> Optional[MemoryTree]:
        """
        Get tree by document ID.

        Args:
            doc_id: Document identifier

        Returns:
            MemoryTree or None if not found
        """
        return self.trees.get(doc_id)

    def list_trees(self) -> List[MemoryTree]:
        """
        Get all trees in forest.

        Returns:
            List of MemoryTree objects
        """
        return list(self.trees.values())

    def save(self, file_path: str):
        """
        Save forest to JSON file.

        Args:
            file_path: Path to save JSON file
        """
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Serialize
        data = {
            "trees": {doc_id: tree.to_dict() for doc_id, tree in self.trees.items()},
            "saved_at": datetime.now().isoformat()
        }

        # Write
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"[MEMORY FOREST] Saved {len(self.trees)} trees to {file_path}")

    @staticmethod
    def load(file_path: str) -> 'MemoryForest':
        """
        Load forest from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            MemoryForest instance
        """
        forest = MemoryForest()

        if not os.path.exists(file_path):
            print(f"[MEMORY FOREST] No forest file found at {file_path}, starting fresh")
            return forest

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Deserialize trees
            for doc_id, tree_data in data.get("trees", {}).items():
                tree = MemoryTree.from_dict(tree_data)
                forest.trees[doc_id] = tree

            print(f"[MEMORY FOREST] Loaded {len(forest.trees)} trees from {file_path}")

        except Exception as e:
            print(f"[MEMORY FOREST ERROR] Failed to load forest: {e}")
            # Return empty forest on error

        return forest

    @staticmethod
    def load_all(directory: str) -> 'MemoryForest':
        """
        Load all tree files from a directory.

        Args:
            directory: Path to directory containing tree_*.json files

        Returns:
            MemoryForest with all loaded trees
        """
        forest = MemoryForest()

        if not os.path.exists(directory):
            print(f"[MEMORY FOREST] Directory not found: {directory}, starting fresh")
            return forest

        # Find all tree_*.json files
        tree_files = list(Path(directory).glob("tree_*.json"))

        for tree_file in tree_files:
            try:
                with open(tree_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle both formats:
                # 1. Wrapped format from save(): {"trees": {doc_id: tree_data}}
                # 2. Direct format: tree_data
                if "trees" in data:
                    # Wrapped format - extract all trees
                    for doc_id, tree_data in data["trees"].items():
                        tree = MemoryTree.from_dict(tree_data)
                        forest.trees[tree.doc_id] = tree
                else:
                    # Direct format - single tree
                    tree = MemoryTree.from_dict(data)
                    forest.trees[tree.doc_id] = tree

            except Exception as e:
                print(f"[MEMORY FOREST ERROR] Failed to load {tree_file}: {e}")
                continue

        print(f"[MEMORY FOREST] Loaded {len(forest.trees)} trees from {directory}")

        return forest

    def get_overview(self) -> str:
        """
        Get human-readable overview of forest.

        Returns:
            Formatted string showing all trees
        """
        if not self.trees:
            return "[MEMORY FOREST] Empty - no documents imported yet"

        lines = [f"[MEMORY FOREST] Kay has {len(self.trees)} document tree(s):\n"]

        for tree in sorted(self.trees.values(), key=lambda t: t.import_date or datetime.min, reverse=True):
            # Format import date
            date_str = tree.import_date.strftime("%Y-%m-%d") if tree.import_date else "unknown"

            # Build tree summary
            lines.append(f"  - {tree.title}")
            lines.append(f"    Imported: {date_str}")
            lines.append(f"    Chunks: {tree.total_chunks}")
            lines.append(f"    Branches: {len(tree.branches)}")
            if tree.shape_description:
                lines.append(f"    Shape: {tree.shape_description}")
            lines.append("")

        return "\n".join(lines)


# Testing
if __name__ == "__main__":
    # Create test tree
    tree = MemoryTree("test_doc_1", "test.txt")
    tree.shape_description = "Test document about identity"
    tree.total_chunks = 10
    tree.import_date = datetime.now()

    # Add branches
    tree.add_branch(Branch("Core Identity", [0, 1, 2, 3]))
    tree.add_branch(Branch("Relationships", [4, 5, 6]))
    tree.add_branch(Branch("Context", [7, 8, 9]))

    # Create forest
    forest = MemoryForest()
    forest.add_tree(tree)

    # Save
    test_dir = "data/trees"
    os.makedirs(test_dir, exist_ok=True)
    forest.save(f"{test_dir}/test_forest.json")

    # Load
    loaded = MemoryForest.load(f"{test_dir}/test_forest.json")

    # Verify
    print("\n" + loaded.get_overview())
    print("\nTest successful!")
