#!/usr/bin/env python
"""
Document Memory Repair Script

Repairs documents that were imported to documents.json but don't have
corresponding memories in memory_layers.json.

This script:
1. Identifies documents missing memories
2. Generates synthesis using LLM (or uses existing synthesis data)
3. Creates document_content and shared_understanding_moment memories
4. Saves to memory_layers.json

Usage:
    python scripts/repair_document_memories.py
    python scripts/repair_document_memories.py --dry-run
    python scripts/repair_document_memories.py --doc-id doc_1763177826
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import os
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Try to import LLM integration
try:
    from integrations.llm_integration import query_llm_json
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("[WARNING] LLM integration not available - will use basic synthesis")


def load_documents() -> Dict:
    """Load documents.json"""
    docs_path = Path(__file__).parent.parent / "memory" / "documents.json"
    if not docs_path.exists():
        print(f"[ERROR] documents.json not found at {docs_path}")
        return {}

    with open(docs_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_memory_layers() -> Dict:
    """Load memory_layers.json"""
    layers_path = Path(__file__).parent.parent / "memory" / "memory_layers.json"
    if not layers_path.exists():
        print(f"[ERROR] memory_layers.json not found at {layers_path}")
        return {"working": [], "long_term": []}

    with open(layers_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
        # Sanitize the content before parsing
        content = sanitize_text(content)
        return json.loads(content)


def sanitize_text(text):
    """Remove surrogate characters that cause encoding issues"""
    if not isinstance(text, str):
        return text
    # Remove surrogate pairs that cause UTF-8 encoding errors
    import re
    return re.sub(r'[\ud800-\udfff]', '', text)


def sanitize_dict(d):
    """Recursively sanitize all strings in a dict"""
    if isinstance(d, dict):
        return {k: sanitize_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [sanitize_dict(item) for item in d]
    elif isinstance(d, str):
        return sanitize_text(d)
    else:
        return d


def save_memory_layers(layers: Dict):
    """Save memory_layers.json with backup - atomic write to prevent corruption"""
    layers_path = Path(__file__).parent.parent / "memory" / "memory_layers.json"
    backup_path = layers_path.with_suffix('.json.repair_backup')
    temp_path = layers_path.with_suffix('.json.tmp')

    # Create backup
    if layers_path.exists():
        import shutil
        shutil.copy(layers_path, backup_path)
        print(f"[BACKUP] Created backup at {backup_path}")

    # Sanitize to avoid unicode encoding errors
    sanitized_layers = sanitize_dict(layers)

    # Write to temp file first, then rename (atomic operation)
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(sanitized_layers, f, indent=2, ensure_ascii=False)

        # Verify the temp file is valid JSON
        with open(temp_path, 'r', encoding='utf-8') as f:
            json.load(f)  # Will raise if invalid

        # Atomic rename
        import os
        if layers_path.exists():
            os.remove(layers_path)
        os.rename(temp_path, layers_path)
        print(f"[SAVED] memory_layers.json updated")

    except Exception as e:
        print(f"[ERROR] Failed to save: {e}")
        if temp_path.exists():
            os.remove(temp_path)
        raise


def get_existing_doc_ids(layers: Dict) -> set:
    """Get set of doc_ids that already have memories"""
    doc_ids = set()

    for layer_name, memories in layers.items():
        if isinstance(memories, list):
            for mem in memories:
                doc_id = mem.get('doc_id')
                mem_type = mem.get('type', '')
                # Only count if it has proper document memories
                if doc_id and mem_type in ['document_content', 'shared_understanding_moment']:
                    doc_ids.add(doc_id)

    return doc_ids


def generate_synthesis_with_llm(doc: Dict) -> Dict:
    """Generate synthesis for a document using LLM"""
    filename = doc.get('filename', 'unknown')
    full_text = doc.get('full_text', '')

    # Truncate text for LLM context
    text_preview = full_text[:8000] if len(full_text) > 8000 else full_text

    prompt = f"""Analyze this document that Re (the user) shared with Kay (an AI companion).

Document: {filename}

Content:
{text_preview}

{"[Content truncated - document continues...]" if len(full_text) > 8000 else ""}

Respond with a JSON object:
{{
    "reveals_about_re": "What this document reveals about Re - her interests, personality, experiences, values (2-3 sentences)",
    "why_shared": "Why Re might have shared this with Kay - what was she hoping Kay would understand? (1-2 sentences)",
    "what_changed": "What Kay now knows or understands differently after reading this (1-2 sentences)",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "emotional_weight": 0.0-1.0 (how emotionally significant is this document?)
}}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            max_tokens=1000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Strip markdown if present
        if response_text.startswith('```'):
            response_text = response_text.split('\n', 1)[1]
            response_text = response_text.rsplit('\n```', 1)[0]

        synthesis = json.loads(response_text)
        print(f"[LLM] Generated synthesis for {filename}")
        return synthesis

    except Exception as e:
        print(f"[LLM ERROR] Failed to generate synthesis: {e}")
        return None


def generate_basic_synthesis(doc: Dict) -> Dict:
    """Generate basic synthesis without LLM (fallback)"""
    filename = doc.get('filename', 'unknown')
    full_text = doc.get('full_text', '')
    word_count = doc.get('word_count', len(full_text.split()))
    topic_tags = doc.get('topic_tags', [])

    # Use existing synthesis if available
    if doc.get('synthesis'):
        reveals = doc['synthesis']
    else:
        reveals = f"Re shared a document called '{filename}' containing {word_count} words."
        if topic_tags:
            reveals += f" Topics include: {', '.join(topic_tags[:5])}."

    return {
        "reveals_about_re": reveals,
        "why_shared": doc.get('why_shared', f"Re wanted Kay to know about the content in '{filename}'."),
        "what_changed": doc.get('what_changed', f"Kay now has access to the information in '{filename}'."),
        "key_insights": topic_tags[:5] if topic_tags else [f"Document: {filename}"],
        "emotional_weight": doc.get('emotional_weight', 0.5)
    }


def create_document_memories(doc: Dict, doc_id: str, synthesis: Dict) -> Tuple[Dict, Dict]:
    """Create the two document memories"""
    filename = doc.get('filename', 'unknown')
    import_date = doc.get('import_date', datetime.now().isoformat())

    # Parse import timestamp
    try:
        if isinstance(import_date, str):
            import_dt = datetime.fromisoformat(import_date.replace('Z', '+00:00'))
        else:
            import_dt = datetime.fromtimestamp(import_date)
    except:
        import_dt = datetime.now()

    timestamp = import_dt.timestamp()

    # Get entities from topic_tags or synthesis
    entities = doc.get('topic_tags', [])
    if not entities and synthesis.get('key_insights'):
        entities = synthesis['key_insights']

    # MEMORY 1: document_content (semantic)
    document_content = {
        'type': 'document_content',
        'memory_type': 'semantic',
        'fact': synthesis.get('reveals_about_re', f"Re shared '{filename}' with Kay"),
        'document_name': filename,
        'sections_read': doc.get('chunk_count', 1),

        # Context integration fields
        'relates_to': synthesis.get('key_insights', [])[:5],
        'explains': [synthesis.get('why_shared', '')] if synthesis.get('why_shared') else [],
        'connects_to': '',
        'reveals_about_re': synthesis.get('reveals_about_re', ''),

        'key_insights': synthesis.get('key_insights', []),
        'section_connections': [],
        'entities': entities[:20],

        # Provenance
        'doc_id': doc_id,
        'source_document': filename,
        'import_timestamp': timestamp,
        'import_timestamp_iso': import_dt.isoformat(),
        'shared_by': 'Re',

        # Retrieval metadata
        'importance': min(1.0, synthesis.get('emotional_weight', 0.5) + 0.3),
        'emotional_weight': synthesis.get('emotional_weight', 0.5),
        'timestamp': timestamp,
        'access_count': 0,
        'perspective': 'kay',
        'is_imported': True,
        'layer': 'long_term',

        # Layer manager fields
        'added_timestamp': datetime.now().isoformat(),
        'last_accessed': datetime.now().isoformat(),
        'importance_score': 0.0,
        'current_strength': 1.0,
        'current_layer': 'long_term'
    }

    # MEMORY 2: shared_understanding_moment (episodic)
    shared_understanding = {
        'type': 'shared_understanding_moment',
        'memory_type': 'episodic',
        'event': 'relational_understanding',
        'fact': f"Re shared '{filename}' with Kay. {synthesis.get('what_changed', 'Kay gained new understanding.')}",
        'document_name': filename,

        # Relational context
        'shared_by': 'Re',
        'why_shared': synthesis.get('why_shared', ''),
        'what_changed': synthesis.get('what_changed', ''),
        'pre_read_hypothesis': '',
        'conversation_context': '',
        'future_implications': '',

        'emotional_weight': synthesis.get('emotional_weight', 0.5),
        'importance': 0.95,

        # Provenance
        'doc_id': doc_id,
        'timestamp': timestamp,
        'timestamp_iso': import_dt.isoformat(),

        'perspective': 'kay',
        'layer': 'long_term',

        # Layer manager fields
        'added_timestamp': datetime.now().isoformat(),
        'access_count': 0,
        'last_accessed': datetime.now().isoformat(),
        'importance_score': 0.0,
        'current_strength': 1.0,
        'current_layer': 'long_term'
    }

    return document_content, shared_understanding


def repair_documents(dry_run: bool = False, specific_doc_id: str = None, use_llm: bool = True):
    """Main repair function"""
    print("=" * 60)
    print("DOCUMENT MEMORY REPAIR")
    print("=" * 60)

    # Load data
    documents = load_documents()
    layers = load_memory_layers()

    if not documents:
        print("[ERROR] No documents found")
        return

    print(f"\n[INFO] Found {len(documents)} documents in documents.json")

    # Find documents missing memories
    existing_doc_ids = get_existing_doc_ids(layers)
    print(f"[INFO] Found {len(existing_doc_ids)} documents with proper memories")

    missing_docs = []
    for doc_id, doc in documents.items():
        if specific_doc_id and doc_id != specific_doc_id:
            continue
        if doc_id not in existing_doc_ids:
            missing_docs.append((doc_id, doc))

    print(f"[INFO] Found {len(missing_docs)} documents missing memories")

    if not missing_docs:
        print("\n[SUCCESS] All documents have memories - nothing to repair!")
        return

    print("\n" + "-" * 60)
    print("DOCUMENTS TO REPAIR:")
    for doc_id, doc in missing_docs:
        print(f"  - {doc_id}: {doc.get('filename', 'unknown')}")
    print("-" * 60)

    if dry_run:
        print("\n[DRY RUN] Would create memories for the above documents")
        return

    # Repair each document
    memories_created = 0

    for doc_id, doc in missing_docs:
        filename = doc.get('filename', 'unknown')
        print(f"\n[REPAIR] Processing: {filename}")

        # Generate synthesis
        synthesis = None

        # Check if document already has synthesis data
        if doc.get('synthesis') and doc.get('why_shared') and doc.get('what_changed'):
            print(f"  [INFO] Using existing synthesis data")
            synthesis = {
                'reveals_about_re': doc['synthesis'],
                'why_shared': doc['why_shared'],
                'what_changed': doc['what_changed'],
                'key_insights': doc.get('topic_tags', [])[:5],
                'emotional_weight': doc.get('emotional_weight', 0.5)
            }
        elif use_llm and LLM_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            print(f"  [INFO] Generating synthesis with LLM...")
            synthesis = generate_synthesis_with_llm(doc)

        # Fallback to basic synthesis
        if not synthesis:
            print(f"  [INFO] Using basic synthesis (no LLM)")
            synthesis = generate_basic_synthesis(doc)

        # Create memories
        doc_content, shared_moment = create_document_memories(doc, doc_id, synthesis)

        # Add to long_term layer
        if 'long_term' not in layers:
            layers['long_term'] = []

        layers['long_term'].append(doc_content)
        layers['long_term'].append(shared_moment)
        memories_created += 2

        print(f"  [OK] Created 2 memories for {filename}")
        print(f"       - document_content: {synthesis.get('reveals_about_re', '')[:80]}...")
        print(f"       - shared_understanding: why shared, what changed")

    # Save
    print("\n" + "-" * 60)
    save_memory_layers(layers)

    print(f"\n[SUCCESS] Created {memories_created} memories for {len(missing_docs)} documents")


def main():
    parser = argparse.ArgumentParser(description="Repair missing document memories")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without making changes")
    parser.add_argument('--doc-id', type=str, help="Repair only a specific document ID")
    parser.add_argument('--no-llm', action='store_true', help="Don't use LLM for synthesis (use basic fallback)")

    args = parser.parse_args()

    repair_documents(
        dry_run=args.dry_run,
        specific_doc_id=args.doc_id,
        use_llm=not args.no_llm
    )


if __name__ == "__main__":
    main()
