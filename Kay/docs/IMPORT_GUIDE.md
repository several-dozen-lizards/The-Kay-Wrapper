# Memory Import System for Kay Zero

## Overview

The memory import system allows you to bulk-import archived documents (text files, PDFs, conversations, etc.) into Kay's persistent memory.

**✅ FIXED (2024-10-27):** Import pipeline now correctly stores memories for retrieval. Kay can recall imported facts instead of hallucinating. See `IMPORT_FIX_SUMMARY.md` for technical details.

## Quick Start

### 1. Prepare Your Documents

Create a directory with your documents:
```
archives/
  ├── conversation_2024-01-15.txt
  ├── journal_entry_2024-02-20.txt
  └── notes.pdf
```

### 2. Run Import

#### Dry Run (Preview)
Test without saving to database:
```bash
python import_memories.py --input archives/ --dry-run
```

#### Full Import
Import and save to Kay's memory:
```bash
python import_memories.py --input archives/
```

### 3. View Progress

The import displays real-time progress:
```
[PARSE] PARSING: Files 3/10 | Chunks 45/120 | Facts 23 | Memories 18
[EXTRACT] EXTRACTING: Files 5/10 | Chunks 67/120 | Facts 45 | Memories 38
[SAVE] INTEGRATING: Files 8/10 | Chunks 98/120 | Facts 72 | Memories 65
[DONE] COMPLETE: Files 10/10 | Chunks 120/120 | Facts 89 | Memories 78
```

### 4. View Summary

After completion:
```
======================================================================
IMPORT COMPLETE
======================================================================

Files processed: 10
Chunks processed: 120
Facts extracted: 89
Memories imported: 78

Memory Tier Distribution:
  - Semantic: 65
  - Episodic: 13
  - Working: 0

Entities:
  - Created: 12
  - Updated: 23

Time elapsed: 45.3 seconds
```

## Usage Examples

### Import Single File
```bash
python import_memories.py --input conversation.txt
```

### Import Multiple Files
```bash
python import_memories.py --input file1.txt file2.txt file3.pdf
```

### Import Directory
```bash
python import_memories.py --input ./archives/
```

### Dry Run (Preview Mode)
```bash
python import_memories.py --input ./archives/ --dry-run
```

### Date Filtering
Import only documents within date range:
```bash
python import_memories.py --input ./archives/ --start-date 2024-01-01 --end-date 2024-10-27
```

### Custom Chunk Size
Adjust document chunking (larger = fewer API calls but less granular):
```bash
python import_memories.py --input ./large_docs/ --chunk-size 5000
```

### Batch Processing
Control LLM rate limiting (smaller = slower but more reliable):
```bash
python import_memories.py --input ./archives/ --batch-size 3
```

## Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input` / `-i` | Input file(s) or directory | Required |
| `--dry-run` | Preview without saving | False |
| `--start-date` | Filter by start date (YYYY-MM-DD) | None |
| `--end-date` | Filter by end date (YYYY-MM-DD) | None |
| `--chunk-size` | Document chunk size in characters | 3000 |
| `--batch-size` | LLM batch size for rate limiting | 5 |

## How It Works

### 1. Document Parsing
- Reads files (TXT, PDF, DOCX, etc.)
- Splits into manageable chunks (default: 3000 chars)
- Maintains context overlap between chunks (500 chars)

### 2. Fact Extraction
- Uses Claude to extract discrete facts from each chunk
- Identifies entities (people, places, things)
- Determines perspective (user, kay, shared)
- Assigns importance scores
- Tags with emotions and topics

### 3. Memory Integration
- Stores facts in appropriate memory tier:
  - **Semantic**: Long-term factual knowledge
  - **Episodic**: Time-bound events and experiences
  - **Working**: Recent context (rarely used in imports)
- Updates entity graph with relationships
- Links entities across memories

### 4. Index Updates
- Automatically updates memory indexes
- Maintains lazy loading compatibility
- No manual rebuild needed

## Supported File Types

- **Text**: `.txt`, `.md`
- **PDF**: `.pdf` (requires `pdfplumber`)
- **Word**: `.docx` (requires `python-docx`)
- **JSON**: `.json` (structured conversation exports)

## Performance

### Throughput
- ~5-10 chunks/minute (depends on API rate limits)
- ~100-200 facts/minute extracted
- ~80-150 memories/minute saved

### Typical Import Times
- 10 documents (~50 pages): ~5-10 minutes
- 100 documents (~500 pages): ~30-60 minutes
- 1000 documents (~5000 pages): ~5-10 hours

## Troubleshooting

### Issue: "No valid input paths provided"
**Solution**: Check that file/directory exists and path is correct
```bash
# Check path
ls archives/

# Use absolute path if needed
python import_memories.py --input /full/path/to/archives/
```

### Issue: "API credit balance too low"
**Solution**: Add credits to your Anthropic account at https://console.anthropic.com/settings/billing

### Issue: Import hangs or is very slow
**Solution**: Reduce batch size to avoid rate limits
```bash
python import_memories.py --input archives/ --batch-size 1
```

### Issue: Import crashes mid-way
**Solution**: The import resumes from where it left off. Re-run the same command.
```bash
# Import is idempotent - safe to re-run
python import_memories.py --input archives/
```

### Issue: Duplicate memories after re-import
**Solution**: Use dry-run first to preview, then clean up manually if needed
```bash
# Preview first
python import_memories.py --input file.txt --dry-run

# Check existing memories
# Then import if not already present
```

### Issue: No progress display
**Solution**: Progress updates every chunk. For small files, it may complete instantly.

### Issue: Low fact extraction rate
**Solution**:
- Increase chunk size for more context: `--chunk-size 5000`
- Check that documents contain extractable facts (not just formatting)
- Use dry-run to see what's being extracted

## After Import

### Verify Import
Check memory counts:
```bash
python -c "
import json
memories = json.load(open('memory/memories.json'))
print(f'Total memories: {len(memories)}')
print(f'Last 5:')
for m in memories[-5:]:
    print(f'  - {m.get(\"fact\", m.get(\"user_input\", \"\"))[:60]}...')
"
```

### Rebuild Indexes (for lazy loading)
After large imports, rebuild indexes:
```bash
python build_memory_indexes.py
```

### Test Retrieval
Start Kay and test memory recall:
```bash
python main.py
# Ask Kay about imported content
```

## File Format Tips

### Best Format: Plain Text Conversations
```
User: What are my cats' names?
Kay: Your cats are [cat] and [dog].
User: Tell me about [cat].
Kay: [cat] is a gray tabby with green eyes...
```

### Good Format: Structured JSON
```json
[
  {
    "speaker": "user",
    "text": "What are my cats' names?",
    "timestamp": "2024-10-27T10:30:00"
  },
  {
    "speaker": "assistant",
    "text": "Your cats are [cat] and [dog].",
    "timestamp": "2024-10-27T10:30:05"
  }
]
```

### Okay Format: Narrative Text
```
Journal Entry - October 27, 2024

Today I took [cat] and [dog] to the vet. [cat] was nervous but [dog]
was very brave. The vet said they're both healthy...
```

### Avoid: Heavily Formatted Documents
- Tables, spreadsheets, forms
- Code dumps
- Binary data, images (unless OCR'd first)

## API Cost Estimation

### Pricing (approximate)
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens
- Average document: ~1000 tokens
- Average fact extraction: ~500 output tokens

### Cost Examples
- 10 documents: ~$0.01-0.05
- 100 documents: ~$0.10-0.50
- 1000 documents: ~$1-5
- 10,000 documents: ~$10-50

**Tip**: Use `--dry-run` first to preview token usage before committing to large imports.

## Best Practices

1. **Start small**: Test with 1-2 files first using `--dry-run`
2. **Check quality**: Review extracted facts to ensure quality
3. **Batch imports**: Import in batches of 100-500 documents
4. **Date filtering**: Use date ranges for chronological imports
5. **Backup first**: Backup `memory/` directory before large imports
6. **Monitor progress**: Watch progress display for errors
7. **Rebuild indexes**: Run `build_memory_indexes.py` after imports

## Integration with Lazy Loading

The import system is fully compatible with the lazy loading system:

1. **During import**: Writes directly to `memories.json`
2. **After import**: Indexes are automatically updated
3. **No manual rebuild**: Indexes stay in sync
4. **Startup speed**: Maintained regardless of import size

If you're using lazy loading and import 10k+ memories:
```bash
# Import
python import_memories.py --input ./large_archive/

# Rebuild indexes for optimal performance
python build_memory_indexes.py

# Verify
python test_lazy_loading_integration.py
```

## Advanced Usage

### Custom Import Pipeline
For specialized import needs, use the ImportManager directly:
```python
from memory_import import ImportManager
from engines.memory_engine import MemoryEngine

# Initialize
memory = MemoryEngine()
manager = ImportManager(
    memory_engine=memory,
    chunk_size=4000,
    overlap=600,
    batch_size=3
)

# Import with custom logic
await manager.import_files(
    file_paths=['custom_format.dat'],
    dry_run=False,
    start_date='2024-01-01'
)
```

## Future Enhancements

Planned features:
- Real-time streaming imports (watch directory)
- Deduplication detection
- Conflict resolution for contradictory imports
- Import from APIs (Discord, Slack, etc.)
- Import from databases (SQL, MongoDB)
- Parallel processing for faster imports
- Resume from checkpoint (mid-file recovery)

## Support

For issues or questions:
1. Check this guide
2. Run with `--dry-run` to debug
3. Check memory files: `ls -lh memory/`
4. Review error messages in output
5. Test with small sample first
