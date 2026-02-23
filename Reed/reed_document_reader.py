"""
Document Reading Tools for Reed

Provides document reading functionality using documents.json as source:
- List available imported documents
- Read full document content  
- Search within specific documents
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class DocumentReader:
    """Handles reading documents from documents.json storage"""
    
    def __init__(self, chroma_client: Any = None, collection_name: str = "reed_documents"):
        # chroma_client is accepted for API compatibility but not used
        # Documents are read from documents.json instead
        # Use absolute path based on this file's location
        project_root = Path(__file__).parent.parent if Path(__file__).parent.name == "memory_import" else Path(__file__).parent
        self.documents_path = project_root / "memory" / "documents.json"
        self._documents_cache = None
    
    def _load_documents(self) -> Dict[str, Dict]:
        """Load documents from documents.json"""
        if not self.documents_path.exists():
            print(f"[DOCUMENT READER] documents.json not found at {self.documents_path}")
            return {}
        
        try:
            with open(self.documents_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                docs = json.loads(content)
                
                # Handle both list and dict formats
                if isinstance(docs, list):
                    docs_dict = {}
                    for i, doc in enumerate(docs):
                        if isinstance(doc, dict):
                            doc_id = doc.get('doc_id') or doc.get('memory_id') or doc.get('filename', f'doc_{i}')
                            docs_dict[doc_id] = doc
                    return docs_dict
                elif isinstance(docs, dict):
                    return docs
                else:
                    return {}
                    
        except Exception as e:
            print(f"[DOCUMENT READER] Error loading documents.json: {e}")
            return {}
    
    def list_available_documents(self) -> Dict[str, Any]:
        """
        List all documents from documents.json
        
        Returns:
            Dict with 'documents' list containing metadata for each document
        """
        docs = self._load_documents()
        
        if not docs:
            return {
                "documents": [],
                "total_count": 0,
                "message": "No documents found in documents.json"
            }
        
        doc_list = []
        for doc_id, doc_data in docs.items():
            if not isinstance(doc_data, dict):
                continue
                
            full_text = doc_data.get('full_text', '')
            word_count = len(full_text.split()) if full_text else 0
            
            doc_list.append({
                'name': doc_data.get('filename', doc_id),
                'doc_id': doc_id,
                'word_count': word_count,
                'import_date': doc_data.get('import_date', 'unknown'),
                'preview': full_text[:200] if full_text else ''
            })
        
        return {
            "documents": doc_list,
            "total_count": len(doc_list)
        }
    
    def read_document(self, document_name: str, max_chars: Optional[int] = None) -> Dict[str, Any]:
        """
        Read full content of a specific document
        
        Args:
            document_name: Name of the document to read (filename)
            max_chars: Optional limit on characters to return
            
        Returns:
            Dict with 'content' (full text), 'metadata', 'word_count'
        """
        docs = self._load_documents()
        
        if not docs:
            return {
                "content": "",
                "error": "No documents found in documents.json"
            }
        
        # Find document by filename
        target_doc = None
        target_doc_id = None
        
        for doc_id, doc_data in docs.items():
            if isinstance(doc_data, dict):
                if doc_data.get('filename', '') == document_name or doc_id == document_name:
                    target_doc = doc_data
                    target_doc_id = doc_id
                    break
        
        if not target_doc:
            # Return helpful error with available documents
            available = [d.get('filename', id) for id, d in docs.items() if isinstance(d, dict)]
            return {
                "content": "",
                "error": f"Document '{document_name}' not found. Available: {', '.join(available[:10])}"
            }
        
        full_text = target_doc.get('full_text', '')
        
        if max_chars and len(full_text) > max_chars:
            full_text = full_text[:max_chars] + f"\n\n[Content truncated at {max_chars} chars]"
        
        # Track exploration if in curiosity mode
        try:
            from engines.curiosity_engine import get_curiosity_status, track_explored_item
            status = get_curiosity_status()
            if status.get('active'):
                track_explored_item('document', target_doc.get('filename', document_name))
        except Exception as e:
            pass  # Silently fail if curiosity engine not available
        
        return {
            "content": full_text,
            "metadata": {
                'doc_id': target_doc_id,
                'filename': target_doc.get('filename', document_name),
                'import_date': target_doc.get('import_date', 'unknown')
            },
            "word_count": len(full_text.split())
        }
    
    def search_within_document(self, document_name: str, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Simple text search within a specific document
        
        Args:
            document_name: Name of document to search within
            query: Search query
            n_results: Number of results to return (not used for simple search)
            
        Returns:
            Dict with 'results' list containing matching excerpts
        """
        docs = self._load_documents()
        
        if not docs:
            return {
                "results": [],
                "error": "No documents found in documents.json"
            }
        
        # Find document by filename
        target_doc = None
        for doc_id, doc_data in docs.items():
            if isinstance(doc_data, dict):
                if doc_data.get('filename', '') == document_name or doc_id == document_name:
                    target_doc = doc_data
                    break
        
        if not target_doc:
            return {
                "results": [],
                "error": f"Document '{document_name}' not found"
            }
        
        full_text = target_doc.get('full_text', '')
        query_lower = query.lower()
        
        # Find all occurrences
        results = []
        lines = full_text.split('\n')
        
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # Get context (line before and after)
                start_idx = max(0, i - 1)
                end_idx = min(len(lines), i + 2)
                context = '\n'.join(lines[start_idx:end_idx])
                
                results.append({
                    'line_number': i + 1,
                    'excerpt': context,
                    'match': line
                })
                
                if len(results) >= n_results:
                    break
        
        # Track exploration if in curiosity mode
        if results:
            try:
                from engines.curiosity_engine import get_curiosity_status, track_explored_item
                status = get_curiosity_status()
                if status.get('active'):
                    track_explored_item('search', f"{document_name}:{query}")
            except Exception as e:
                pass  # Silently fail if curiosity engine not available
        
        return {
            "results": results,
            "total_matches": len(results),
            "query": query
        }


def get_reed_document_tools(chroma_client: Any = None) -> Dict[str, callable]:
    """
    Get document reading tools for Reed's tool system
    
    Args:
        chroma_client: ChromaDB client instance (optional, not used)
        
    Returns:
        Dict of tool name -> callable function
    """
    reader = DocumentReader(chroma_client)
    
    return {
        'list_documents': reader.list_available_documents,
        'read_document': reader.read_document,
        'search_document': reader.search_within_document
    }
