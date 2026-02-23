# Session Browser for Kay Zero

A comprehensive session management system that integrates seamlessly with Kay's UI, providing session browsing, search, viewing, export, and memory loading capabilities.

## Features

### ✨ Core Features

- **📚 Session List View**: Browse all saved sessions chronologically with monthly grouping
- **🔍 Full-Text Search**: Search across all session content with context snippets
- **👁 Session Viewer**: Read-only window showing complete conversation history
- **▶ Resume Sessions**: Load previous session as current working session
- **📖 Load for Review**: Import session into Kay's memory so he can reference it
- **💾 Export**: Save sessions as readable text, Markdown, or JSON
- **🗑 Delete**: Remove sessions with confirmation
- **📝 Notes & Tags**: Annotate sessions with notes and custom tags

### 🤖 Auto-Generated Metadata

When sessions are saved, automatically generates:

- **Title**: 3-5 word summary using LLM
- **Summary**: 1-2 sentence description
- **Key Topics**: Main discussion topics
- **Emotional Arc**: Emotional progression (e.g., "curiosity → understanding")
- **Important Moments**: Flagged high-importance turns
- **Tags**: Auto-generated tags from topics and emotions

### 🎯 Kay-Specific Features

- **Load Session for Review**: Tell Kay to read a past conversation - it loads into his episodic memory
- **Current Session Indicator**: Visual indicator showing active session
- **Compression Levels**: Choose how much detail to load (high/medium/low)

## Installation

The session browser is already in your `session_browser/` directory:

```
session_browser/
├── __init__.py
├── session_manager.py         # Core session operations
├── session_metadata.py        # LLM-based metadata generation
├── session_loader.py          # Load sessions into memory
├── session_browser_ui.py      # Main browser UI
├── session_viewer.py          # Session viewer window
├── kay_integration.py         # Kay UI integration
└── README.md                  # This file
```

## Quick Integration (3 Steps)

### Step 1: Import

Add to your `kay_ui.py` imports:

```python
from session_browser import add_session_browser_to_kay_ui
```

### Step 2: Initialize

In your `KayApp.__init__()` method, after initializing LLM and memory engine:

```python
class KayApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Your existing initialization...
        self.llm_client = ...  # Your LLM client
        self.memory_engine = ...  # Your memory engine
        self.current_session_id = None

        # Add session browser (ONE LINE!)
        self.session_browser = add_session_browser_to_kay_ui(
            self,
            llm_client=self.llm_client,
            memory_engine=self.memory_engine,
            session_dir="saved_sessions",
            add_to_menu=True,  # Adds "Sessions" menu
            add_button_to=your_toolbar_frame  # Optional: adds button to toolbar
        )
```

### Step 3: Save Sessions with Metadata

When saving sessions, use this instead of direct JSON save:

```python
# Old way:
# with open(f"saved_sessions/{session_id}.json", 'w') as f:
#     json.dump(session_data, f)

# New way (with auto-metadata generation):
await self.session_browser.save_session_with_metadata(
    session_data,
    generate_metadata=True  # Auto-generates title, summary, etc.
)
```

**That's it!** Session browser is now integrated.

## Advanced Integration

### Custom Integration

If you need more control:

```python
from session_browser import SessionBrowserIntegration

class KayApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ... your initialization ...

        # Create integration with custom callbacks
        self.session_browser = SessionBrowserIntegration(
            self,
            llm_client=self.llm_client,
            memory_engine=self.memory_engine,
            session_dir="saved_sessions",
            current_session_callback=self.get_current_session,
            resume_session_callback=self.resume_session
        )

        # Add menu
        self.session_browser.add_to_menu(self.menubar)

        # OR add button
        button = self.session_browser.add_browser_button(
            self.toolbar,
            text="📚 Browse Sessions",
            bg="#4c4c4c"
        )
        button.pack(side=tk.LEFT, padx=5)

    def get_current_session(self) -> str:
        """Return current session ID"""
        return self.current_session_id

    def resume_session(self, session_id: str):
        """Resume a previous session"""
        # Load session data
        session_data = self.session_browser.session_manager.load_session(session_id)

        # Restore conversation history
        self.conversation_history = session_data.get("conversation", [])

        # Restore entity state
        self.entity_graph = session_data.get("entity_graph", {})

        # Restore emotional state
        self.emotional_state = session_data.get("emotional_state", {})

        # Update current session
        self.current_session_id = session_id

        # Notify browser
        self.session_browser.update_current_session(session_id)

        # Refresh UI
        self.refresh_chat_display()
```

## Usage Guide

### Opening Session Browser

Three ways to open:

1. **Menu**: Sessions → Browse Sessions
2. **Button**: Click "📚 Sessions" button (if added to toolbar)
3. **Programmatically**:
   ```python
   self.session_browser.open_browser()
   ```

### Searching Sessions

1. Type query in search box at top
2. Search covers:
   - Session titles
   - Summaries
   - Tags
   - Full conversation content
3. Results show context snippets highlighting matches

### Viewing a Session

1. Click **👁 View** on any session
2. Opens read-only viewer window with:
   - Complete conversation history
   - Metadata header
   - Search within session
   - Add notes/tags
   - Export options

### Resuming a Session

1. Click **▶ Resume** on any session (except current)
2. Confirms before ending current session
3. Loads:
   - Conversation history
   - Entity graph state
   - Emotional state
   - Memory state

**Note**: Implement `resume_session_callback` to enable this.

### Loading Session for Review

This is Kay-specific - allows Kay to "read" past conversations:

1. Click **📖 Load for Review**
2. Choose compression level:
   - **High**: Summary only (1 memory)
   - **Medium**: Summary + key moments (5-10 memories) - **RECOMMENDED**
   - **Low**: All turns (could be 50+ memories)
3. Session loads into Kay's episodic memory
4. Kay can now reference that conversation

**Example user interaction:**

```
User: "Read the session from November 17th"
[User clicks Load for Review on that session, chooses "medium"]
Kay: "I've loaded that session into memory. You were asking about the Archive Zero
      integration and we discussed the contradiction resolution system."
```

### Exporting Sessions

1. Click **💾 Export**
2. Choose format:
   - **Plain Text**: Readable .txt file
   - **Markdown**: .md file with formatting
   - **JSON**: Raw session data
3. Choose save location
4. Session exported

### Deleting Sessions

1. Click **🗑 Delete**
2. Confirm deletion
3. Session permanently removed

**Warning**: Deletion cannot be undone. Consider backing up first.

## Session Data Format

### Existing Format (Backwards Compatible)

Your existing sessions work without changes:

```json
{
  "session_id": "1763530042",
  "start_time": "2025-11-19T00:28:15.228014",
  "conversation": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "entity_graph": {...},
  "emotional_state": {...}
}
```

### Enhanced Format (With Metadata)

New sessions saved with metadata:

```json
{
  "session_id": "1763530042",
  "start_time": "2025-11-19T00:28:15.228014",
  "conversation": [...],
  "entity_graph": {...},
  "emotional_state": {...},

  "metadata": {
    "title": "Memory Architecture Discussion",
    "summary": "Conversation about entity contradictions and memory layer distribution.",
    "key_topics": ["entity graph", "memory layers", "contradictions"],
    "emotional_arc": "curiosity -> understanding -> satisfaction",
    "important_moments": [
      {
        "turn_index": 5,
        "role": "user",
        "preview": "So the 741 goal contradictions...",
        "timestamp": "2025-11-19T00:35:22"
      }
    ],
    "tags": ["entity", "memory", "architecture", "debugging"],
    "turn_count": 12,
    "duration_minutes": 23.5,
    "generated_at": "2025-11-19T00:51:45",
    "notes": [
      {
        "text": "Important session for reference",
        "author": "User",
        "timestamp": "2025-11-19T10:15:00"
      }
    ]
  }
}
```

## Configuration

### Metadata Generation

Control when metadata is generated:

```python
# Generate metadata when saving
await self.session_browser.save_session_with_metadata(
    session_data,
    generate_metadata=True  # Set to False to skip
)

# Generate metadata for existing session later
session_id = "1763530042"
session_data = self.session_browser.session_manager.load_session(session_id)
conversation = session_data["conversation"]

metadata = await self.session_browser.metadata_generator.generate_metadata(
    conversation,
    session_data
)

session_data["metadata"] = metadata
self.session_browser.session_manager.save_session(session_data)
```

### Session Directory

Change where sessions are stored:

```python
self.session_browser = SessionBrowserIntegration(
    self,
    llm_client=self.llm_client,
    session_dir="custom/session/path"  # Default: "saved_sessions"
)
```

### Compression Levels

When loading sessions for review:

```python
# Programmatically load session
session_data = self.session_browser.session_manager.load_session(session_id)

memories = self.session_browser.session_loader.load_session_for_review(
    session_data,
    current_turn=self.current_turn,
    compression_level="medium"  # "high", "medium", or "low"
)

# Add to memory
for memory in memories:
    self.memory_engine.store_memory(
        content=memory["content"],
        perspective=memory["perspective"],
        importance=memory["importance"]
    )
```

## API Reference

### SessionManager

```python
from session_browser import SessionManager

manager = SessionManager("saved_sessions")

# List all sessions
sessions = manager.list_sessions()

# Load session
session_data = manager.load_session(session_id)

# Save session
manager.save_session(session_data)

# Delete session
manager.delete_session(session_id)

# Search sessions
results = manager.search_sessions("query text")

# Filter sessions
filtered = manager.filter_sessions(
    start_date=datetime(...),
    end_date=datetime(...),
    tags=["important"],
    min_turns=5
)

# Export session
manager.export_session_file(session_id, "output.txt", format="txt")

# Add notes/tags
manager.add_note_to_session(session_id, "This was important")
manager.add_tags_to_session(session_id, ["important", "reference"])

# Get sessions by month
by_month = manager.get_sessions_by_month()
```

### SessionMetadataGenerator

```python
from session_browser import SessionMetadataGenerator

generator = SessionMetadataGenerator(llm_client)

# Generate metadata
metadata = await generator.generate_metadata(
    conversation,  # List of {"role": ..., "content": ...}
    session_data   # Full session data dict
)

# Access metadata
print(metadata.title)
print(metadata.summary)
print(metadata.key_topics)
print(metadata.emotional_arc)
print(metadata.important_moments)
print(metadata.tags)
```

### SessionLoader

```python
from session_browser import SessionLoader

loader = SessionLoader(memory_engine)

# Load for review
memories = loader.load_session_for_review(
    session_data,
    current_turn=100,
    compression_level="medium"
)

# Generate prompt context (alternative to storing as memories)
context_string = loader.create_review_summary_for_prompt(session_data)
# Inject context_string into LLM prompt

# Load multiple sessions
all_memories = loader.load_multiple_sessions_for_review(
    [session1, session2, session3],
    current_turn=100,
    max_total_memories=50
)
```

## Performance

- **Handles 100+ sessions** without lag
- **Lazy loading**: Session list loads metadata only (not full content)
- **Background operations**: Search and metadata generation run in background threads
- **Caching**: Session list cached for 5 seconds to reduce file I/O
- **Efficient search**: Full-text search with early termination

## Troubleshooting

### "Session manager not configured" error

**Cause**: Integration created without proper setup

**Fix**: Ensure you pass `session_manager` to components:

```python
self.session_browser = SessionBrowserIntegration(
    self,
    llm_client=self.llm_client,
    memory_engine=self.memory_engine  # Don't forget this!
)
```

### Metadata generation fails

**Cause**: LLM client not responding or invalid format

**Fix**: Check LLM client has `async query()` method:

```python
class YourLLMClient:
    async def query(self, prompt: str, max_tokens: int, temperature: float) -> str:
        # Call your LLM API
        return response_text
```

### Resume session doesn't work

**Cause**: `resume_session_callback` not implemented

**Fix**: Implement the callback:

```python
self.session_browser = SessionBrowserIntegration(
    self,
    llm_client=self.llm_client,
    resume_session_callback=self.resume_session  # Add this
)

def resume_session(self, session_id: str):
    # Load and restore session state
    session_data = self.session_browser.session_manager.load_session(session_id)
    # ... restore state ...
```

### Sessions not appearing in browser

**Cause**: Wrong session directory or permissions

**Fix**: Check directory path and permissions:

```python
# Verify directory
import os
session_dir = "saved_sessions"
print(f"Session dir exists: {os.path.exists(session_dir)}")
print(f"Session files: {os.listdir(session_dir)}")

# Specify correct path
self.session_browser = SessionBrowserIntegration(
    self,
    llm_client=self.llm_client,
    session_dir="path/to/actual/sessions"
)
```

## Examples

### Complete Kay UI Integration

```python
import tkinter as tk
from session_browser import add_session_browser_to_kay_ui

class KayApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Kay Zero")
        self.geometry("1000x700")

        # Initialize your components
        self.llm_client = YourLLMClient()
        self.memory_engine = YourMemoryEngine()
        self.current_session_id = None
        self.conversation_history = []

        # Create menubar
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # Create toolbar
        self.toolbar = tk.Frame(self, bg="#2b2b2b", height=50)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Add session browser (adds menu + button)
        self.session_browser = add_session_browser_to_kay_ui(
            self,
            llm_client=self.llm_client,
            memory_engine=self.memory_engine,
            add_to_menu=True,
            add_button_to=self.toolbar
        )

        # Rest of your UI...

    async def save_current_session(self):
        """Save session with metadata"""

        session_data = {
            "session_id": self.current_session_id,
            "start_time": self.session_start_time,
            "conversation": self.conversation_history,
            "entity_graph": self.entity_graph.to_dict(),
            "emotional_state": self.emotional_state
        }

        # Save with auto-generated metadata
        await self.session_browser.save_session_with_metadata(session_data)

    def resume_session(self, session_id: str):
        """Resume a previous session"""

        session_data = self.session_browser.session_manager.load_session(session_id)

        if not session_data:
            messagebox.showerror("Error", "Failed to load session")
            return

        # Restore state
        self.current_session_id = session_id
        self.conversation_history = session_data.get("conversation", [])
        self.entity_graph.load_from_dict(session_data.get("entity_graph", {}))
        self.emotional_state = session_data.get("emotional_state", {})

        # Update browser
        self.session_browser.update_current_session(session_id)

        # Refresh UI
        self.refresh_chat_display()

        messagebox.showinfo("Session Resumed", f"Resumed session {session_id}")
```

## Roadmap

Future enhancements planned:

- [ ] **Filters UI**: Date range picker, tag filter, turn count range
- [ ] **Collapsible month groups**: Click to expand/collapse
- [ ] **Session branching**: Resume from specific turn, not just session start
- [ ] **Visual timeline**: Timeline view of sessions
- [ ] **Bulk export**: Export multiple sessions as compiled document
- [ ] **Star/favorite**: Mark important sessions
- [ ] **Keyboard shortcuts**: Navigate browser with keyboard
- [ ] **Session comparison**: Compare two sessions side-by-side
- [ ] **Automatic backup**: Backup sessions before delete

## Support

For issues or questions:

1. Check this README
2. Check docstrings in each module
3. Check `kay_integration.py` for integration examples
4. Open issue in repository

## License

Part of the AlphaKayZero project.
