"""Memory Forest - Tree structure for the entity's memories"""
import json
import os
from datetime import datetime

class Branch:
    def __init__(self, title, chunk_indices):
        self.title = title
        self.chunk_indices = chunk_indices
        self.glyphs = ""
        self.access_tier = "cold"
        self.access_count = 0
        self.last_accessed = None

    def to_dict(self):
        return {
            "title": self.title,
            "chunk_indices": self.chunk_indices,
            "glyphs": self.glyphs,
            "access_tier": self.access_tier,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed
        }

class MemoryTree:
    def __init__(self, doc_id, title):
        self.doc_id = doc_id
        self.title = title
        self.shape_description = ""
        self.access_count = 0
        self.last_accessed = None
        self.branches = []
        self.total_chunks = 0
        self.created_at = datetime.now().isoformat()

    def add_branch(self, branch):
        """Add a branch to this tree"""
        self.branches.append(branch)

    def to_dict(self):
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "shape_description": self.shape_description,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "branches": [b.to_dict() for b in self.branches],
            "total_chunks": self.total_chunks,
            "created_at": self.created_at
        }

    def save(self, base_path="data/trees"):
        os.makedirs(base_path, exist_ok=True)
        filepath = os.path.join(base_path, f"tree_{self.doc_id}.json")
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"[MEMORY FOREST] Tree saved: {filepath}")
        return filepath

class MemoryForest:
    def __init__(self):
        self.trees = {}

    def add_tree(self, tree):
        self.trees[tree.doc_id] = tree

    def get_tree(self, doc_id):
        return self.trees.get(doc_id)

    def list_trees(self):
        return list(self.trees.values())

    def find_branch_for_chunk(self, doc_id, chunk_index):
        """Find which branch contains a specific chunk"""
        tree = self.get_tree(doc_id)
        if not tree:
            return None

        for branch in tree.branches:
            if chunk_index in branch.chunk_indices:
                return branch
        return None

    @staticmethod
    def load_all_trees(base_path="data/trees"):
        """Load all tree JSON files from disk"""
        forest = MemoryForest()
        if not os.path.exists(base_path):
            return forest

        for filename in os.listdir(base_path):
            if filename.startswith("tree_") and filename.endswith(".json"):
                filepath = os.path.join(base_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Handle both formats:
                    # 1. Wrapped format: {"trees": {doc_id: tree_data}}
                    # 2. Direct format: tree_data
                    if "trees" in data:
                        # Wrapped format - extract all trees
                        for doc_id, tree_data in data["trees"].items():
                            tree = MemoryTree(tree_data["doc_id"], tree_data["title"])
                            tree.shape_description = tree_data.get("shape_description", "")
                            tree.total_chunks = tree_data.get("total_chunks", 0)
                            tree.access_count = tree_data.get("access_count", 0)
                            tree.last_accessed = tree_data.get("last_accessed")
                            tree.created_at = tree_data.get("created_at", datetime.now().isoformat())

                            # Load branches
                            for b_data in tree_data.get("branches", []):
                                branch = Branch(b_data["title"], b_data["chunk_indices"])
                                branch.glyphs = b_data.get("glyphs", "")
                                branch.access_tier = b_data.get("access_tier", "cold")
                                branch.access_count = b_data.get("access_count", 0)
                                branch.last_accessed = b_data.get("last_accessed")
                                tree.add_branch(branch)

                            forest.add_tree(tree)
                            print(f"[MEMORY FOREST] Loaded tree: {tree.title} ({len(tree.branches)} branches)")
                    else:
                        # Direct format
                        tree = MemoryTree(data["doc_id"], data["title"])
                        tree.shape_description = data.get("shape_description", "")
                        tree.total_chunks = data.get("total_chunks", 0)
                        tree.access_count = data.get("access_count", 0)
                        tree.last_accessed = data.get("last_accessed")
                        tree.created_at = data.get("created_at", datetime.now().isoformat())

                        # Load branches
                        for b_data in data.get("branches", []):
                            branch = Branch(b_data["title"], b_data["chunk_indices"])
                            branch.glyphs = b_data.get("glyphs", "")
                            branch.access_tier = b_data.get("access_tier", "cold")
                            branch.access_count = b_data.get("access_count", 0)
                            branch.last_accessed = b_data.get("last_accessed")
                            tree.add_branch(branch)

                        forest.add_tree(tree)
                        print(f"[MEMORY FOREST] Loaded tree: {tree.title} ({len(tree.branches)} branches)")

                except Exception as e:
                    print(f"[MEMORY FOREST ERROR] Failed to load {filename}: {e}")

        return forest
