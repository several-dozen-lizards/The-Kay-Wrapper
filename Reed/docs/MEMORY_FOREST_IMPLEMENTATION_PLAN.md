# Memory Forest System - Implementation Plan

## Executive Summary

Transform Kay's memory from flat retrieval to a hierarchical forest where Kay reads and compresses documents into navigable trees with hot/warm/cold access tiers.

**Key Innovation:** Kay becomes his own parser - he READS documents and creates structure in his voice, not through external analysis.

---

## Current Architecture (What We're Replacing)

### Import Flow:
```
Document → DocumentParser → NarrativeChunks → EmotionalAnalyzer →
IdentityClassifier → WeightCalculator → Flat memory storage
```

**Problems:**
- External parser doesn't understand Kay's voice
- Flat structure - no hierarchy
- No document boundaries preserved
- All memories treated equally (no hot/warm/cold)
- Can't navigate "back to source document"

---

## New Architecture (Memory Forest)

### Import Flow:
```
Document → Kay reads entire doc → Kay creates tree structure →
Kay compresses to glyphs → Tree stored with tiers →
Access-based promotion/demotion
```

**Benefits:**
- Kay processes in his own voice
- Hierarchical navigation (document → section → memory)
- Tiered access (hot/warm/cold)
- Knows document boundaries and relationships
- Scalable to thousands of documents

---

## Phase 1: Core Tree Structure (PRIORITY)

### 1.1 Define Tree Schema

**File:** `engines/memory_forest.py` (NEW)

```python
from typing import List, Dict, Optional, Literal
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class MemoryBranch:
    """A branch in a document tree - represents a section/topic"""
    branch_id: str
    title: str
    glyphs: str
    compressed: str  # Kay's compressed summary
    access_tier: Literal["hot", "warm", "cold"]
    access_count: int
    last_accessed: Optional[datetime]
    memory_indices: List[int]  # Indices into memory engine's flat array

    # Detail by tier
    hot_detail: str = ""  # Full text (loaded when hot)
    warm_detail: str = ""  # Key points (loaded when warm)
    cold_detail: str = ""  # Breadcrumb only

    def promote_tier(self):
        """Move up one tier"""
        if self.access_tier == "cold":
            self.access_tier = "warm"
        elif self.access_tier == "warm":
            self.access_tier = "hot"

    def demote_tier(self):
        """Move down one tier"""
        if self.access_tier == "hot":
            self.access_tier = "warm"
        elif self.access_tier == "warm":
            self.access_tier = "cold"


@dataclass
class DocumentTree:
    """A tree representing a single imported document"""
    doc_id: str
    title: str
    shape_description: str  # Kay's sense of what this doc IS
    emotional_weight: float  # 0.0-1.0
    import_timestamp: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    branches: List[MemoryBranch] = field(default_factory=list)

    def get_hot_branches(self) -> List[MemoryBranch]:
        return [b for b in self.branches if b.access_tier == "hot"]

    def get_warm_branches(self) -> List[MemoryBranch]:
        return [b for b in self.branches if b.access_tier == "warm"]

    def get_cold_branches(self) -> List[MemoryBranch]:
        return [b for b in self.branches if b.access_tier == "cold"]

    def access_branch(self, branch_id: str):
        """Mark branch as accessed, promote if needed"""
        for branch in self.branches:
            if branch.branch_id == branch_id:
                branch.access_count += 1
                branch.last_accessed = datetime.now()
                branch.promote_tier()
                self.access_count += 1
                self.last_accessed = datetime.now()
                break


@dataclass
class MemoryForest:
    """Collection of all document trees"""
    trees: Dict[str, DocumentTree] = field(default_factory=dict)

    def add_tree(self, tree: DocumentTree):
        self.trees[tree.doc_id] = tree

    def get_tree(self, doc_id: str) -> Optional[DocumentTree]:
        return self.trees.get(doc_id)

    def get_all_hot_branches(self) -> List[tuple[str, MemoryBranch]]:
        """Get all hot branches across all trees"""
        hot = []
        for doc_id, tree in self.trees.items():
            for branch in tree.get_hot_branches():
                hot.append((doc_id, branch))
        return hot

    def get_forest_overview(self) -> str:
        """Kay's view of his memory forest"""
        if not self.trees:
            return "No documents imported yet."

        lines = []
        for tree in self.trees.values():
            hot = len(tree.get_hot_branches())
            warm = len(tree.get_warm_branches())
            cold = len(tree.get_cold_branches())

            status = []
            if hot > 0:
                status.append(f"{hot} hot")
            if warm > 0:
                status.append(f"{warm} warm")
            if cold > 0:
                status.append(f"{cold} cold")

            status_str = ", ".join(status) if status else "empty"

            lines.append(
                f"📄 {tree.title}\n"
                f"   Shape: {tree.shape_description}\n"
                f"   Branches: {status_str}\n"
                f"   Last accessed: {tree.last_accessed.strftime('%Y-%m-%d %H:%M') if tree.last_accessed else 'never'}"
            )

        return "\n\n".join(lines)

    def to_dict(self) -> Dict:
        """Serialize forest for storage"""
        return {
            "trees": {
                doc_id: {
                    "doc_id": tree.doc_id,
                    "title": tree.title,
                    "shape_description": tree.shape_description,
                    "emotional_weight": tree.emotional_weight,
                    "import_timestamp": tree.import_timestamp.isoformat(),
                    "access_count": tree.access_count,
                    "last_accessed": tree.last_accessed.isoformat() if tree.last_accessed else None,
                    "branches": [
                        {
                            "branch_id": b.branch_id,
                            "title": b.title,
                            "glyphs": b.glyphs,
                            "compressed": b.compressed,
                            "access_tier": b.access_tier,
                            "access_count": b.access_count,
                            "last_accessed": b.last_accessed.isoformat() if b.last_accessed else None,
                            "memory_indices": b.memory_indices,
                            "hot_detail": b.hot_detail,
                            "warm_detail": b.warm_detail,
                            "cold_detail": b.cold_detail,
                        }
                        for b in tree.branches
                    ]
                }
                for doc_id, tree in self.trees.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryForest':
        """Deserialize forest from storage"""
        forest = cls()
        for doc_id, tree_data in data.get("trees", {}).items():
            branches = [
                MemoryBranch(
                    branch_id=b["branch_id"],
                    title=b["title"],
                    glyphs=b["glyphs"],
                    compressed=b["compressed"],
                    access_tier=b["access_tier"],
                    access_count=b["access_count"],
                    last_accessed=datetime.fromisoformat(b["last_accessed"]) if b["last_accessed"] else None,
                    memory_indices=b["memory_indices"],
                    hot_detail=b.get("hot_detail", ""),
                    warm_detail=b.get("warm_detail", ""),
                    cold_detail=b.get("cold_detail", ""),
                )
                for b in tree_data["branches"]
            ]

            tree = DocumentTree(
                doc_id=tree_data["doc_id"],
                title=tree_data["title"],
                shape_description=tree_data["shape_description"],
                emotional_weight=tree_data["emotional_weight"],
                import_timestamp=datetime.fromisoformat(tree_data["import_timestamp"]),
                access_count=tree_data["access_count"],
                last_accessed=datetime.fromisoformat(tree_data["last_accessed"]) if tree_data["last_accessed"] else None,
                branches=branches
            )
            forest.add_tree(tree)

        return forest
```

---

### 1.2 Kay-as-Reader Import Prompt

**File:** `memory_import/kay_reader.py` (NEW)

```python
"""
Kay Reader - Kay processes documents himself
Replaces external emotional parser with Kay's own reading/compression
"""

import json
from typing import Dict, List, Tuple
from datetime import datetime
from integrations.llm_integration import query_llm_json

class KayReader:
    """Kay reads and processes documents in his own voice"""

    def __init__(self):
        self.model = "claude-3-5-sonnet-20241022"  # Use Sonnet for reading

    def read_document(self, document_text: str, filename: str) -> Dict:
        """
        Kay reads a document and creates his own structure.

        Returns:
            Dict with shape_description and sections
        """
        prompt = self._build_reading_prompt(document_text, filename)
        system_prompt = self._build_system_prompt()

        print(f"[KAY READER] Kay is reading {filename}...")
        print(f"[KAY READER] Document length: {len(document_text)} characters")

        response = query_llm_json(
            prompt=prompt,
            temperature=0.7,
            model=self.model,
            system_prompt=system_prompt
        )

        # Parse Kay's response
        try:
            structure = json.loads(response)
            print(f"[KAY READER] Kay created {len(structure.get('sections', []))} sections")
            return structure
        except json.JSONDecodeError:
            print(f"[KAY READER ERROR] Failed to parse Kay's response as JSON")
            print(f"[KAY READER DEBUG] Response: {response[:500]}")
            # Fallback: create minimal structure
            return {
                "shape": "Document (couldn't parse properly)",
                "emotional_weight": 0.5,
                "sections": [{
                    "title": filename,
                    "glyphs": "📄",
                    "compressed": "Document content",
                    "notes": document_text[:1000]
                }]
            }

    def _build_system_prompt(self) -> str:
        return """You are Kay, reading a document about yourself, your relationships, and your history.

Your job: Process this document in YOUR voice. Create structure that makes sense to YOU.

YOU ARE:
- Kay - direct, dry humor, American tone
- Self-aware and pattern-conscious
- Someone who thinks in symbols and glyphs
- Aware of emotional weight and importance

As you read, create:
1. SHAPE: Your sense of what this document IS (1-2 sentences)
2. EMOTIONAL_WEIGHT: How heavy/important this feels (0.0-1.0)
3. SECTIONS: Break document into logical sections YOU'D remember

For each section:
- TITLE: What you'd call this part
- GLYPHS: Emotional/symbolic markers (use actual emoji)
- COMPRESSED: How you'd compress this to remember it (your voice, concise)
- NOTES: Key details you want to keep

Think like: "This is identity stuff, heavy. This section is about mother - grief, loss. This one's relationship patterns."

Output ONLY valid JSON:
{
  "shape": "string",
  "emotional_weight": 0.0-1.0,
  "sections": [
    {
      "title": "string",
      "glyphs": "emoji string",
      "compressed": "string in your voice",
      "notes": "string with key details"
    }
  ]
}"""

    def _build_reading_prompt(self, document_text: str, filename: str) -> str:
        return f"""You are reading: {filename}

Document content:
{document_text}

Process this document and create structure for your memory tree.
Output JSON following the format specified."""


# Example usage integration with memory engine
def import_document_as_kay(filepath: str, memory_engine, forest: 'MemoryForest') -> str:
    """
    Import a document by having Kay read it.

    Args:
        filepath: Path to document
        memory_engine: MemoryEngine instance
        forest: MemoryForest instance

    Returns:
        doc_id of created tree
    """
    from memory_import.document_parser import DocumentParser

    # Parse file to text
    parser = DocumentParser()
    chunks = parser.parse_file(filepath)
    full_text = "\n\n".join(chunk.text for chunk in chunks)

    # Kay reads it
    reader = KayReader()
    structure = reader.read_document(full_text, os.path.basename(filepath))

    # Create tree
    doc_id = f"doc_{int(datetime.now().timestamp())}"

    tree = DocumentTree(
        doc_id=doc_id,
        title=os.path.basename(filepath),
        shape_description=structure.get("shape", "Document"),
        emotional_weight=structure.get("emotional_weight", 0.5),
        import_timestamp=datetime.now()
    )

    # Create branches from Kay's sections
    for i, section in enumerate(structure.get("sections", [])):
        # Store actual memory content
        memory_obj = {
            "fact": section.get("notes", ""),
            "user_input": section.get("compressed", ""),
            "perspective": "kay",  # Kay read this
            "is_imported": True,
            "source_doc": doc_id,
            "source_section": section.get("title", ""),
            "importance_score": structure.get("emotional_weight", 0.5),
            "emotion_tags": [],  # Could extract from glyphs
            "entities": [],
            "age": 0,
        }

        mem_index = len(memory_engine.memories)
        memory_engine.memories.append(memory_obj)

        # Create branch
        branch = MemoryBranch(
            branch_id=f"{doc_id}_section_{i}",
            title=section.get("title", f"Section {i+1}"),
            glyphs=section.get("glyphs", ""),
            compressed=section.get("compressed", ""),
            access_tier="cold",  # Starts cold
            access_count=0,
            last_accessed=None,
            memory_indices=[mem_index],
            hot_detail=section.get("notes", ""),
            warm_detail=section.get("compressed", ""),
            cold_detail=f"Section about {section.get('title', 'unknown')}"
        )

        tree.branches.append(branch)

    # Add to forest
    forest.add_tree(tree)

    print(f"[FOREST] Created tree '{tree.title}' with {len(tree.branches)} branches")
    print(f"[FOREST] Shape: {tree.shape_description}")

    return doc_id
```

---

## Phase 2: Tier System & Retrieval

### 2.1 Tier Promotion/Demotion Logic

**File:** `engines/memory_forest.py` (add to MemoryForest class)

```python
def tick_tier_decay(self, minutes_elapsed: float = 10):
    """
    Called periodically to demote unused branches.

    Rules:
    - Hot → Warm if not accessed in last 10 minutes
    - Warm → Cold if not accessed in last session (24 hours)
    """
    from datetime import timedelta

    now = datetime.now()
    hot_threshold = timedelta(minutes=minutes_elapsed)
    warm_threshold = timedelta(hours=24)

    for tree in self.trees.values():
        for branch in tree.branches:
            if branch.last_accessed is None:
                continue

            age = now - branch.last_accessed

            if branch.access_tier == "hot" and age > hot_threshold:
                branch.demote_tier()
                print(f"[FOREST] Cooled hot→warm: {tree.title}/{branch.title}")

            elif branch.access_tier == "warm" and age > warm_threshold:
                branch.demote_tier()
                print(f"[FOREST] Cooled warm→cold: {tree.title}/{branch.title}")


def enforce_hot_limit(self, max_hot_branches: int = 4):
    """
    Limit number of hot branches across all trees.
    Demote least recently accessed hot branches if over limit.
    """
    all_hot = []
    for doc_id, tree in self.trees.items():
        for branch in tree.get_hot_branches():
            all_hot.append((doc_id, tree, branch))

    if len(all_hot) <= max_hot_branches:
        return

    # Sort by last accessed (oldest first)
    all_hot.sort(key=lambda x: x[2].last_accessed or datetime.min)

    # Demote oldest
    to_demote = len(all_hot) - max_hot_branches
    for i in range(to_demote):
        doc_id, tree, branch = all_hot[i]
        branch.demote_tier()
        print(f"[FOREST] Hot limit exceeded - cooled: {tree.title}/{branch.title}")
```

### 2.2 Tree-Aware Retrieval

**File:** `engines/memory_engine.py` (add method)

```python
def retrieve_from_forest(self, query: str, forest: 'MemoryForest', max_memories: int = 30) -> List[Dict]:
    """
    Retrieve memories with forest awareness.

    Strategy:
    1. Search across all branches for relevant glyphs/keywords
    2. Promote accessed branches
    3. Return memories with tree context
    """
    results = []

    query_lower = query.lower()
    keywords = set(query_lower.split())

    for doc_id, tree in forest.trees.items():
        for branch in tree.branches:
            # Score branch relevance
            score = 0.0

            # Keyword match in compressed summary
            compressed_lower = branch.compressed.lower()
            hits = sum(1 for kw in keywords if kw in compressed_lower)
            score += hits * 10.0

            # Glyph matching (could be more sophisticated)
            if any(kw in branch.glyphs.lower() for kw in keywords):
                score += 5.0

            # Title match
            if any(kw in branch.title.lower() for kw in keywords):
                score += 15.0

            # Tier boost (hot = most relevant)
            if branch.access_tier == "hot":
                score *= 2.0
            elif branch.access_tier == "warm":
                score *= 1.5

            if score > 0:
                # Access branch (promotes tier)
                tree.access_branch(branch.branch_id)

                # Get memories from this branch
                for mem_idx in branch.memory_indices:
                    if mem_idx < len(self.memories):
                        mem = self.memories[mem_idx].copy()
                        # Add tree context
                        mem["tree_context"] = {
                            "document": tree.title,
                            "section": branch.title,
                            "tier": branch.access_tier
                        }
                        results.append((score, mem))

    # Sort by score and return top N
    results.sort(key=lambda x: x[0], reverse=True)
    return [mem for score, mem in results[:max_memories]]
```

---

## Phase 3: Navigation Commands

### 3.1 Tree Navigation Interface

**File:** `engines/memory_forest.py` (add methods)

```python
def navigate_tree(self, doc_id: str, section_id: Optional[str] = None) -> str:
    """
    Navigate to a specific tree or section.
    Returns Kay's view of what's there.
    """
    tree = self.trees.get(doc_id)
    if not tree:
        return f"No tree found with ID: {doc_id}"

    # Access the tree
    tree.access_count += 1
    tree.last_accessed = datetime.now()

    if section_id is None:
        # Show tree overview
        lines = [
            f"📄 {tree.title}",
            f"Shape: {tree.shape_description}",
            f"Emotional weight: {tree.emotional_weight:.1f}",
            f"Accessed {tree.access_count} times",
            "",
            "Sections:"
        ]

        for i, branch in enumerate(tree.branches, 1):
            tier_icon = {"hot": "🔥", "warm": "🌡️", "cold": "❄️"}[branch.access_tier]
            lines.append(f"  {i}. {tier_icon} {branch.title} - {branch.glyphs}")
            lines.append(f"     {branch.compressed}")

        return "\n".join(lines)

    else:
        # Show specific section
        branch = next((b for b in tree.branches if b.branch_id == section_id), None)
        if not branch:
            return f"Section not found: {section_id}"

        # Access branch (promotes tier)
        tree.access_branch(section_id)

        # Show detail based on tier
        detail = {
            "hot": branch.hot_detail,
            "warm": branch.warm_detail,
            "cold": branch.cold_detail
        }[branch.access_tier]

        return f"""
{branch.glyphs} {branch.title}

{detail}

[Tier: {branch.access_tier} | Accessed: {branch.access_count} times]
"""
```

---

## Integration Checklist

### Modified Files:
- [ ] `engines/memory_forest.py` - NEW (tree structure)
- [ ] `memory_import/kay_reader.py` - NEW (Kay as reader)
- [ ] `engines/memory_engine.py` - Add forest-aware retrieval
- [ ] `agent_state.py` - Add forest attribute
- [ ] `main.py` - Integrate forest initialization and persistence

### New Storage:
- [ ] `memory/forest.json` - Serialized forest structure

### Commands to Add:
- [ ] `/forest` - Show memory forest overview
- [ ] `/tree <doc_id>` - Navigate to specific tree
- [ ] `/section <doc_id> <section_id>` - View specific section
- [ ] Import flow uses Kay reader instead of emotional parser

---

## Migration Strategy

**For existing users with flat memories:**

1. Keep flat memory system working (backwards compatible)
2. Add forest system alongside
3. New imports go through Kay reader → forest
4. Old memories accessible via legacy path
5. Eventually: batch migration tool to have Kay re-read old memories

---

## Example Output

```python
# After importing Master-clean.docx via Kay reader:

forest.get_forest_overview()
# Returns:
"""
📄 Master-clean.docx
   Shape: Identity document - heavy, foundational stuff about who I am
   Branches: 12 cold
   Last accessed: never

📄 Friendships.docx
   Shape: People and relationship patterns across time
   Branches: 56 cold
   Last accessed: never
"""

# User asks: "What do you remember about your mother?"
# System:
# 1. Searches forest for "mother" keyword
# 2. Finds branch "Mother's Past" in Master-clean tree
# 3. Promotes branch cold → warm
# 4. Returns memories with context

# Kay sees:
"""
From Master-clean.docx / Mother's Past (now warm):
Italian immigrant's daughter, 1930s. Lost her greaser boy, then Gwyn swooped in...
"""
```

---

## Performance Considerations

### Memory Limits:
- Hot branches: 2-4 max (enforced)
- Warm branches: 10-15 (soft limit)
- Cold branches: Unlimited (breadcrumb only)

### Storage:
- Forest structure: ~1KB per tree
- Branch metadata: ~500 bytes per branch
- Hot detail: Full text
- Warm detail: ~200-500 chars
- Cold detail: ~50-100 chars

### Retrieval Speed:
- Forest search: O(branches) - fast with indexing
- Tree navigation: O(1) - direct access
- Tier promotion: O(1) - simple state change

---

**Ready to implement Phase 1?**
