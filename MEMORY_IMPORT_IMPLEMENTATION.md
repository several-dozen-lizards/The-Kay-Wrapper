# MEMORY IMPORT SYSTEM - IMPLEMENTATION GUIDE

## Overview

A complete memory import system for Kay Zero that processes archived documents (.txt, .pdf, .docx, .json, .xlsx) into Kay's persistent memory using LLM-based extraction and integration with the existing 3-tier memory architecture.

---

## ✅ COMPLETED COMPONENTS

### 1. Document Parser (`memory_import/document_parser.py`)

**Features**:
- Parses: `.txt`, `.pdf`, `.docx`, `.json`, `.xlsx`
- Automatic chunking (3000 chars with 500 char overlap)
- Date extraction from filenames (e.g., `transcript_20241023.txt`)
- Metadata extraction (file size, modified date, etc.)
- Batch directory processing
- Smart sentence-boundary chunking

**Usage**:
```python
from memory_import import DocumentParser

parser = DocumentParser(chunk_size=3000, overlap=500)

# Parse single file
chunks = parser.parse_file("transcript.pdf")

# Parse entire directory
all_chunks = parser.parse_directory("./archives/")
```

**Dependencies** (install as needed):
```bash
pip install pdfplumber python-docx openpyxl
```

### 2. LLM Memory Extractor (`memory_import/memory_extractor.py`)

**Features**:
- Uses Anthropic API (already integrated)
- Extracts structured facts with importance scores (0.0-1.0)
- Detects entities and relationships
- Assigns memory categories and tiers
- Batch processing with rate limiting
- Async/concurrent for performance
- JSON output with full provenance

**Usage**:
```python
from memory_import import MemoryExtractor

extractor = MemoryExtractor(existing_entities=["Re", "Kay", "Chrome"])

result = await extractor.extract_memories(text, metadata)
# Returns: {"facts": [...], "relationships": [...], "glyph_summary": "..."}
```

**LLM Prompt Structure**:
- System prompt defines extraction rules
- User prompt includes:
  * Document text chunk
  * Metadata (filename, date, etc.)
  * List of existing entities for context
- Returns structured JSON with facts, relationships, emotional tone

### 3. Import Manager (`memory_import/import_manager.py`)

**Features**:
- Coordinates: parsing → extraction → integration
- Deduplication logic (prevents duplicate facts)
- Progress tracking with callbacks
- Error handling and recovery
- Date range filtering
- Dry-run mode (preview without saving)
- Memory tier assignment (working/episodic/semantic)

**Usage**:
```python
from memory_import import ImportManager

manager = ImportManager(
    memory_engine=memory_engine,
    entity_graph=entity_graph
)

# Set progress callback for UI updates
manager.set_progress_callback(lambda p: print(p.status))

# Import files
progress = await manager.import_files(
    file_paths=["./archives/"],
    dry_run=False,
    start_date="2020-01-01",
    end_date="2024-10-27"
)
```

### 4. CLI Script (`import_memories.py`)

**Features**:
- Standalone command-line tool
- Real-time progress display
- Dry-run mode
- Date filtering
- Batch size configuration
- Summary statistics

**Usage**:
```bash
# Import directory
python import_memories.py --input ./archives/

# Single file with dry-run
python import_memories.py --input document.pdf --dry-run

# With date filter
python import_memories.py --input ./docs/ --start-date 2020-01-01 --end-date 2024-10-27

# Custom batch size
python import_memories.py --input ./large_docs/ --batch-size 3
```

---

## 🔧 INTEGRATION WITH KAY_UI.PY

To add the import interface to `kay_ui.py`, follow these steps:

### Step 1: Add Import Button to Sidebar

In `kay_ui.py`, after the existing buttons (around line 165):

```python
# Add after export_button (line 165)
self.import_button = ctk.CTkButton(
    self.sidebar,
    text="Import Memories",
    command=self.open_import_window,
    font=ctk.CTkFont(size=14)
)
self.import_button.grid(row=7, column=0, padx=20, pady=4, sticky="ew")
```

### Step 2: Create Import Window Class

Add this class to `kay_ui.py`:

```python
class ImportWindow(ctk.CTkToplevel):
    """Import memories from archived documents."""

    def __init__(self, parent, memory_engine, entity_graph):
        super().__init__(parent)
        self.title("Import Memories")
        self.geometry("800x600")

        self.memory_engine = memory_engine
        self.entity_graph = entity_graph
        self.import_manager = None
        self.import_task = None

        self._build_ui()

    def _build_ui(self):
        """Build import interface."""
        # File selection
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(padx=20, pady=10, fill="x")

        self.file_label = ctk.CTkLabel(
            self.file_frame,
            text="Select files or directory:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.file_label.pack(anchor="w", padx=10, pady=5)

        self.file_button = ctk.CTkButton(
            self.file_frame,
            text="Choose Files",
            command=self.choose_files
        )
        self.file_button.pack(side="left", padx=10, pady=5)

        self.dir_button = ctk.CTkButton(
            self.file_frame,
            text="Choose Directory",
            command=self.choose_directory
        )
        self.dir_button.pack(side="left", padx=10, pady=5)

        self.file_path_label = ctk.CTkLabel(
            self.file_frame,
            text="No files selected",
            font=ctk.CTkFont(size=12)
        )
        self.file_path_label.pack(anchor="w", padx=10, pady=5)

        # Options
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(padx=20, pady=10, fill="x")

        # Dry run checkbox
        self.dry_run_var = ctk.BooleanVar(value=False)
        self.dry_run_check = ctk.CTkCheckBox(
            self.options_frame,
            text="Dry Run (preview without saving)",
            variable=self.dry_run_var
        )
        self.dry_run_check.pack(anchor="w", padx=10, pady=5)

        # Date filters
        self.date_frame = ctk.CTkFrame(self.options_frame)
        self.date_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.date_frame, text="Start Date (YYYY-MM-DD):").pack(side="left", padx=5)
        self.start_date_entry = ctk.CTkEntry(self.date_frame, width=120)
        self.start_date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(self.date_frame, text="End Date:").pack(side="left", padx=5)
        self.end_date_entry = ctk.CTkEntry(self.date_frame, width=120)
        self.end_date_entry.pack(side="left", padx=5)

        # Batch size slider
        self.batch_label = ctk.CTkLabel(
            self.options_frame,
            text="Batch Size: 5",
            font=ctk.CTkFont(size=12)
        )
        self.batch_label.pack(anchor="w", padx=10, pady=5)

        self.batch_var = ctk.IntVar(value=5)
        self.batch_slider = ctk.CTkSlider(
            self.options_frame,
            from_=1, to=10,
            number_of_steps=9,
            variable=self.batch_var,
            command=self._on_batch_change
        )
        self.batch_slider.pack(fill="x", padx=10, pady=5)

        # Progress display
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.progress_text = ctk.CTkTextbox(
            self.progress_frame,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=11)
        )
        self.progress_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.progress_text.insert("1.0", "Ready to import...\n")
        self.progress_text.configure(state="disabled")

        # Control buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(padx=20, pady=10, fill="x")

        self.start_button = ctk.CTkButton(
            self.button_frame,
            text="Start Import",
            command=self.start_import,
            fg_color="green"
        )
        self.start_button.pack(side="left", padx=10, pady=5)

        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.cancel_import,
            fg_color="red"
        )
        self.cancel_button.pack(side="left", padx=10, pady=5)
        self.cancel_button.configure(state="disabled")

    def choose_files(self):
        """Choose multiple files."""
        from tkinter import filedialog
        files = filedialog.askopenfilenames(
            title="Choose documents",
            filetypes=[
                ("All supported", "*.txt *.pdf *.docx *.json *.xlsx"),
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
                ("Word files", "*.docx"),
                ("JSON files", "*.json"),
                ("Excel files", "*.xlsx")
            ]
        )
        if files:
            self.selected_files = list(files)
            self.file_path_label.configure(text=f"{len(files)} file(s) selected")

    def choose_directory(self):
        """Choose directory."""
        from tkinter import filedialog
        directory = filedialog.askdirectory(title="Choose directory")
        if directory:
            self.selected_files = [directory]
            self.file_path_label.configure(text=f"Directory: {directory}")

    def _on_batch_change(self, value):
        """Update batch size label."""
        self.batch_label.configure(text=f"Batch Size: {int(value)}")

    def log(self, message):
        """Add message to progress log."""
        self.progress_text.configure(state="normal")
        self.progress_text.insert("end", f"{message}\n")
        self.progress_text.see("end")
        self.progress_text.configure(state="disabled")

    def progress_callback(self, progress):
        """Update UI with import progress."""
        self.log(f"[{progress.status.upper()}] Files: {progress.processed_files}/{progress.total_files}, "
                 f"Facts: {progress.facts_extracted}, Memories: {progress.memories_imported}")

    async def run_import(self):
        """Run import in background."""
        from memory_import import ImportManager

        self.import_manager = ImportManager(
            memory_engine=self.memory_engine,
            entity_graph=self.entity_graph,
            batch_size=self.batch_var.get()
        )

        self.import_manager.set_progress_callback(self.progress_callback)

        try:
            progress = await self.import_manager.import_files(
                file_paths=self.selected_files,
                dry_run=self.dry_run_var.get(),
                start_date=self.start_date_entry.get() or None,
                end_date=self.end_date_entry.get() or None
            )

            # Show summary
            self.log("\n" + "="*50)
            self.log("IMPORT COMPLETE")
            self.log("="*50)
            self.log(f"Total facts: {progress.facts_extracted}")
            self.log(f"Memories imported: {progress.memories_imported}")
            self.log(f"Semantic: {progress.tier_distribution['semantic']}")
            self.log(f"Episodic: {progress.tier_distribution['episodic']}")
            self.log(f"Working: {progress.tier_distribution['working']}")

            if progress.errors:
                self.log(f"\nErrors: {len(progress.errors)}")

        except Exception as e:
            self.log(f"ERROR: {e}")
        finally:
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")

    def start_import(self):
        """Start import process."""
        if not hasattr(self, 'selected_files'):
            self.log("ERROR: No files selected")
            return

        self.log("Starting import...\n")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        # Run import in background
        import threading
        import asyncio

        def run_async_import():
            asyncio.run(self.run_import())

        thread = threading.Thread(target=run_async_import, daemon=True)
        thread.start()

    def cancel_import(self):
        """Cancel import."""
        self.log("Cancelling import...")
        # Would need to implement cancellation logic in ImportManager
        self.cancel_button.configure(state="disabled")
```

### Step 3: Add Open Import Window Method

Add this method to the main `KayApp` class:

```python
def open_import_window(self):
    """Open import memories window."""
    if not hasattr(self, 'import_window') or not self.import_window.winfo_exists():
        self.import_window = ImportWindow(
            self,
            memory_engine=self.memory_engine,
            entity_graph=self.memory_engine.entity_graph
        )
        self.import_window.focus()
    else:
        self.import_window.focus()
```

---

## 📊 DATA FLOW

```
1. PARSING
   └─> Documents (.txt, .pdf, .docx, .json, .xlsx)
       └─> DocumentParser
           └─> Chunks (3000 chars with 500 overlap)
               └─> Metadata extraction (filename, date, etc.)

2. EXTRACTION
   └─> Chunks + Metadata
       └─> MemoryExtractor (Anthropic LLM)
           └─> Structured Facts (JSON)
               ├─> text, importance, category
               ├─> entities, relationships
               ├─> date, tier, perspective
               └─> emotion_tags, glyph_summary

3. INTEGRATION
   └─> Extracted Facts
       └─> ImportManager
           ├─> Deduplication
           ├─> Tier assignment (working/episodic/semantic)
           ├─> Entity graph updates
           └─> Memory storage
               └─> memory_layers.json
               └─> entity_graph.json
```

---

## 🧪 TESTING

### 1. Test Document Parser

```bash
cd F:\AlphaKayZero
python -c "from memory_import import DocumentParser; p = DocumentParser(); print(p.parse_file('test.txt'))"
```

### 2. Test Memory Extractor

```bash
python memory_import/memory_extractor.py
```

### 3. Test Full CLI Import

```bash
# Create test document
echo "Chrome is Re's cat. He likes to door-dash." > test_import.txt

# Dry run
python import_memories.py --input test_import.txt --dry-run

# Actual import
python import_memories.py --input test_import.txt
```

### 4. Test UI Integration

1. Launch `python kay_ui.py`
2. Click "Import Memories" button
3. Select test files
4. Check "Dry Run"
5. Click "Start Import"
6. Verify progress display

---

## 📦 DEPENDENCIES

Install required packages:

```bash
pip install pdfplumber python-docx openpyxl
```

Already in Kay Zero:
- anthropic (for LLM)
- customtkinter (for UI)

---

## 🔍 MEMORY FORMAT

Extracted memories are stored in Kay's existing format:

```json
{
  "fact": "Chrome is Re's cat who likes to door-dash",
  "perspective": "user",
  "topic": "pets",
  "entities": ["Re", "Chrome"],
  "emotion_tags": ["affection"],
  "importance_score": 0.8,
  "turn_number": 0,
  "added_timestamp": "2024-10-27T10:30:00",
  "access_count": 0,
  "current_strength": 1.0,
  "current_layer": "semantic",
  "source_document": "transcript_20241023.txt",
  "chunk_index": 0
}
```

---

## ⚙️ CONFIGURATION

### Chunking
- `chunk_size`: 3000 characters (default)
- `overlap`: 500 characters (default)

### LLM Extraction
- `batch_size`: 5 concurrent calls (default)
- `delay`: 1 second between batches
- `temperature`: 0.3 (consistent extraction)
- `max_tokens`: 2000 per response

### Importance Thresholds
- 0.9-1.0: Critical identity facts
- 0.7-0.8: Significant events
- 0.5-0.6: Notable details
- 0.3-0.4: Context
- 0.0-0.2: Trivial

### Tier Assignment
- **Semantic**: Timeless facts (names, permanent relationships)
- **Episodic**: Time-bound events (conversations, experiences)
- **Working**: Recent/temporary context

---

## 🚧 KNOWN LIMITATIONS

1. **No Resume/Pause**: Long imports can't be paused mid-process
   - Workaround: Import in smaller batches

2. **Simple Deduplication**: Text-based only (doesn't detect semantic similarity)
   - Could enhance with embeddings

3. **No Multi-threading in UI**: Import blocks UI thread
   - Next: Implement proper async/await in UI

4. **Rate Limiting**: Anthropic API rate limits apply
   - Adjust `batch_size` and `delay` as needed

5. **Error Recovery**: Failed chunks stop batch
   - Next: Add retry logic

---

## 🔮 FUTURE ENHANCEMENTS

1. **Memory Browser UI**:
   - View imported memories by date
   - Filter by source document
   - Click to see original text

2. **Selective Import**:
   - Preview pane with checkboxes
   - Accept/reject individual facts

3. **Document Storage**:
   - Store original documents in `documents/` folder
   - Link memories to source documents

4. **Progress Persistence**:
   - Save import state to resume later
   - Import queue management

5. **Smarter Deduplication**:
   - Semantic similarity (embeddings)
   - Merge similar facts

6. **Batch Management**:
   - Import queue with priorities
   - Schedule imports for off-hours

---

## 📝 USAGE EXAMPLES

### CLI Examples

```bash
# Import journal entries from 2024
python import_memories.py --input ./journals/2024/ --start-date 2024-01-01

# Import single transcript
python import_memories.py --input meeting_notes.pdf

# Preview without saving
python import_memories.py --input ./archives/ --dry-run

# Large document with custom chunk size
python import_memories.py --input huge_transcript.txt --chunk-size 5000 --batch-size 3
```

### Python API Examples

```python
from memory_import import ImportManager, DocumentParser, MemoryExtractor
from engines.memory_engine import MemoryEngine

# Initialize
memory_engine = MemoryEngine()
entity_graph = memory_engine.entity_graph

manager = ImportManager(
    memory_engine=memory_engine,
    entity_graph=entity_graph
)

# Import with callback
def progress_callback(p):
    print(f"{p.status}: {p.processed_files}/{p.total_files} files")

manager.set_progress_callback(progress_callback)

# Run import
import asyncio
progress = asyncio.run(manager.import_files(
    file_paths=["./archives/"],
    dry_run=False
))

print(f"Imported {progress.memories_imported} memories")
```

---

## ✅ CHECKLIST

Before going live:

- [ ] Install dependencies: `pip install pdfplumber python-docx openpyxl`
- [ ] Test document parser with sample files
- [ ] Test LLM extractor (check API key in `.env`)
- [ ] Test CLI import with `--dry-run`
- [ ] Integrate UI button into kay_ui.py
- [ ] Test UI import window
- [ ] Verify memory storage in `memory/memory_layers.json`
- [ ] Check entity graph updates in `memory/entity_graph.json`
- [ ] Test with various file types (.txt, .pdf, .docx, .xlsx)
- [ ] Verify deduplication works
- [ ] Check date filtering
- [ ] Test error handling with malformed files

---

## 🎓 ARCHITECTURE NOTES

**Why Separate Modules?**
- `document_parser`: Pure document processing (no LLM dependency)
- `memory_extractor`: LLM-specific logic (can swap models)
- `import_manager`: Orchestration layer (business logic)

**Why Async?**
- LLM calls are I/O-bound (waiting for API responses)
- Batch processing with concurrency = faster imports
- Non-blocking UI updates

**Why Chunking?**
- LLM context limits (can't process 100-page PDFs in one call)
- Better extraction quality (focused context)
- Progress tracking (chunk-by-chunk feedback)

**Why Deduplication?**
- Same fact might appear in multiple documents
- Prevents memory bloat
- Maintains data quality

---

## 🆘 TROUBLESHOOTING

**Import fails with "LLM client not available"**:
- Check `.env` has `ANTHROPIC_API_KEY`
- Run from Kay Zero root directory

**PDF parsing fails**:
- Install: `pip install pdfplumber`

**Word document parsing fails**:
- Install: `pip install python-docx`

**Excel parsing fails**:
- Install: `pip install openpyxl`

**Import hangs/slow**:
- Reduce `batch_size` to 2-3
- Check Anthropic API rate limits
- Try `--dry-run` first to test extraction

**Memories not appearing in Kay's responses**:
- Check `memory/memory_layers.json` was updated
- Verify tier assignment (semantic memories have highest priority)
- Restart Kay UI to reload memory

---

## 📞 SUPPORT

For issues:
1. Check error messages in console
2. Try `--dry-run` mode first
3. Verify file formats are supported
4. Check dependencies are installed
5. Review Kay's memory with "Peek Memories" in UI

---

**System Status**: ✅ Core components complete, ready for integration and testing.
