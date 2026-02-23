"""
Automatic Document Import with Reading

Combines emotional import (RAG storage) with automatic reading (Kay responses).

Flow:
1. Import document via emotional importer (stores in RAG)
2. Load document into DocumentReader for segmentation
3. Use AutoReader to feed each segment to Kay
4. Reed's responses appear naturally in chat
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Callable, Tuple

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.document_reader import DocumentReader
from engines.auto_reader import AutoReader
from memory_import.emotional_importer import EmotionalMemoryImporter


async def import_and_read_document(
    filepath: str,
    memory_engine,
    add_message_func: Callable,
    llm_response_func: Callable,
    agent_state=None,
    chunk_size: int = 25000
) -> Tuple[str, List[str]]:
    """
    Import document and automatically read through all segments.

    Args:
        filepath: Path to document file
        memory_engine: Memory engine instance
        add_message_func: Function to display messages (role, message)
        llm_response_func: Function to get LLM responses (prompt, agent_state) -> str
        agent_state: Optional agent state for full context
        chunk_size: Size of readable segments (default 25000 chars)

    Returns:
        tuple of (doc_id, list of Reed's responses)
    """

    doc_name = os.path.basename(filepath)

    # Step 1: Import document emotionally (RAG storage)
    print(f"[AUTO IMPORT] Importing {doc_name} to RAG...")
    add_message_func("system", f"Importing {doc_name}...")

    emotional_importer = EmotionalMemoryImporter(memory_engine=memory_engine)

    # Read document
    with open(filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Import to RAG (async)
    try:
        # Call import_document method (adjust based on actual API)
        if hasattr(emotional_importer, 'import_document_async'):
            doc_id = await emotional_importer.import_document_async(
                document_text=full_text,
                filename=doc_name
            )
        else:
            # Fallback to sync in thread
            doc_id = await asyncio.to_thread(
                emotional_importer.import_document,
                full_text,
                doc_name
            )

        print(f"[AUTO IMPORT] Document stored in RAG as {doc_id}")

    except Exception as e:
        print(f"[AUTO IMPORT] Error importing to RAG: {e}")
        add_message_func("system", f"Error importing document: {e}")
        raise

    # Step 2: Load into DocumentReader for segments
    print(f"[AUTO IMPORT] Creating readable segments...")
    doc_reader = DocumentReader(chunk_size=chunk_size)
    num_chunks = doc_reader.load_document(full_text, doc_name, doc_id)

    print(f"[AUTO IMPORT] Created {num_chunks} segments")
    add_message_func("system", f"Reading {doc_name} ({num_chunks} sections)...")

    # Step 3: Automatically read through all segments
    auto_reader = AutoReader(
        get_llm_response_func=llm_response_func,
        add_message_func=add_message_func,
        memory_engine=memory_engine
    )

    responses = await auto_reader.read_document_async(
        doc_reader=doc_reader,
        doc_name=doc_name,
        agent_state=agent_state
    )

    print(f"[AUTO IMPORT] Complete: {doc_name}")

    return doc_id, responses


def import_and_read_document_sync(
    filepath: str,
    memory_engine,
    add_message_func: Callable,
    llm_response_func: Callable,
    agent_state=None,
    chunk_size: int = 25000
) -> Tuple[str, List[str]]:
    """
    Synchronous version for main.py terminal use.

    Args:
        filepath: Path to document file
        memory_engine: Memory engine instance
        add_message_func: Function to display messages (role, message)
        llm_response_func: Function to get LLM responses (prompt, agent_state) -> str
        agent_state: Optional agent state for full context
        chunk_size: Size of readable segments (default 25000 chars)

    Returns:
        tuple of (doc_id, list of Reed's responses)
    """
    doc_name = os.path.basename(filepath)

    # Step 1: Import to RAG
    print(f"[AUTO IMPORT] Importing {doc_name} to RAG...")
    add_message_func("system", f"Importing {doc_name}...")

    emotional_importer = EmotionalMemoryImporter(memory_engine=memory_engine)

    with open(filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Import to RAG (sync)
    try:
        doc_id = emotional_importer.import_document(
            document_text=full_text,
            filename=doc_name
        )
        print(f"[AUTO IMPORT] Document stored in RAG as {doc_id}")

    except Exception as e:
        print(f"[AUTO IMPORT] Error importing to RAG: {e}")
        add_message_func("system", f"Error importing document: {e}")
        raise

    # Step 2: Create segments
    print(f"[AUTO IMPORT] Creating readable segments...")
    doc_reader = DocumentReader(chunk_size=chunk_size)
    num_chunks = doc_reader.load_document(full_text, doc_name, doc_id)

    print(f"[AUTO IMPORT] Created {num_chunks} segments")
    add_message_func("system", f"Reading {doc_name} ({num_chunks} sections)...")

    # Step 3: Read through segments
    auto_reader = AutoReader(
        get_llm_response_func=llm_response_func,
        add_message_func=add_message_func,
        memory_engine=memory_engine
    )

    responses = auto_reader.read_document_sync(
        doc_reader=doc_reader,
        doc_name=doc_name,
        agent_state=agent_state
    )

    print(f"[AUTO IMPORT] Complete: {doc_name}")

    return doc_id, responses


# Example usage
if __name__ == "__main__":
    # Test import
    test_file = "test_documents/YW_test_section.txt"

    def mock_add_message(role, message):
        print(f"[{role.upper()}] {message}")

    def mock_llm_response(prompt, state):
        return "[Mock response - replace with actual LLM call]"

    if os.path.exists(test_file):
        print("Testing auto-import...")
        doc_id, responses = import_and_read_document_sync(
            filepath=test_file,
            memory_engine=None,  # Replace with actual memory engine
            add_message_func=mock_add_message,
            llm_response_func=mock_llm_response,
            agent_state=None
        )

        print(f"\nImport complete: {doc_id}")
        print(f"Generated {len(responses)} responses")
    else:
        print(f"Test file not found: {test_file}")
