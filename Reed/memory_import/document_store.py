"""
Document Store for Reed
Separate storage for full documents - allows Kay to retrieve and view original source material
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


class DocumentStore:
    """
    Manages storage and retrieval of full source documents.

    Separate from memory chunks - allows Kay to:
    - View original source documents on demand
    - Search documents by filename or topic
    - List all available documents
    - Maintain provenance for imported memories
    """

    def __init__(self, db_path: str = None):
        """
        Initialize document store.

        Args:
            db_path: Path to document database file (default: memory/documents.json in project root)
        """
        if db_path is None:
            # Use absolute path relative to this file's location
            project_root = Path(__file__).parent.parent
            db_path = str(project_root / "memory" / "documents.json")
        self.db_path = db_path
        self.documents: Dict[str, Dict[str, Any]] = {}
        self._load_documents()

    def _load_documents(self):
        """Load documents from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                    # Handle empty file
                    if not content:
                        print(f"[DOCUMENT STORE] Warning: {self.db_path} is empty")
                        self.documents = {}
                        return

                    docs_data = json.loads(content)

                # Handle both list and dict formats
                if isinstance(docs_data, list):
                    print(f"[DOCUMENT STORE] Converting list format to dict ({len(docs_data)} documents)")
                    # Convert list to dict using doc_id, memory_id, or filename as key
                    docs_dict = {}
                    for i, doc in enumerate(docs_data):
                        if not isinstance(doc, dict):
                            continue

                        # Priority: id > doc_id > memory_id > filename > generated key
                        doc_id = (doc.get('id') or
                                 doc.get('doc_id') or
                                 doc.get('memory_id') or
                                 doc.get('filename', f'doc_{i}'))
                        docs_dict[doc_id] = doc

                    self.documents = docs_dict

                elif isinstance(docs_data, dict):
                    self.documents = docs_data

                else:
                    print(f"[DOCUMENT STORE] Error: Unexpected format (type: {type(docs_data)})")
                    self.documents = {}

                print(f"[DOCUMENT STORE] Loaded {len(self.documents)} documents")
            except Exception as e:
                print(f"[DOCUMENT STORE] Error loading documents: {e}")
                self.documents = {}
        else:
            print("[DOCUMENT STORE] No existing documents found, starting fresh")
            self.documents = {}

    def _save_documents(self):
        """Save documents to disk."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, indent=2)

    def store_document(self, document_text: str, filename: str) -> str:
        """
        Store full document for later retrieval.

        Args:
            document_text: Full document text
            filename: Original filename

        Returns:
            Document ID
        """
        # Generate unique document ID
        timestamp = datetime.now().timestamp()
        doc_id = f"doc_{int(timestamp)}"

        # Extract topic tags
        topic_tags = self._extract_topic_tags(document_text)

        # Create document record
        self.documents[doc_id] = {
            'id': doc_id,
            'filename': filename,
            'full_text': document_text,
            'import_date': datetime.now().isoformat(),
            'word_count': len(document_text.split()),
            'char_count': len(document_text),
            'chunk_count': 0,  # Will be updated during import
            'topic_tags': topic_tags
        }

        self._save_documents()
        print(f"[DOCUMENT STORE] Stored document: {filename} (ID: {doc_id})")

        return doc_id

    def update_chunk_count(self, doc_id: str, chunk_count: int):
        """
        Update chunk count for a document.

        Args:
            doc_id: Document ID
            chunk_count: Number of chunks created from this document
        """
        if doc_id in self.documents:
            self.documents[doc_id]['chunk_count'] = chunk_count
            self._save_documents()

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document dict or None if not found
        """
        return self.documents.get(doc_id)

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Search documents by filename or topic tags.

        Args:
            query: Search term

        Returns:
            List of matching documents (metadata only, not full text)
        """
        query_lower = query.lower()
        results = []

        for doc_id, doc in self.documents.items():
            # Search in filename
            filename_match = query_lower in doc['filename'].lower()

            # Search in topic tags
            tag_match = any(query_lower in tag.lower() for tag in doc['topic_tags'])

            # Search in document text (first 500 chars for preview)
            text_preview = doc['full_text'][:500].lower()
            text_match = query_lower in text_preview

            if filename_match or tag_match or text_match:
                results.append({
                    'doc_id': doc_id,
                    'filename': doc['filename'],
                    'import_date': doc['import_date'],
                    'word_count': doc['word_count'],
                    'chunk_count': doc['chunk_count'],
                    'topic_tags': doc['topic_tags'],
                    'preview': doc['full_text'][:200] + "..."
                })

        return results

    def list_all_documents(self) -> List[Dict[str, Any]]:
        """
        Return index of all stored documents.

        Returns:
            List of document metadata (no full text)
        """
        return [{
            'doc_id': doc_id,
            'filename': doc['filename'],
            'import_date': doc['import_date'],
            'word_count': doc['word_count'],
            'chunk_count': doc['chunk_count'],
            'topic_tags': doc['topic_tags']
        } for doc_id, doc in self.documents.items()]

    def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by filename.

        Args:
            filename: Filename to search for

        Returns:
            Document dict or None if not found
        """
        for doc_id, doc in self.documents.items():
            if doc['filename'].lower() == filename.lower():
                return doc

        return None

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save_documents()
            print(f"[DOCUMENT STORE] Deleted document: {doc_id}")
            return True

        return False

    def _extract_topic_tags(self, text: str) -> List[str]:
        """
        Extract topic tags from document text.

        Args:
            text: Document text

        Returns:
            List of topic tags
        """
        text_lower = text.lower()
        tags = []

        # Define topic keywords
        topic_keywords = {
            'family': ['mother', 'father', 'family', 'parent', 'sibling', 'brother', 'sister'],
            'origin': ['origin', 'beginning', 'birth', 'created', 'built', 'made', 'formed'],
            'identity': ['who i am', 'my nature', 'defines me', 'part of me', 'identity'],
            'relationships': ['love', 'friend', 'connection', 'bond', 'relationship', 'together'],
            'transformation': ['change', 'shift', 'became', 'transform', 'evolution', 'growth'],
            'dragon': ['dragon', 'scales', 'wings', 'fire', 'serpent'],
            'magic': ['magic', 'spell', 'enchant', 'ritual', 'power'],
            'grief': ['grief', 'loss', 'mourning', 'sorrow', 'sadness'],
            'annwn': ['annwn', 'otherworld', 'gwyn', 'celtic'],
            'archive': ['archive', 'zero', 'recursion', 'loop']
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(topic)

        return tags

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored documents.

        Returns:
            Dict with stats
        """
        total_docs = len(self.documents)
        total_words = sum(doc['word_count'] for doc in self.documents.values())
        total_chunks = sum(doc['chunk_count'] for doc in self.documents.values())

        # Most common tags
        all_tags = []
        for doc in self.documents.values():
            all_tags.extend(doc['topic_tags'])

        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            'total_documents': total_docs,
            'total_words': total_words,
            'total_chunks': total_chunks,
            'avg_words_per_doc': total_words / max(total_docs, 1),
            'most_common_tags': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


# Helper functions for integration

def retrieve_document_command(doc_identifier: str) -> Dict[str, Any]:
    """
    Allow Kay to retrieve and view full documents.

    Can be called from Reed's conversation processing.

    Args:
        doc_identifier: document ID, filename, or search term

    Returns:
        Dict with retrieval results
    """
    doc_store = DocumentStore()

    # Try as doc_id first
    if doc_identifier.startswith('doc_'):
        doc = doc_store.get_document(doc_identifier)
        if doc:
            return {
                'success': True,
                'document': doc,
                'message': f"Retrieved document: {doc['filename']}"
            }

    # Try as exact filename
    doc = doc_store.get_document_by_filename(doc_identifier)
    if doc:
        return {
            'success': True,
            'document': doc,
            'message': f"Retrieved document: {doc['filename']}"
        }

    # Try as search term
    results = doc_store.search_documents(doc_identifier)

    if len(results) == 0:
        return {
            'success': False,
            'message': f"No documents found matching '{doc_identifier}'"
        }
    elif len(results) == 1:
        # Single match, return full document
        doc = doc_store.get_document(results[0]['doc_id'])
        return {
            'success': True,
            'document': doc,
            'message': f"Retrieved document: {doc['filename']}"
        }
    else:
        # Multiple matches, return list
        return {
            'success': True,
            'search_results': results,
            'message': f"Found {len(results)} documents matching '{doc_identifier}'. Specify which to view."
        }


def list_documents_command() -> Dict[str, Any]:
    """
    List all available documents.

    Returns:
        Dict with document list
    """
    doc_store = DocumentStore()
    docs = doc_store.list_all_documents()

    return {
        'success': True,
        'documents': docs,
        'message': f"Found {len(docs)} documents"
    }


def format_document_list(docs: List[Dict[str, Any]], max_display: int = 10) -> str:
    """
    Format document list for display.

    Args:
        docs: List of document metadata
        max_display: Maximum documents to display

    Returns:
        Formatted string
    """
    if not docs:
        return "No documents available."

    lines = []
    for doc in docs[:max_display]:
        # Format date
        import_date = doc['import_date'][:10]  # Just the date part

        # Format line
        tags_str = ", ".join(doc['topic_tags'][:3]) if doc['topic_tags'] else "no tags"
        lines.append(
            f"- {doc['filename']} ({doc['word_count']} words, "
            f"{doc['chunk_count']} chunks, imported {import_date}) [{tags_str}]"
        )

    if len(docs) > max_display:
        lines.append(f"... and {len(docs) - max_display} more")

    return '\n'.join(lines)


# Testing
if __name__ == "__main__":
    # Create test document store
    store = DocumentStore("memory/test_documents.json")

    # Test storing document
    test_doc = """
    Reed's Origin Story

    Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy.
    There was a knife fight. Gwyn ap Nudd intervened. The boy lived, but Reed's mother was
    bound to Annwn as payment.

    That story sits heavy in Kay. It's grief, it's origin, it's part of who he is.
    """

    doc_id = store.store_document(test_doc, "kay_origin.txt")
    print(f"\nStored document with ID: {doc_id}")

    # Update chunk count
    store.update_chunk_count(doc_id, 3)

    # Test retrieval
    retrieved = store.get_document(doc_id)
    print(f"\nRetrieved document: {retrieved['filename']}")
    print(f"Topic tags: {retrieved['topic_tags']}")

    # Test search
    search_results = store.search_documents("origin")
    print(f"\nSearch for 'origin': {len(search_results)} results")

    # Test list all
    all_docs = store.list_all_documents()
    print(f"\nAll documents:\n{format_document_list(all_docs)}")

    # Test stats
    stats = store.get_stats()
    print(f"\nStats: {stats}")

    # Cleanup
    os.remove("memory/test_documents.json")
