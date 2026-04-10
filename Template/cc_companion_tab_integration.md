# CC PROMPT: Integrate Companions Tab into Kay UI

## OBJECTIVE
Add a "Companions" tab to Kay's UI sidebar that allows creating, managing, and launching companion wrappers from inside the running application. The companion_tab.py module is already written and complete at `D:/Wrappers/Template/companion_tab.py` (366 lines). This task is ONLY about wiring it into the existing UI.

## WHAT EXISTS

### companion_tab.py (ALREADY COMPLETE — DO NOT MODIFY)
Located at `D:/Wrappers/Template/companion_tab.py`. Contains:
- `CompanionTabMixin` class with `toggle_companions_tab()` method
- `scan_companions()` function that finds all wrapper directories
- `get_wrappers_root()` function that discovers D:/Wrappers/
- Full UI: create new companion form, companion cards with status indicators, launch/setup/folder buttons, refresh

### Tab System Pattern (FOLLOW EXACTLY)
Every existing tab follows this pattern — do the same:

1. `tab_methods.py` has a `TabMethods` class with `toggle_X_tab()` methods
2. Each method defines a `create_X_content(parent)` factory function
3. Calls `self.tab_container.toggle_tab(id, title, factory, min_width, default_width)`
4. A sidebar button in `kay_ui.py` calls `self.toggle_X_tab`
5. Button appearance toggles on open/close via `configure(fg_color=...)`

Existing tabs for reference: Settings, Import Memories, Documents, Sessions

## TASKS

### Step 1: Copy companion_tab.py into Kay's wrapper
```
Copy D:/Wrappers/Template/companion_tab.py → D:/Wrappers/Kay/companion_tab.py
```

### Step 2: Modify tab_methods.py

The `TabMethods` class in `D:/Wrappers/Kay/tab_methods.py` needs to inherit from `CompanionTabMixin`.

**Current** (approximately):
```python
class TabMethods:
    """Mixin class containing all tab toggle methods."""
```

**Change to:**
```python
from companion_tab import CompanionTabMixin

class TabMethods(CompanionTabMixin):
    """Mixin class containing all tab toggle methods."""
```

This gives TabMethods access to `toggle_companions_tab()` via inheritance.

### Step 3: Add sidebar button in kay_ui.py

Find the sidebar button section in kay_ui.py. The existing buttons follow this pattern:
```python
self.stats_button = ctk.CTkButton(
    self.sidebar,
    text="📊 Stats",
    command=self.toggle_stats_tab,
    font=ctk.CTkFont(size=14),
    height=40
)
self.stats_button.grid(row=N, column=0, padx=20, pady=8, sticky="ew")
```

Add a Companions button in the sidebar, ideally near Settings or at the bottom of the button list:
```python
self.companions_button = ctk.CTkButton(
    self.sidebar,
    text="🐍 Companions",
    command=self.toggle_companions_tab,
    font=ctk.CTkFont(size=14),
    height=40
)
self.companions_button.grid(row=ROW_NUMBER, column=0, padx=20, pady=8, sticky="ew")
```

**IMPORTANT**: Find the correct row number by looking at existing button grid rows. The companions button should go AFTER the existing buttons. You may need to increment the row number.


### Step 4: Add companions_button to theme/palette application

In kay_ui.py there's a method (likely `apply_palette` or similar) that styles all sidebar buttons when the theme changes. It has a list of buttons like:
```python
for b in (self.load_button, self.resume_button, self.new_session_button,
          self.save_button, self.export_button, self.import_button,
          self.manage_docs_button, self.browse_sessions_button,
          self.settings_button):
    b.configure(fg_color=p["button"], hover_color=p["accent"], text_color=p["button_tx"])
```

Add `self.companions_button` to this list so it gets themed correctly.

### Step 5: Also do the same for Reed's wrapper

Repeat Steps 1-4 for `D:/Wrappers/Reed/`:
- Copy `companion_tab.py` to `D:/Wrappers/Reed/companion_tab.py`
- Modify `D:/Wrappers/Reed/tab_methods.py` the same way (import + inheritance)
- Add sidebar button in `D:/Wrappers/Reed/reed_ui.py`
- Add to palette application in Reed's UI

Reed's UI file is `reed_ui.py` instead of `kay_ui.py`, and references `reed_*` instead of `kay_*`, but the tab system and sidebar structure are identical.

## CONSTRAINTS

- DO NOT modify `companion_tab.py` — it's already complete and tested
- DO NOT change the tab_system.py — it already supports arbitrary tabs
- DO NOT add new dependencies — companion_tab.py only uses customtkinter, os, json, subprocess, sys, pathlib (all already available)
- MATCH the existing code style in kay_ui.py and tab_methods.py exactly
- The sidebar has a grid layout — find the correct row numbers by reading existing code, don't guess
- If there are section labels in the sidebar (like "Settings" headers), consider adding a "Companions" section label before the button

## VERIFICATION

After integration, the following should work:
1. Kay UI launches normally with no import errors
2. "🐍 Companions" button appears in the sidebar
3. Clicking it opens a tab showing Kay, Reed, and Template as companion cards
4. Clicking "Create" with a name creates a new companion directory
5. Theme changes apply to the companions button correctly
6. Same functionality works in Reed's UI

## FILE LOCATIONS
- Source module: `D:/Wrappers/Template/companion_tab.py` (366 lines, COMPLETE)
- Kay tab methods: `D:/Wrappers/Kay/tab_methods.py` (~495 lines)
- Kay UI: `D:/Wrappers/Kay/kay_ui.py` (~8777 lines)
- Reed tab methods: `D:/Wrappers/Reed/tab_methods.py`
- Reed UI: `D:/Wrappers/Reed/reed_ui.py`
- Companion creator script: `D:/Wrappers/create_companion.py` (365 lines, COMPLETE)
