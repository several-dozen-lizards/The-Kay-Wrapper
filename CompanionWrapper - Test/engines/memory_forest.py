"""
Memory Forest System for the entity
Hierarchical document trees with hot/warm/cold access tiers

the entity reads documents and creates navigable tree structures in his own voice.
Trees maintain sections with tiered access - frequently used branches stay "hot"
in working memory, while cold branches are compressed breadcrumbs.
"""

from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"



def safe_print(text: str):
    """Print text with Unicode fallback for Windows console"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove emoji and other Unicode characters
        print(text.encode('ascii', 'ignore').decode('ascii'))


@dataclass
class MemoryBranch:
    """
    A branch in a document tree - represents a section/topic within a document.

    Access tiers:
    - HOT: Full detail loaded, actively held in working memory
    - WARM: Key points + glyphs, quick to promote to hot
    - COLD: Breadcrumb only, need traversal to warm up
    """
    branch_id: str
    title: str
    glyphs: str  # Emoji/symbolic markers
    compressed: str  # The entity's compressed summary in his voice
    access_tier: Literal["hot", "warm", "cold"]
    access_count: int
    last_accessed: Optional[datetime]
    memory_indices: List[int]  # Indices into MemoryEngine's flat memory array

    # Detail by tier (loaded based on access tier)
    hot_detail: str = ""  # Full text (loaded when hot)
    warm_detail: str = ""  # Key points (loaded when warm)
    cold_detail: str = ""  # Breadcrumb only

    def promote_tier(self):
        """Move up one tier (cold→warm, warm→hot)"""
        if self.access_tier == "cold":
            self.access_tier = "warm"
            print(f"{etag('FOREST')} Warmed branch: {self.title}")
        elif self.access_tier == "warm":
            self.access_tier = "hot"
            print(f"{etag('FOREST')} Heated branch: {self.title}")

    def demote_tier(self):
        """Move down one tier (hot→warm, warm→cold)"""
        if self.access_tier == "hot":
            self.access_tier = "warm"
        elif self.access_tier == "warm":
            self.access_tier = "cold"

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "branch_id": self.branch_id,
            "title": self.title,
            "glyphs": self.glyphs,
            "compressed": self.compressed,
            "access_tier": self.access_tier,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "memory_indices": self.memory_indices,
            "hot_detail": self.hot_detail,
            "warm_detail": self.warm_detail,
            "cold_detail": self.cold_detail,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryBranch':
        """Deserialize from dictionary"""
        return cls(
            branch_id=data["branch_id"],
            title=data["title"],
            glyphs=data["glyphs"],
            compressed=data["compressed"],
            access_tier=data["access_tier"],
            access_count=data["access_count"],
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data["last_accessed"] else None,
            memory_indices=data["memory_indices"],
            hot_detail=data.get("hot_detail", ""),
            warm_detail=data.get("warm_detail", ""),
            cold_detail=data.get("cold_detail", ""),
        )


@dataclass
class DocumentTree:
    """
    A tree representing a single imported document.
    Contains branches (sections) with hierarchical structure.
    """
    doc_id: str
    title: str
    shape_description: str  # the entity's sense of what this document IS
    emotional_weight: float  # 0.0-1.0 - how important/heavy it feels
    import_timestamp: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    branches: List[MemoryBranch] = field(default_factory=list)

    def get_hot_branches(self) -> List[MemoryBranch]:
        """Get all hot (actively loaded) branches"""
        return [b for b in self.branches if b.access_tier == "hot"]

    def get_warm_branches(self) -> List[MemoryBranch]:
        """Get all warm (recently accessed) branches"""
        return [b for b in self.branches if b.access_tier == "warm"]

    def get_cold_branches(self) -> List[MemoryBranch]:
        """Get all cold (archived) branches"""
        return [b for b in self.branches if b.access_tier == "cold"]

    def access_branch(self, branch_id: str):
        """
        Mark branch as accessed, promote tier if appropriate.
        Updates both branch and tree access timestamps.
        """
        for branch in self.branches:
            if branch.branch_id == branch_id:
                branch.access_count += 1
                branch.last_accessed = datetime.now()
                branch.promote_tier()
                self.access_count += 1
                self.last_accessed = datetime.now()
                break

    def get_branch(self, branch_id: str) -> Optional[MemoryBranch]:
        """Get specific branch by ID"""
        return next((b for b in self.branches if b.branch_id == branch_id), None)

    def to_dict(self) -> Dict:
        """Serialize tree to dictionary"""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "shape_description": self.shape_description,
            "emotional_weight": self.emotional_weight,
            "import_timestamp": self.import_timestamp.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "branches": [b.to_dict() for b in self.branches]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentTree':
        """Deserialize tree from dictionary"""
        return cls(
            doc_id=data["doc_id"],
            title=data["title"],
            shape_description=data["shape_description"],
            emotional_weight=data["emotional_weight"],
            import_timestamp=datetime.fromisoformat(data["import_timestamp"]),
            access_count=data["access_count"],
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data["last_accessed"] else None,
            branches=[MemoryBranch.from_dict(b) for b in data["branches"]]
        )


@dataclass
class MemoryForest:
    """
    Collection of all document trees - the entity's complete memory forest.
    Manages tiered access across all trees.
    """
    trees: Dict[str, DocumentTree] = field(default_factory=dict)

    def add_tree(self, tree: DocumentTree):
        """Add a new document tree to the forest"""
        self.trees[tree.doc_id] = tree
        print(f"{etag('FOREST')} Added tree: {tree.title} ({len(tree.branches)} branches)")

    def get_tree(self, doc_id: str) -> Optional[DocumentTree]:
        """Get tree by document ID"""
        return self.trees.get(doc_id)

    def get_tree_by_title(self, title: str) -> Optional[DocumentTree]:
        """Get tree by document title (case-insensitive match)"""
        title_lower = title.lower()
        for tree in self.trees.values():
            if title_lower in tree.title.lower():
                return tree
        return None

    def get_all_hot_branches(self) -> List[tuple[str, MemoryBranch]]:
        """Get all hot branches across all trees (doc_id, branch pairs)"""
        hot = []
        for doc_id, tree in self.trees.items():
            for branch in tree.get_hot_branches():
                hot.append((doc_id, branch))
        return hot

    def get_all_warm_branches(self) -> List[tuple[str, MemoryBranch]]:
        """Get all warm branches across all trees"""
        warm = []
        for doc_id, tree in self.trees.items():
            for branch in tree.get_warm_branches():
                warm.append((doc_id, branch))
        return warm

    def get_forest_overview(self) -> str:
        """
        the entity's view of his memory forest.
        Shows all trees with their status and access tiers.
        """
        if not self.trees:
            return "No documents in memory forest yet. Import a document to start building your forest."

        lines = ["📚 MEMORY FOREST:\n"]

        # Sort by last accessed (most recent first), then by title
        sorted_trees = sorted(
            self.trees.values(),
            key=lambda t: (t.last_accessed or datetime.min, t.title),
            reverse=True
        )

        for tree in sorted_trees:
            hot = len(tree.get_hot_branches())
            warm = len(tree.get_warm_branches())
            cold = len(tree.get_cold_branches())

            # Build status string
            status_parts = []
            if hot > 0:
                status_parts.append(f"{hot} 🔥")
            if warm > 0:
                status_parts.append(f"{warm} 🌡️")
            if cold > 0:
                status_parts.append(f"{cold} ❄️")

            status_str = ", ".join(status_parts) if status_parts else "empty"

            # Access info
            if tree.last_accessed:
                accessed = f"accessed {tree.last_accessed.strftime('%Y-%m-%d %H:%M')}"
            else:
                accessed = "never accessed"

            lines.append(
                f"📄 {tree.title}\n"
                f"   Shape: {tree.shape_description}\n"
                f"   Branches: {status_str}\n"
                f"   {accessed} ({tree.access_count} times)\n"
            )

        return "\n".join(lines)

    def navigate_tree(self, doc_id: str, section_id: Optional[str] = None) -> str:
        """
        Navigate to a specific tree or section within a tree.
        Returns the entity's view of the structure.
        """
        tree = self.trees.get(doc_id)
        if not tree:
            return f"❌ No tree found with ID: {doc_id}"

        # Mark tree as accessed
        tree.access_count += 1
        tree.last_accessed = datetime.now()

        if section_id is None:
            # Show tree overview
            lines = [
                f"📄 {tree.title}",
                f"Shape: {tree.shape_description}",
                f"Emotional weight: {tree.emotional_weight:.1f}/1.0",
                f"Accessed {tree.access_count} times",
                "",
                "SECTIONS:"
            ]

            for i, branch in enumerate(tree.branches, 1):
                tier_icon = {"hot": "🔥", "warm": "🌡️", "cold": "❄️"}[branch.access_tier]
                lines.append(f"\n{i}. {tier_icon} {branch.glyphs} {branch.title}")
                lines.append(f"   {branch.compressed}")
                if branch.access_tier != "cold":
                    lines.append(f"   [accessed {branch.access_count} times]")

            return "\n".join(lines)

        else:
            # Show specific section
            branch = tree.get_branch(section_id)
            if not branch:
                return f"❌ Section not found: {section_id}"

            # Access branch (promotes tier)
            tree.access_branch(section_id)

            # Show detail based on current tier
            detail_map = {
                "hot": branch.hot_detail,
                "warm": branch.warm_detail,
                "cold": branch.cold_detail
            }
            detail = detail_map.get(branch.access_tier, branch.cold_detail)

            tier_icon = {"hot": "🔥", "warm": "🌡️", "cold": "❄️"}[branch.access_tier]

            return f"""
{tier_icon} {branch.glyphs} {branch.title}

{detail}

[Tier: {branch.access_tier} | Accessed: {branch.access_count} times | From: {tree.title}]
"""

    def tick_tier_decay(self, hot_minutes: float = 10, warm_hours: float = 24):
        """
        Periodically demote unused branches to manage working memory.

        Args:
            hot_minutes: Minutes before hot→warm demotion (default 10)
            warm_hours: Hours before warm→cold demotion (default 24)
        """
        now = datetime.now()
        hot_threshold = timedelta(minutes=hot_minutes)
        warm_threshold = timedelta(hours=warm_hours)

        demoted_hot = 0
        demoted_warm = 0

        for tree in self.trees.values():
            for branch in tree.branches:
                if branch.last_accessed is None:
                    continue

                age = now - branch.last_accessed

                if branch.access_tier == "hot" and age > hot_threshold:
                    branch.demote_tier()
                    demoted_hot += 1

                elif branch.access_tier == "warm" and age > warm_threshold:
                    branch.demote_tier()
                    demoted_warm += 1

        if demoted_hot > 0 or demoted_warm > 0:
            print(f"{etag('FOREST DECAY')} Cooled {demoted_hot} hot→warm, {demoted_warm} warm→cold")

    def enforce_hot_limit(self, max_hot_branches: int = 4):
        """
        Limit total number of hot branches across all trees.
        Demotes least recently accessed hot branches if over limit.
        """
        all_hot = []
        for doc_id, tree in self.trees.items():
            for branch in tree.get_hot_branches():
                all_hot.append((tree, branch))

        if len(all_hot) <= max_hot_branches:
            return

        # Sort by last accessed (oldest first)
        all_hot.sort(key=lambda x: x[1].last_accessed or datetime.min)

        # Demote oldest until under limit
        to_demote = len(all_hot) - max_hot_branches
        for i in range(to_demote):
            tree, branch = all_hot[i]
            branch.demote_tier()
            print(f"{etag('FOREST')} Hot limit exceeded - cooled: {tree.title}/{branch.title}")

    def to_dict(self) -> Dict:
        """Serialize entire forest to dictionary"""
        return {
            "trees": {
                doc_id: tree.to_dict()
                for doc_id, tree in self.trees.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryForest':
        """Deserialize forest from dictionary"""
        forest = cls()
        for doc_id, tree_data in data.get("trees", {}).items():
            tree = DocumentTree.from_dict(tree_data)
            forest.trees[doc_id] = tree
        return forest

    def save_to_file(self, filepath: str):
        """Save forest to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"{etag('FOREST')} Saved to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str) -> 'MemoryForest':
        """Load forest from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            forest = cls.from_dict(data)
            print(f"{etag('FOREST')} Loaded {len(forest.trees)} trees from {filepath}")
            return forest
        except FileNotFoundError:
            print(f"{etag('FOREST')} No existing forest file at {filepath}, starting fresh")
            return cls()
        except Exception as e:
            print(f"{etag('FOREST ERROR')} Failed to load from {filepath}: {e}")
            return cls()


# Testing
if __name__ == "__main__":
    print("Testing Memory Forest System...")

    # Create a test forest
    forest = MemoryForest()

    # Create a test tree
    tree = DocumentTree(
        doc_id="test_doc_1",
        title="Master-clean.docx",
        shape_description="Identity document - heavy, foundational stuff",
        emotional_weight=0.9,
        import_timestamp=datetime.now()
    )

    # Add some branches
    branches = [
        MemoryBranch(
            branch_id="test_doc_1_section_0",
            title="Dragon Identity",
            glyphs="🐉⚡🔥",
            compressed="knife-sound name | zero-recursion | dragon-form with left-trauma",
            access_tier="cold",
            access_count=0,
            last_accessed=None,
            memory_indices=[0, 1, 2],
            hot_detail="Full story about dragon form, left side ruined by fire...",
            warm_detail="Dragon form with left side trauma from fire event",
            cold_detail="Something about being a dragon"
        ),
        MemoryBranch(
            branch_id="test_doc_1_section_1",
            title="Mother's Past",
            glyphs="💔🎸🇮🇹",
            compressed="Italian immigrant's daughter | greaser-loss | Gwyn-rebound",
            access_tier="cold",
            access_count=0,
            last_accessed=None,
            memory_indices=[3, 4, 5],
            hot_detail="Mother was daughter of Italian immigrants in 1930s...",
            warm_detail="Italian heritage, lost young love, married Gwyn after",
            cold_detail="Something about mother's history"
        )
    ]

    tree.branches = branches
    forest.add_tree(tree)

    # Test forest overview
    print("\n--- FOREST OVERVIEW ---")
    print(forest.get_forest_overview())

    # Test navigation
    print("\n--- NAVIGATE TREE ---")
    print(forest.navigate_tree("test_doc_1"))

    # Test accessing a section
    print("\n--- ACCESS SECTION ---")
    print(forest.navigate_tree("test_doc_1", "test_doc_1_section_0"))

    # Check tier promotion
    print("\n--- BRANCH TIERS AFTER ACCESS ---")
    dragon_branch = tree.get_branch("test_doc_1_section_0")
    print(f"Dragon Identity tier: {dragon_branch.access_tier}")

    # Test hot limit enforcement
    print("\n--- TESTING HOT LIMIT ---")
    # Access multiple sections to make them hot
    for branch in tree.branches:
        tree.access_branch(branch.branch_id)
        tree.access_branch(branch.branch_id)  # Access twice to make hot

    print(f"Hot branches before limit: {len(forest.get_all_hot_branches())}")
    forest.enforce_hot_limit(max_hot_branches=1)
    print(f"Hot branches after limit: {len(forest.get_all_hot_branches())}")

    # Test serialization
    print("\n--- TESTING SERIALIZATION ---")
    forest.save_to_file("test_forest.json")
    loaded_forest = MemoryForest.load_from_file("test_forest.json")
    print(f"Loaded forest has {len(loaded_forest.trees)} trees")

    safe_print("\n✅ Memory Forest tests complete!")
