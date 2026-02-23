"""
Migrate Existing Documents to Vector Store

This script retroactively indexes documents that were imported before
the vector store integration was added to active_reader.py.

Run this script once to populate the vector store with existing documents
from documents.json.

Usage:
    python scripts/migrate_documents_to_vector_store.py

The script will:
1. Load all documents from memory/documents.json
2. Check which ones are already in the vector store
3. Add missing documents to the vector store
4. Update documents.json with rag_chunks count
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from engines.vector_store import VectorStore
from memory_import.document_store import DocumentStore


def migrate_documents():
    """Migrate existing documents to vector store."""
    print("=" * 60)
    print("DOCUMENT VECTOR STORE MIGRATION")
    print("=" * 60)
    print()

    # Initialize stores
    print("[1/4] Initializing stores...")
    vector_store = VectorStore(persist_directory="memory/vector_db")
    doc_store = DocumentStore()

    # Get current vector store stats
    vs_stats = vector_store.get_stats()
    print(f"      Vector store: {vs_stats['total_chunks']} chunks, {vs_stats['total_documents']} documents")
    print(f"      Document store: {len(doc_store.documents)} documents")
    print()

    # Get list of documents already in vector store
    print("[2/4] Checking for missing documents...")
    vs_docs = vector_store.list_documents()
    vs_doc_ids = set()
    vs_source_files = set()

    for vs_doc in vs_docs:
        if vs_doc.get('document_id'):
            vs_doc_ids.add(vs_doc['document_id'])
        if vs_doc.get('source_file'):
            # Extract just filename from full path
            source = Path(vs_doc['source_file']).name
            vs_source_files.add(source.lower())

    print(f"      Documents in vector store: {len(vs_doc_ids)} by ID, {len(vs_source_files)} by filename")

    # Find documents that need migration
    to_migrate = []
    already_indexed = 0
    no_content = 0

    for doc_id, doc in doc_store.documents.items():
        filename = doc.get('filename', '')
        full_text = doc.get('full_text', doc.get('content', ''))

        # Check if already indexed
        if doc_id in vs_doc_ids or filename.lower() in vs_source_files:
            already_indexed += 1
            continue

        # Check if has content
        if not full_text or len(full_text) < 50:
            no_content += 1
            print(f"      Skipping {filename}: No content or too short")
            continue

        to_migrate.append({
            'doc_id': doc_id,
            'filename': filename,
            'full_text': full_text,
            'import_date': doc.get('import_date', ''),
        })

    print(f"      Already indexed: {already_indexed}")
    print(f"      No content: {no_content}")
    print(f"      Need migration: {len(to_migrate)}")
    print()

    if not to_migrate:
        print("[3/4] No documents need migration!")
        print()
        print("[4/4] MIGRATION COMPLETE - No changes needed")
        return

    # Migrate documents
    print(f"[3/4] Migrating {len(to_migrate)} documents...")
    total_chunks = 0
    success = 0
    failed = 0

    for i, doc in enumerate(to_migrate, 1):
        doc_id = doc['doc_id']
        filename = doc['filename']
        full_text = doc['full_text']

        print(f"      [{i}/{len(to_migrate)}] {filename}...", end=" ")

        try:
            result = vector_store.add_document(
                text=full_text,
                source_file=filename,
                chunk_size=800,
                overlap=100,
                metadata={
                    "doc_id": doc_id,
                    "import_timestamp": doc.get('import_date', datetime.now().isoformat()),
                    "migrated": True,
                    "migration_date": datetime.now().isoformat()
                }
            )

            chunks = result.get('chunks_created', 0)
            status = result.get('status', 'unknown')

            if status == 'success' and chunks > 0:
                total_chunks += chunks
                success += 1
                print(f"{chunks} chunks")

                # Update DocumentStore with chunk count
                if doc_id in doc_store.documents:
                    doc_store.documents[doc_id]['rag_chunks'] = chunks
            elif status == 'duplicate':
                print("already exists")
                already_indexed += 1
            else:
                print(f"no chunks ({status})")
                failed += 1

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    # Save updated DocumentStore
    doc_store._save_documents()
    print()

    # Final stats
    print("[4/4] MIGRATION COMPLETE")
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Documents migrated: {success}")
    print(f"  Documents failed: {failed}")
    print(f"  Total chunks created: {total_chunks}")
    print()

    # Show updated vector store stats
    new_stats = vector_store.get_stats()
    print(f"  Vector store now has:")
    print(f"    - {new_stats['total_chunks']} total chunks")
    print(f"    - {new_stats['total_documents']} total documents")
    print()
    print("Kay can now use RAG to semantically search document content!")


if __name__ == "__main__":
    migrate_documents()
