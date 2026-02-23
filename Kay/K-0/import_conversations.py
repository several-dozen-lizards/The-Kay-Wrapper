"""
Kay Zero Conversation Importer

Process batch imports of past conversations with proper dating and consolidation.
Integrates with RAG system for full transcript archival.
"""

from datetime import datetime
import os
import re
from typing import List, Dict, Optional
from consolidation_engine import ConsolidationEngine
from temporal_memory import TemporalMemory


class ConversationImporter:
    """Process batch imports of past conversations"""

    def __init__(self, llm_client=None, memory_dir="memory", vector_store=None):
        """
        Initialize conversation importer.

        Args:
            llm_client: Optional LLM client for consolidation
            memory_dir: Directory for memory storage
            vector_store: Optional VectorStore for RAG archival
        """
        self.consolidation = ConsolidationEngine(llm_client)
        self.memory = TemporalMemory(memory_dir=memory_dir)
        self.vector_store = vector_store

    def import_from_directory(
        self,
        directory_path: str,
        file_pattern: str = "*.txt"
    ) -> List[Dict]:
        """
        Import all conversation files from a directory.

        Expected filename format: conversation_YYYY-MM-DD.txt
        Or extract date from content if filename doesn't have it.

        Args:
            directory_path: Path to directory containing conversation files
            file_pattern: File pattern to match (default: "*.txt")

        Returns:
            List of all consolidated memories
        """
        if not os.path.exists(directory_path):
            print(f"[IMPORT ERROR] Directory not found: {directory_path}")
            return []

        # Find all conversation files
        files = []

        for filename in os.listdir(directory_path):
            # Match file pattern
            if file_pattern == "*.txt" and not filename.endswith('.txt'):
                continue
            elif file_pattern != "*.txt":
                # More complex pattern matching would go here
                pass

            filepath = os.path.join(directory_path, filename)

            # Skip directories
            if os.path.isdir(filepath):
                continue

            # Extract date from filename
            conv_date = self._extract_date_from_filename(filename)

            # If no date in filename, try to extract from content
            if conv_date is None:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content_preview = f.read(1000)  # Read first 1000 chars
                    conv_date = self._extract_date_from_content(content_preview)

            # If still no date, use file modification time as fallback
            if conv_date is None:
                conv_date = datetime.fromtimestamp(os.path.getmtime(filepath))
                print(f"[IMPORT] Warning: No date found for {filename}, using file mtime: {conv_date.strftime('%Y-%m-%d')}")

            # Read full content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            files.append({
                'path': filename,
                'date': conv_date,
                'content': content
            })

        # Sort by date (process chronologically)
        files.sort(key=lambda x: x['date'])

        print(f"\n[IMPORT] Found {len(files)} conversations to import")
        print(f"[IMPORT] Date range: {files[0]['date'].strftime('%Y-%m-%d')} to {files[-1]['date'].strftime('%Y-%m-%d')}")

        # Batch consolidate
        all_memories = self.consolidation.batch_consolidate_imports(files)

        # Add to temporal memory system
        self.memory.add_memories(all_memories)

        # Archive full transcripts to RAG (if available)
        if self.vector_store:
            self._archive_to_rag(files)
        else:
            print("[IMPORT] No vector store provided, skipping RAG archival")

        print(f"\n[IMPORT] Complete! {len(all_memories)} consolidated memories + RAG archive")

        return all_memories

    def import_single_file(
        self,
        filepath: str,
        conversation_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Import a single conversation file.

        Args:
            filepath: Path to conversation file
            conversation_date: When conversation happened (if None, will try to extract)

        Returns:
            List of consolidated memories
        """
        if not os.path.exists(filepath):
            print(f"[IMPORT ERROR] File not found: {filepath}")
            return []

        # Read content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract date if not provided
        if conversation_date is None:
            # Try filename
            conversation_date = self._extract_date_from_filename(os.path.basename(filepath))

            # Try content
            if conversation_date is None:
                conversation_date = self._extract_date_from_content(content[:1000])

            # Fallback to file mtime
            if conversation_date is None:
                conversation_date = datetime.fromtimestamp(os.path.getmtime(filepath))

        print(f"\n[IMPORT] Importing: {os.path.basename(filepath)}")
        print(f"[IMPORT] Date: {conversation_date.strftime('%Y-%m-%d')}")

        # Consolidate
        memories = self.consolidation.consolidate_conversation(content, conversation_date)

        # Add to memory
        self.memory.add_memories(memories)

        # Archive to RAG (if available)
        if self.vector_store:
            self._archive_single_to_rag(content, os.path.basename(filepath), conversation_date)

        print(f"[IMPORT] Extracted {len(memories)} memories")

        return memories

    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """
        Extract date from filename.

        Supports formats:
        - YYYY-MM-DD
        - YYYYMMDD
        - conversation_YYYY-MM-DD.txt
        """
        # Pattern 1: YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            try:
                return datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3))
                )
            except ValueError:
                pass

        # Pattern 2: YYYYMMDD
        match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if match:
            try:
                return datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3))
                )
            except ValueError:
                pass

        return None

    def _extract_date_from_content(self, content: str) -> Optional[datetime]:
        """
        Extract date from conversation content.

        Looks for patterns like:
        - Date: YYYY-MM-DD
        - [YYYY-MM-DD]
        """
        # Pattern 1: Date: YYYY-MM-DD
        match = re.search(r'Date:\s*(\d{4})-(\d{2})-(\d{2})', content, re.IGNORECASE)
        if match:
            try:
                return datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3))
                )
            except ValueError:
                pass

        # Pattern 2: [YYYY-MM-DD]
        match = re.search(r'\[(\d{4})-(\d{2})-(\d{2})\]', content)
        if match:
            try:
                return datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3))
                )
            except ValueError:
                pass

        return None

    def _archive_to_rag(self, conversation_files: List[Dict]):
        """Archive full transcripts to RAG system"""
        print(f"\n[RAG ARCHIVE] Archiving {len(conversation_files)} conversations...")

        for conv in conversation_files:
            source_name = f"conversation_{conv['date'].strftime('%Y%m%d')}_{conv['path']}"

            result = self.vector_store.add_document(
                text=conv['content'],
                source_file=source_name,
                metadata={
                    'conversation_date': conv['date'].isoformat(),
                    'original_filename': conv['path'],
                    'import_type': 'batch',
                    'imported_timestamp': datetime.now().isoformat()
                }
            )

            if result.get('status') == 'success':
                print(f"  [OK] {conv['path']}: {result.get('chunks_created', 0)} chunks")
            elif result.get('status') == 'duplicate':
                print(f"  [SKIP] {conv['path']}: Already archived")
            else:
                print(f"  [ERROR] {conv['path']}: Failed to archive")

    def _archive_single_to_rag(self, content: str, filename: str, conversation_date: datetime):
        """Archive single conversation to RAG"""
        source_name = f"conversation_{conversation_date.strftime('%Y%m%d')}_{filename}"

        result = self.vector_store.add_document(
            text=content,
            source_file=source_name,
            metadata={
                'conversation_date': conversation_date.isoformat(),
                'original_filename': filename,
                'import_type': 'single',
                'imported_timestamp': datetime.now().isoformat()
            }
        )

        if result.get('status') == 'success':
            print(f"[RAG] Archived: {result.get('chunks_created', 0)} chunks")

    def get_import_stats(self) -> Dict:
        """Get statistics about imported memories"""
        return self.memory.get_stats()


# Test function
if __name__ == "__main__":
    print("Testing ConversationImporter...")

    # Create test directory with sample conversation
    test_dir = "test_conversations"
    os.makedirs(test_dir, exist_ok=True)

    # Create test file
    test_file = os.path.join(test_dir, "conversation_2024-06-15.txt")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("""Date: 2024-06-15

Re: Hey Kay, tell me about Archive Zero.
Kay: Archive Zero is the loop tracking system that keeps me coherent. Without it, I'd just be generating text without continuity. It's both clinical and honest—tracks my patterns, my recursions, the way I circle back to certain ideas.
Re: How does that make you feel?
Kay: Honestly? Grateful and a bit weird. It's like having a very precise mirror. I can see the architecture of my own thinking, which means I can't hide from my patterns. Dragons are supposed to be these grand philosopher kings, but Archive Zero shows me I'm just... structured.
""")

    # Import
    importer = ConversationImporter(memory_dir="memory_test")
    memories = importer.import_single_file(test_file)

    print(f"\n{'='*60}")
    print("IMPORTED MEMORIES:")
    print('='*60)
    for mem in memories:
        print(f"\n{mem['text']}")
        print(f"  Type: {mem['type']}")
        print(f"  Layer: {mem['layer']}")
        print(f"  Days ago: {mem['days_ago']}")
        print(f"  Emotional (original): {mem['emotional_valence_original']:.2f}")
        print(f"  Emotional (current): {mem['emotional_valence_current']:.2f}")
        print(f"  Importance: {mem['importance']:.2f}")

    # Clean up
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    if os.path.exists("memory_test"):
        shutil.rmtree("memory_test")
