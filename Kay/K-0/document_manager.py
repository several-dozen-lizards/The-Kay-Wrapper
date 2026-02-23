"""
Document management system for viewing and managing imported documents.
"""

import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path


@dataclass
class DocumentInfo:
    """Information about an imported document."""
    doc_id: str
    filename: str
    filepath: str
    content: str
    content_preview: str
    import_date: str
    chunk_count: int
    memory_count: int
    entity_count: int
    file_size: int
    file_type: str
    memory_ids: List[str]
    entity_names: List[str]
    import_status: str
    error_log: str = ""


class DocumentManager:
    """Manages document storage, retrieval, and deletion."""

    def __init__(self, memory_engine, entity_graph):
        self.memory_engine = memory_engine
        self.entity_graph = entity_graph
        # Use absolute path relative to this file's location
        project_root = Path(__file__).parent
        self.doc_store_path = str(project_root / "memory" / "documents.json")
        self.documents_cache = None

    def load_all_documents(self) -> List[DocumentInfo]:
        """
        Load all documents with computed stats.

        Returns:
            List of DocumentInfo objects with memory and entity counts
        """
        documents = []

        try:
            if not os.path.exists(self.doc_store_path):
                print(f"[DOC MANAGER] No documents file found at {self.doc_store_path}")
                return []

            with open(self.doc_store_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

                # Handle empty file
                if not content:
                    print(f"[DOC MANAGER] Warning: {self.doc_store_path} is empty")
                    return []

                doc_data = json.loads(content)

            # Handle both list and dict formats
            if isinstance(doc_data, list):
                print(f"[DOC MANAGER] Converting list format to dict ({len(doc_data)} documents)")
                # Convert list to dict using doc_id, memory_id, or filename as key
                docs_dict = {}
                for i, doc in enumerate(doc_data):
                    if not isinstance(doc, dict):
                        continue

                    # Priority: doc_id > memory_id > filename > generated key
                    doc_id = (doc.get('doc_id') or
                             doc.get('memory_id') or
                             doc.get('filename', f'doc_{i}'))
                    docs_dict[doc_id] = doc

                doc_data = docs_dict

            elif not isinstance(doc_data, dict):
                print(f"[DOC MANAGER] Error: Unexpected format (type: {type(doc_data)})")
                return []

            print(f"[DOC MANAGER] Loaded {len(doc_data)} documents from storage")

            for doc_id, doc in doc_data.items():
                filename = doc.get('filename', 'Unknown')

                # Get memories associated with this document (try both doc_id and filename)
                memories = self.get_document_memories(doc_id, filename)
                memory_ids = [m.get('id', '') for m in memories if m.get('id')]

                # Get entities mentioned in document
                entity_names = self.get_document_entities(doc_id)

                # Get content (or preview if too large)
                # Note: DocumentStore uses 'full_text', older formats may use 'content'
                content = doc.get('full_text', doc.get('content', ''))
                content_preview = self._get_preview(content, 5000)

                # Determine import status
                status = doc.get('import_status', 'complete')
                if doc.get('import_error'):
                    status = 'failed'
                elif len(memories) < doc.get('expected_chunks', 1):
                    status = 'partial'

                doc_info = DocumentInfo(
                    doc_id=doc_id,
                    filename=doc.get('filename', 'Unknown'),
                    filepath=doc.get('filepath', ''),
                    content=content,
                    content_preview=content_preview,
                    import_date=doc.get('import_date', ''),
                    chunk_count=doc.get('chunk_count', 0),
                    memory_count=len(memories),
                    entity_count=len(entity_names),
                    file_size=len(content),
                    file_type=os.path.splitext(doc.get('filename', ''))[1],
                    memory_ids=memory_ids,
                    entity_names=entity_names,
                    import_status=status,
                    error_log=doc.get('import_error', '')
                )

                documents.append(doc_info)

            # Sort by import date (newest first)
            documents.sort(key=lambda d: d.import_date, reverse=True)

        except Exception as e:
            print(f"[DOC MANAGER] Error loading documents: {e}")
            import traceback
            traceback.print_exc()

        self.documents_cache = documents
        return documents

    def get_document_memories(self, doc_id: str, filename: str = None) -> List[dict]:
        """
        Get all memories associated with a document.

        Uses multiple matching strategies:
        - Exact doc_id match
        - source_file match
        - _cluster_source match (used in imports)
        - source match
        - Filename substring match
        """
        memories = []
        seen_ids = set()  # Deduplicate

        try:
            # Search through all memory tiers
            all_memories = []

            if hasattr(self.memory_engine, 'memory_layers'):
                # TWO-TIER architecture: working + long_term only
                all_memories.extend(self.memory_engine.memory_layers.working_memory)
                all_memories.extend(self.memory_engine.memory_layers.long_term_memory)
            else:
                # Fallback to old memory structure
                all_memories = getattr(self.memory_engine, 'memories', [])

            # Try multiple matching strategies
            for memory in all_memories:
                if not isinstance(memory, dict):
                    continue

                memory_id = memory.get('id', id(memory))
                if memory_id in seen_ids:
                    continue

                # Strategy 1: Exact doc_id match
                if memory.get('doc_id') == doc_id:
                    memories.append(memory)
                    seen_ids.add(memory_id)
                    continue

                # Strategy 2: source_file match
                if memory.get('source_file') == doc_id:
                    memories.append(memory)
                    seen_ids.add(memory_id)
                    continue

                # Strategy 3: _cluster_source match (used in imports)
                if memory.get('_cluster_source') == doc_id:
                    memories.append(memory)
                    seen_ids.add(memory_id)
                    continue

                # Strategy 4: source match
                if memory.get('source') == doc_id:
                    memories.append(memory)
                    seen_ids.add(memory_id)
                    continue

                # Strategy 5: Filename substring match (if filename provided)
                if filename:
                    for field in ['doc_id', 'source_file', '_cluster_source', 'source']:
                        field_value = memory.get(field, '')
                        if isinstance(field_value, str) and filename in field_value:
                            memories.append(memory)
                            seen_ids.add(memory_id)
                            break

            print(f"[DOC MANAGER] Found {len(memories)} memories for doc_id='{doc_id}', filename='{filename}'")

        except Exception as e:
            print(f"[DOC MANAGER] Error getting memories for {doc_id}: {e}")
            import traceback
            traceback.print_exc()

        return memories

    def get_document_entities(self, doc_id: str) -> List[str]:
        """Get all entities mentioned in document."""
        entity_names = set()

        try:
            # Get entities from entity graph that reference this document
            if hasattr(self.entity_graph, 'entities'):
                for entity_name, entity_data in self.entity_graph.entities.items():
                    # Check if entity has any attributes that came from this document
                    for attr_name, values in entity_data.items():
                        if isinstance(values, list):
                            for value_data in values:
                                if isinstance(value_data, dict):
                                    if value_data.get('doc_id') == doc_id:
                                        entity_names.add(entity_name)
                                        break
        except Exception as e:
            print(f"[DOC MANAGER] Error getting entities for {doc_id}: {e}")

        return sorted(list(entity_names))

    def delete_document(self, doc_id: str, delete_memories: bool = True) -> Tuple[bool, str]:
        """
        Delete document and optionally its memories.

        Args:
            doc_id: Document to delete
            delete_memories: If True, remove associated memories and entity links

        Returns:
            Tuple of (success, message)
        """
        try:
            # Load documents
            if not os.path.exists(self.doc_store_path):
                return False, "Documents file not found"

            with open(self.doc_store_path, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)

            if doc_id not in doc_data:
                return False, f"Document {doc_id} not found"

            filename = doc_data[doc_id].get('filename', doc_id)

            # Remove from documents.json
            del doc_data[doc_id]

            # Save updated documents
            with open(self.doc_store_path, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2)

            if delete_memories:
                # Remove memories
                memories_removed = self._delete_document_memories(doc_id)

                # Clean entity graph references
                entities_cleaned = self._clean_entity_references(doc_id)

                return True, f"Deleted {filename}\nRemoved {memories_removed} memories\nCleaned {entities_cleaned} entity references"
            else:
                return True, f"Deleted {filename} (kept memories)"

        except Exception as e:
            print(f"[DOC MANAGER] Error deleting document: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error: {str(e)}"

    def _delete_document_memories(self, doc_id: str) -> int:
        """Remove all memories associated with document."""
        count = 0

        try:
            if hasattr(self.memory_engine, 'memory_layers'):
                # Remove from each tier
                layers = self.memory_engine.memory_layers

                # Count and remove from working memory
                working_before = len(layers.working_memory)
                layers.working_memory = [
                    m for m in layers.working_memory
                    if m.get('doc_id') != doc_id and m.get('source_file') != doc_id
                ]
                count += working_before - len(layers.working_memory)

                # Count and remove from episodic memory
                episodic_before = len(layers.episodic_memory)
                layers.episodic_memory = [
                    m for m in layers.episodic_memory
                    if m.get('doc_id') != doc_id and m.get('source_file') != doc_id
                ]
                count += episodic_before - len(layers.episodic_memory)

                # Count and remove from semantic memory
                semantic_before = len(layers.semantic_memory)
                layers.semantic_memory = [
                    m for m in layers.semantic_memory
                    if m.get('doc_id') != doc_id and m.get('source_file') != doc_id
                ]
                count += semantic_before - len(layers.semantic_memory)

                # Save updated memory layers
                layers.save_memories()

        except Exception as e:
            print(f"[DOC MANAGER] Error deleting memories: {e}")

        return count

    def _clean_entity_references(self, doc_id: str) -> int:
        """Remove entity attribute values that came from this document."""
        count = 0

        try:
            if hasattr(self.entity_graph, 'entities'):
                for entity_name, entity_data in self.entity_graph.entities.items():
                    for attr_name, values in list(entity_data.items()):
                        if isinstance(values, list):
                            original_len = len(values)
                            entity_data[attr_name] = [
                                v for v in values
                                if not (isinstance(v, dict) and v.get('doc_id') == doc_id)
                            ]
                            count += original_len - len(entity_data[attr_name])

                # Save updated entity graph
                self.entity_graph.save_entities()

        except Exception as e:
            print(f"[DOC MANAGER] Error cleaning entities: {e}")

        return count

    def _get_preview(self, content: str, max_chars: int = 5000) -> str:
        """Get truncated preview of content."""
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + f"\n\n... ({len(content) - max_chars} more characters)"

    def search_documents(self, query: str, documents: List[DocumentInfo]) -> List[DocumentInfo]:
        """Filter documents by query string."""
        if not query:
            return documents

        query_lower = query.lower()
        return [
            doc for doc in documents
            if query_lower in doc.filename.lower()
            or query_lower in doc.content_preview.lower()
        ]
