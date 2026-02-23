# Tab System Integration Guide

## Overview

This guide shows how to integrate the resizable tab system into kay_ui.py, replacing popup windows with expandable tabs.

## Changes Required

### 1. Add Import (around line 36)

```python
# === Glyph Filter System ===
from context_filter import GlyphFilter
from glyph_decoder import GlyphDecoder

# === Tab System === (NEW)
from tab_system import TabContainer

# Keep base "dark"; we repaint everything with our palettes
```

### 2. Update Grid Layout in `__init__` (around line 1492-1494)

**BEFORE:**
```python
# Layout
self.grid_columnconfigure(1, weight=1)
self.grid_rowconfigure(0, weight=1)

# Sidebar (scrollable to handle window resizing)
self.sidebar = ctk.CTkScrollableFrame(self, width=240, corner_radius=10)
self.sidebar.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)
```

**AFTER:**
```python
# Layout - 3 columns now: sidebar | tab_container | output
self.grid_columnconfigure(0, weight=0, minsize=260)  # Sidebar (fixed)
self.grid_columnconfigure(1, weight=0)                # Tab container (dynamic)
self.grid_columnconfigure(2, weight=1)                # Output area (flexible)
self.grid_rowconfigure(0, weight=1)

# Sidebar (scrollable to handle window resizing)
self.sidebar = ctk.CTkScrollableFrame(self, width=240, corner_radius=10)
self.sidebar.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)

# Tab container (NEW - sits between sidebar and output)
self.tab_container = TabContainer(self, on_layout_change=self._on_tabs_changed)
self.tab_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=10)
# Start with no tabs (container is empty but takes up space)

# Track tab state
self.tab_widths = {}  # Store tab widths for session persistence
```

### 3. Update Chat Log Position (around line 1568)

**BEFORE:**
```python
# Chat + Input
self.chat_log = ctk.CTkTextbox(self, wrap="word", corner_radius=10, state="disabled", font=ctk.CTkFont(size=15))
self.chat_log.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
```

**AFTER:**
```python
# Chat + Input (moved to column 2 to make room for tabs)
self.chat_log = ctk.CTkTextbox(self, wrap="word", corner_radius=10, state="disabled", font=ctk.CTkFont(size=15))
self.chat_log.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
```

### 4. Update Input Frame Columnspan (around line 1572)

**BEFORE:**
```python
# Input frame (contains textbox + voice button)
self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
self.input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
```

**AFTER:**
```python
# Input frame (contains textbox + voice button)
self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
self.input_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
```

### 5. Update Navigation Button Frame Columnspan (around line 1590)

**BEFORE:**
```python
# Navigation button frame (appears when Kay says "continue reading")
self.nav_button_frame = ctk.CTkFrame(self, corner_radius=8)
self.nav_button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
```

**AFTER:**
```python
# Navigation button frame (appears when Kay says "continue reading")
self.nav_button_frame = ctk.CTkFrame(self, corner_radius=8)
self.nav_button_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
```

### 6. Add Tab Callback Method (add after `__init__`)

```python
def _on_tabs_changed(self):
    """Called when tabs are opened/closed/resized."""
    # Save current tab widths
    self.tab_widths = self.tab_container.get_tab_widths()

    # Force layout update
    self.update_idletasks()
```

### 7. Convert Menu Buttons to Tab Toggles

#### Settings Tab (NEW - add to sidebar after row 26)

```python
# Settings section (NEW)
self.section_settings = ctk.CTkLabel(self.sidebar, text="Settings", anchor="w", font=ctk.CTkFont(size=15))
self.section_settings.grid(row=27, column=0, padx=20, pady=(12, 0), sticky="w")

self.settings_button = ctk.CTkButton(
    self.sidebar,
    text="⚙️ Settings",
    command=self.toggle_settings_tab,
    font=ctk.CTkFont(size=14)
)
self.settings_button.grid(row=28, column=0, padx=20, pady=4, sticky="ew")
```

#### Convert Import Memories Button (around line 1521)

**BEFORE:**
```python
self.import_button = ctk.CTkButton(self.sidebar, text="Import Memories", command=self.open_import_window, font=ctk.CTkFont(size=14))
self.import_button.grid(row=7, column=0, padx=20, pady=4, sticky="ew")
```

**AFTER:**
```python
self.import_button = ctk.CTkButton(
    self.sidebar,
    text="📥 Import Memories",
    command=self.toggle_import_tab,
    font=ctk.CTkFont(size=14)
)
self.import_button.grid(row=7, column=0, padx=20, pady=4, sticky="ew")
```

#### Convert Manage Documents Button (around line 1524)

**BEFORE:**
```python
self.manage_docs_button = ctk.CTkButton(self.sidebar, text="Manage Documents", command=self.open_document_manager, font=ctk.CTkFont(size=14))
self.manage_docs_button.grid(row=8, column=0, padx=20, pady=4, sticky="ew")
```

**AFTER:**
```python
self.manage_docs_button = ctk.CTkButton(
    self.sidebar,
    text="📄 Manage Documents",
    command=self.toggle_documents_tab,
    font=ctk.CTkFont(size=14)
)
self.manage_docs_button.grid(row=8, column=0, padx=20, pady=4, sticky="ew")
```

#### Convert Browse Sessions Button (around line 1527)

**BEFORE:**
```python
self.browse_sessions_button = ctk.CTkButton(self.sidebar, text="📚 Browse Sessions", command=self.open_session_browser, font=ctk.CTkFont(size=14))
self.browse_sessions_button.grid(row=9, column=0, padx=20, pady=4, sticky="ew")
```

**AFTER:**
```python
self.browse_sessions_button = ctk.CTkButton(
    self.sidebar,
    text="📚 Browse Sessions",
    command=self.toggle_sessions_tab,
    font=ctk.CTkFont(size=14)
)
self.browse_sessions_button.grid(row=9, column=0, padx=20, pady=4, sticky="ew")
```

### 8. Add Tab Toggle Methods (replace existing popup methods around line 2984-3008)

```python
def toggle_settings_tab(self):
    """Toggle settings tab."""
    def create_settings_content(parent):
        frame = ctk.CTkScrollableFrame(parent)

        # Affect slider
        affect_label = ctk.CTkLabel(
            frame,
            text="Response Affect",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        affect_label.pack(anchor="w", padx=20, pady=(20, 5))

        affect_value_label = ctk.CTkLabel(
            frame,
            text=f"Current: {self.affect_var.get():.1f} / 5",
            font=ctk.CTkFont(size=14)
        )
        affect_value_label.pack(anchor="w", padx=20, pady=(0, 5))

        def update_affect_label(value):
            affect_value_label.configure(text=f"Current: {float(value):.1f} / 5")
            self._on_affect_change(value)

        affect_slider = ctk.CTkSlider(
            frame,
            from_=0.0,
            to=5.0,
            variable=self.affect_var,
            command=update_affect_label
        )
        affect_slider.pack(fill="x", padx=20, pady=(0, 20))

        # Palette selector
        palette_label = ctk.CTkLabel(
            frame,
            text="Color Palette",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        palette_label.pack(anchor="w", padx=20, pady=(10, 5))

        palette_menu = ctk.CTkOptionMenu(
            frame,
            values=list(PALETTES.keys()),
            command=self.change_palette,
            font=ctk.CTkFont(size=14)
        )
        palette_menu.set(self.palette_name)
        palette_menu.pack(fill="x", padx=20, pady=(0, 20))

        # Other settings can go here

        return frame

    is_open = self.tab_container.toggle_tab(
        "settings",
        "Settings",
        create_settings_content,
        min_width=250,
        default_width=300
    )

    # Update button appearance
    if is_open:
        self.settings_button.configure(fg_color=("gray75", "gray25"))
    else:
        self.settings_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])

def toggle_import_tab(self):
    """Toggle import memories tab."""
    def create_import_content(parent):
        # Embed the ImportWindow content directly
        from import_window import ImportWindow

        # Create import window but embed it instead of as toplevel
        import_content = ImportWindow(
            parent,
            memory_engine=self.memory,
            entity_graph=self.memory.entity_graph,
            agent_state=self.agent_state,
            affect_var=self.affect_var,
            embed_mode=True  # Flag to tell ImportWindow to embed instead of Toplevel
        )
        return import_content

    is_open = self.tab_container.toggle_tab(
        "import",
        "Import Memories",
        create_import_content,
        min_width=400,
        default_width=500
    )

    # Update button appearance
    if is_open:
        self.import_button.configure(fg_color=("gray75", "gray25"))
    else:
        self.import_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])

def toggle_documents_tab(self):
    """Toggle document manager tab."""
    def create_documents_content(parent):
        # Embed DocumentManagerWindow
        from document_manager_ui import DocumentManagerWindow

        doc_manager = DocumentManagerWindow(
            parent,
            memory_engine=self.memory,
            entity_graph=self.memory.entity_graph,
            embed_mode=True  # Flag for embedded mode
        )
        return doc_manager

    is_open = self.tab_container.toggle_tab(
        "documents",
        "Documents",
        create_documents_content,
        min_width=450,
        default_width=550
    )

    # Update button appearance
    if is_open:
        self.manage_docs_button.configure(fg_color=("gray75", "gray25"))
    else:
        self.manage_docs_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])

def toggle_sessions_tab(self):
    """Toggle session browser tab."""
    def create_sessions_content(parent):
        # Use session browser integration
        session_frame = ctk.CTkScrollableFrame(parent)

        # Create embedded session browser UI
        title_label = ctk.CTkLabel(
            session_frame,
            text="Session Browser",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(anchor="w", padx=20, pady=(20, 10))

        # Add session browser controls
        # This would need the SessionBrowserIntegration to support embedded mode
        # For now, we can create a simplified inline browser

        return session_frame

    is_open = self.tab_container.toggle_tab(
        "sessions",
        "Sessions",
        create_sessions_content,
        min_width=400,
        default_width=500
    )

    # Update button appearance
    if is_open:
        self.browse_sessions_button.configure(fg_color=("gray75", "gray25"))
    else:
        self.browse_sessions_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])

# Keep old methods for compatibility but redirect to tabs
def open_import_window(self):
    """Redirect to tab (legacy compatibility)."""
    if not self.tab_container.has_tab("import"):
        self.toggle_import_tab()

def open_document_manager(self):
    """Redirect to tab (legacy compatibility)."""
    if not self.tab_container.has_tab("documents"):
        self.toggle_documents_tab()

def open_session_browser(self):
    """Redirect to tab (legacy compatibility)."""
    if not self.tab_container.has_tab("sessions"):
        self.toggle_sessions_tab()
```

### 9. Add Tab State Persistence to Session Save/Load

#### In `save_session()` method (around line 2890):

```python
# Add to session_data dict
"tab_widths": self.tab_widths,  # Save tab widths
```

#### In `load_session()` and `resume_session()` methods (after loading):

```python
# Restore tab widths if present
if "tab_widths" in session_data:
    self.tab_container.restore_tab_widths(session_data["tab_widths"])
```

## Testing

1. Start the UI: `python kay_ui.py`
2. Click "Import Memories" - should open a tab instead of popup
3. Click again - should close the tab (toggle)
4. Open multiple tabs - they should sit side-by-side
5. Drag the right edge of a tab - should resize
6. Output area should adjust automatically as tabs open/close/resize

## Notes

- The ImportWindow and DocumentManagerWindow classes may need minor modifications to support `embed_mode` parameter
- If they inherit from `ctk.CTkToplevel`, they'll need to support `ctk.CTkFrame` parent for embedding
- Button colors change when their tab is open (visual feedback)
- Tab widths persist across sessions when saved
