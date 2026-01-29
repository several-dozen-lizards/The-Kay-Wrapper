import os
import json
import re
from pathlib import Path
from typing import List, Dict, Set, Optional

class DocumentIndex:
    """
    Fast searchable index of all imported document trees.
    Searched BEFORE chunk-level retrieval to ensure complete document access.
    """

    def __init__(self, trees_dir: str = "data/trees", print_diagnostic: bool = False):
        self.trees_dir = Path(trees_dir)
        self.index = {}
        self.entity_index = {}  # NEW: Maps entity -> set of doc_ids

        if self.trees_dir.exists():
            self.index = self._build_index()
            if print_diagnostic:
                self._print_diagnostic()
        else:
            print(f"[DOCUMENT INDEX] Warning: Trees directory not found: {self.trees_dir}")

    def _extract_entities_from_filename(self, filename: str) -> Set[str]:
        """
        Extract entity keywords from filename.

        Handles common patterns:
        - "pigeons.txt" -> {"pigeon", "pigeons"}
        - "Re_pigeons.txt" -> {"re", "pigeon", "pigeons"}
        - "fancy_pigeons.txt" -> {"fancy", "pigeon", "pigeons", "fancy pigeon"}
        """
        entities = set()

        # Remove file extension
        name_base = filename.lower()
        if '.' in name_base:
            name_base = name_base.rsplit('.', 1)[0]

        # Replace separators with spaces
        name_clean = re.sub(r'[_\-]', ' ', name_base)

        # Extract words
        words = [w.strip() for w in name_clean.split() if len(w.strip()) > 2]

        # Add individual words
        for word in words:
            entities.add(word)

            # Add singular/plural variants
            if word.endswith('s') and len(word) > 3:
                # "pigeons" -> "pigeon"
                entities.add(word[:-1])
            else:
                # "pigeon" -> "pigeons"
                entities.add(word + 's')

        # Add multi-word phrases for 2-3 word filenames
        if len(words) == 2:
            # "fancy pigeons" -> {"fancy pigeon", "fancy pigeons"}
            entities.add(' '.join(words))
            # Try singular/plural of second word
            if words[1].endswith('s'):
                entities.add(f"{words[0]} {words[1][:-1]}")
            else:
                entities.add(f"{words[0]} {words[1]}s")

        return entities

    def _extract_entities_from_content(self, text: str, max_entities: int = 20) -> Set[str]:
        """
        Extract entity keywords from document content.

        Looks for:
        - Capitalized words (potential proper nouns)
        - Repeated significant words
        """
        entities = set()

        # Extract capitalized words (potential proper nouns)
        # Match words that start with capital and are 3+ chars
        capitalized = re.findall(r'\b[A-Z][a-z]{2,}\b', text)

        # Count frequency
        from collections import Counter
        word_freq = Counter(capitalized)

        # Take top frequent capitalized words
        for word, count in word_freq.most_common(max_entities):
            if count >= 2:  # Mentioned at least twice
                entities.add(word.lower())

                # Add singular/plural
                if word.lower().endswith('s'):
                    entities.add(word.lower()[:-1])
                else:
                    entities.add(word.lower() + 's')

        return entities

    def _build_index(self) -> Dict[str, Dict]:
        """Build searchable index from all tree files.

        ACTUAL TREE STRUCTURE:
        {
          "trees": {
            "doc_id": {
              "doc_id": "...",
              "title": "filename.txt",
              "branches": [
                {"title": "Branch Name", "chunk_indices": [0, 1, 2], ...}
              ]
            }
          }
        }
        """
        index = {}

        if not self.trees_dir.exists():
            return index

        tree_files = list(self.trees_dir.glob("tree_doc_*.json"))
        print(f"[DOCUMENT INDEX] Found {len(tree_files)} tree files")

        # Load documents.json once for keyword extraction
        docs_data = {}
        docs_file = Path("memory/documents.json")
        if docs_file.exists():
            try:
                with open(docs_file, 'r', encoding='utf-8') as f:
                    docs_data = json.load(f)
            except Exception as e:
                print(f"[DOCUMENT INDEX] Warning: Could not load documents.json: {e}")

        for tree_file in tree_files:
            print(f"[DOCUMENT INDEX] Processing: {tree_file.name}")
            try:
                with open(tree_file, 'r', encoding='utf-8') as f:
                    tree_data = json.load(f)

                print(f"[DOCUMENT INDEX]   Loaded JSON successfully")

                # Handle TWO tree formats:
                # Format 1 (nested): {"trees": {"doc_id": {...}}}
                # Format 2 (flat): {"doc_id": "...", "title": "...", "branches": [...]}

                if 'trees' in tree_data:
                    # Nested format
                    print(f"[DOCUMENT INDEX]   Format: Nested (trees key)")
                    trees = tree_data.get('trees', {})
                    if not trees:
                        print(f"[DOCUMENT INDEX]   SKIP: Empty trees dict")
                        continue

                    # Get first (and usually only) tree in the file
                    doc_id = list(trees.keys())[0]
                    tree = trees[doc_id]
                elif 'doc_id' in tree_data:
                    # Flat format (direct from MemoryForest)
                    print(f"[DOCUMENT INDEX]   Format: Flat (doc_id at top level)")
                    doc_id = tree_data.get('doc_id')
                    tree = tree_data  # The whole file is the tree
                else:
                    print(f"[DOCUMENT INDEX]   SKIP: Unknown format")
                    print(f"[DOCUMENT INDEX]   Available keys: {list(tree_data.keys())}")
                    continue

                print(f"[DOCUMENT INDEX]   doc_id: {doc_id}")

                filename = tree.get('title', 'unknown')
                branches = tree.get('branches', [])  # List, not dict!
                total_chunks = tree.get('total_chunks', 0)

                # Extract searchable keywords from branches and content
                keywords = set()

                # Common stop words to exclude
                stop_words = {'the', 'and', 'are', 'you', 'any', 'have', 'been', 'see', 'can', 'for',
                             'this', 'that', 'from', 'with', 'what', 'they', 'there', 'here', 'then',
                             'than', 'your', 'their', 'about', 'would', 'could', 'should', 'were'}

                # Add filename (clean punctuation)
                filename_clean = re.sub(r'[^\w\s]', ' ', filename.lower())
                filename_words = [w for w in filename_clean.split() if len(w) > 2 and w not in stop_words]
                keywords.update(filename_words)

                # Branches is an array of objects
                branch_names = []
                for branch in branches:
                    branch_title = branch.get('title', '')
                    branch_names.append(branch_title)

                    # Clean branch title and add keywords
                    branch_clean = re.sub(r'[^\w\s]', ' ', branch_title.lower())
                    branch_words = [w for w in branch_clean.split() if len(w) > 2 and w not in stop_words]
                    keywords.update(branch_words)

                # Extract keywords from document full text if available
                if doc_id in docs_data:
                    doc = docs_data[doc_id]
                    full_text = doc.get('full_text', '')[:500]  # First 500 chars
                    # Clean punctuation
                    text_clean = re.sub(r'[^\w\s]', ' ', full_text.lower())
                    # Extract meaningful words (3+ chars, not stop words, alphabetic)
                    text_words = [w for w in text_clean.split()
                                 if len(w) > 3 and w.isalpha() and w not in stop_words]
                    keywords.update(text_words[:20])  # First 20 meaningful words

                # NEW: Extract entities from filename
                filename_entities = self._extract_entities_from_filename(filename)

                # NEW: Extract entities from content
                content_entities = set()
                if doc_id in docs_data:
                    doc = docs_data[doc_id]
                    full_text = doc.get('full_text', '')
                    if full_text:
                        content_entities = self._extract_entities_from_content(full_text)

                # Combine all entities
                all_entities = filename_entities | content_entities

                index[doc_id] = {
                    'filename': filename,
                    'branches': branch_names,
                    'keywords': keywords,
                    'entities': all_entities,  # NEW: Store entities
                    'tree_file': str(tree_file),
                    'chunk_count': total_chunks
                }

                # NEW: Update entity_index (entity -> doc_ids mapping)
                for entity in all_entities:
                    if entity not in self.entity_index:
                        self.entity_index[entity] = set()
                    self.entity_index[entity].add(doc_id)

                print(f"[DOCUMENT INDEX] Indexed: {filename} ({total_chunks} chunks, {len(keywords)} keywords, {len(all_entities)} entities)")
                if all_entities:
                    sample_entities = list(all_entities)[:5]
                    print(f"[DOCUMENT INDEX]   Entities: {', '.join(sample_entities)}")

            except Exception as e:
                print(f"[DOCUMENT INDEX] FAILED to index {tree_file.name}")
                print(f"[DOCUMENT INDEX]   Error: {e}")
                print(f"[DOCUMENT INDEX]   Error type: {type(e).__name__}")
                import traceback
                print(f"[DOCUMENT INDEX]   Traceback:")
                traceback.print_exc()
                continue

        print(f"[DOCUMENT INDEX] Successfully indexed {len(index)} documents")
        return index

    def _print_diagnostic(self):
        """Print diagnostic information about the index."""
        print("\n" + "="*80)
        print("=== DOCUMENT INDEX DIAGNOSTIC ===")
        print("="*80)
        print(f"Trees directory: {self.trees_dir}")
        print(f"Total documents indexed: {len(self.index)}")
        print(f"Total entities in entity_index: {len(self.entity_index)}")

        for doc_id, meta in self.index.items():
            print(f"\n  Doc: {meta['filename']}")
            print(f"    - ID: {doc_id}")
            print(f"    - Branches: {', '.join(meta['branches'])}")
            print(f"    - Chunks: {meta['chunk_count']}")
            print(f"    - Sample keywords: {', '.join(list(meta['keywords'])[:10])}")
            print(f"    - Entities: {', '.join(list(meta.get('entities', []))[:10])}")

        # Show sample entity mappings
        print(f"\n  Sample Entity Mappings (first 20):")
        for i, (entity, doc_ids) in enumerate(list(self.entity_index.items())[:20]):
            doc_names = [self.index[did]['filename'] for did in doc_ids if did in self.index]
            print(f"    '{entity}' -> {doc_names}")

        print("\n" + "="*80)
        print("=== END DIAGNOSTIC ===")
        print("="*80 + "\n")

    def refresh(self):
        """
        Refresh the index - check for new tree files and rebuild.
        Call this after importing new documents.
        """
        print("[DOCUMENT INDEX] Refreshing index...")

        # Count current vs new
        old_count = len(self.index)

        # Clear entity_index before rebuild
        self.entity_index = {}

        # Rebuild from scratch (also rebuilds entity_index)
        self.index = self._build_index()

        new_count = len(self.index)

        if new_count > old_count:
            print(f"[DOCUMENT INDEX] Added {new_count - old_count} new documents (total: {new_count})")
        elif new_count == old_count:
            print(f"[DOCUMENT INDEX] No new documents (still {new_count} total)")
        else:
            print(f"[DOCUMENT INDEX] Warning: Document count decreased: {old_count} -> {new_count}")

        # Log entity index stats
        print(f"[DOCUMENT INDEX] Entity index: {len(self.entity_index)} entities mapped to documents")

    def search(self, query: str, min_score: float = 0.2) -> List[str]:
        """
        Search document index for query.
        Returns list of doc_ids that match, sorted by relevance.

        NEW: Checks entity_index FIRST for entity matches with 10.0x boost.
        """
        # Clean query: remove punctuation, normalize whitespace
        query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
        # Split and filter: only words 3+ chars (skip "the", "is", "a", etc)
        query_words = set(w for w in query_clean.split() if len(w) > 2)

        # Remove common stop words that don't help matching
        stop_words = {'the', 'and', 'are', 'you', 'any', 'have', 'been', 'see', 'can', 'for',
                      'this', 'that', 'from', 'with', 'what', 'they', 'there', 'here', 'then',
                      'than', 'your', 'their', 'about', 'would', 'could', 'should', 'were'}
        query_words = query_words - stop_words

        print(f"[DOCUMENT INDEX] Searching for: '{query}'")
        print(f"[DOCUMENT INDEX] Query words (cleaned): {query_words}")

        if not query_words:
            print(f"[DOCUMENT INDEX] Warning: No meaningful query words after cleaning")
            return []

        # NEW: Step 1 - Check entity_index for entity matches (PRIORITY)
        entity_matched_docs = set()
        for word in query_words:
            # Check exact entity match
            if word in self.entity_index:
                entity_matched_docs.update(self.entity_index[word])
                print(f"[DOCUMENT INDEX] Entity match: '{word}' -> {len(self.entity_index[word])} docs")

            # Check singular/plural variants
            if word.endswith('s') and len(word) > 3:
                singular = word[:-1]
                if singular in self.entity_index:
                    entity_matched_docs.update(self.entity_index[singular])
                    print(f"[DOCUMENT INDEX] Entity match (singular): '{singular}' -> {len(self.entity_index[singular])} docs")
            else:
                plural = word + 's'
                if plural in self.entity_index:
                    entity_matched_docs.update(self.entity_index[plural])
                    print(f"[DOCUMENT INDEX] Entity match (plural): '{plural}' -> {len(self.entity_index[plural])} docs")

        matches = []

        # Process all documents
        for doc_id, doc_meta in self.index.items():
            score = 0.0
            match_strategy = None

            # PRIORITY: Entity match gets massive 10.0 base score
            if doc_id in entity_matched_docs:
                score = 10.0
                match_strategy = "entity_map"
                print(f"  [ENTITY MATCH] {doc_meta['filename']}: score={score:.2f} (entity_map)")

            # Secondary: Keyword matching (normal scoring)
            keyword_matches = len(query_words & doc_meta['keywords'])

            # Boost for filename matches
            filename_matches = sum(1 for word in query_words
                                  if word in doc_meta['filename'].lower())
            if filename_matches > 0:
                keyword_matches += filename_matches * 2

            # Boost for branch name matches
            branch_matches = sum(1 for branch in doc_meta['branches']
                               for word in query_words
                               if word in branch.lower())
            if branch_matches > 0:
                keyword_matches += branch_matches

            keyword_score = keyword_matches / max(len(query_words), 1)

            # Combine scores: entity match (10.0) + keyword bonus
            if match_strategy == "entity_map":
                # Entity match already has 10.0, add keyword bonus
                score += keyword_score
            else:
                # Pure keyword matching
                score = keyword_score
                if keyword_score >= min_score:
                    match_strategy = "keyword_matching"

            # Accept match if score meets threshold
            if score >= min_score:
                matches.append((doc_id, score, doc_meta, match_strategy))
                if match_strategy == "keyword_matching":
                    print(f"  [KEYWORD MATCH] {doc_meta['filename']}: score={score:.2f} ({keyword_matches} matches)")
            elif keyword_matches > 0 and match_strategy != "entity_map":
                print(f"  [WEAK] {doc_meta['filename']}: score={score:.2f} (below threshold)")

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)

        matched_ids = [match[0] for match in matches]
        print(f"[DOCUMENT INDEX] Found {len(matched_ids)} matching documents")

        # Log matching strategies used
        if matches:
            entity_count = sum(1 for m in matches if m[3] == "entity_map")
            keyword_count = sum(1 for m in matches if m[3] == "keyword_matching")
            print(f"[DOCUMENT INDEX] Match strategies: {entity_count} entity_map, {keyword_count} keyword_matching")

        return matched_ids
    
    def load_tree(self, doc_id: str) -> Optional[Dict]:
        """Load complete tree data AND document content for a document.

        Returns combined structure with:
        - Tree metadata (branches, structure)
        - Full document text from documents.json
        """
        doc_meta = self.index.get(doc_id)
        if not doc_meta:
            print(f"[DOCUMENT INDEX] Warning: doc_id {doc_id} not in index")
            return None

        try:
            # Load tree structure
            with open(doc_meta['tree_file'], 'r', encoding='utf-8') as f:
                tree_data = json.load(f)

            # Load document full text from documents.json
            docs_file = Path("memory/documents.json")
            if docs_file.exists():
                with open(docs_file, 'r', encoding='utf-8') as f:
                    docs = json.load(f)

                doc = docs.get(doc_id)
                if doc:
                    # Add full_text to tree_data for chunk extraction
                    trees = tree_data.get('trees', {})
                    if doc_id in trees:
                        trees[doc_id]['full_text'] = doc.get('full_text', '')
                        trees[doc_id]['source_file'] = doc.get('filename', doc_meta['filename'])

            print(f"[DOCUMENT INDEX] Loaded tree: {doc_meta['filename']}")
            return tree_data

        except Exception as e:
            print(f"[DOCUMENT INDEX] Error loading tree: {e}")
            return None