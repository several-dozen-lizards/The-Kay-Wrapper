"""
Resizable Tab System for Kay UI

Provides expandable tab panels that sit between the menu and output area.
Multiple tabs can be open simultaneously with draggable resize handles.
"""

import customtkinter as ctk
from tkinter import NSEW, EW
from typing import Dict, Callable, Optional


class ResizableTab(ctk.CTkFrame):
    """
    A single resizable tab with header, content, and drag handle.
    """

    def __init__(self, parent, tab_id: str, title: str, on_close: Callable,
                 on_resize: Callable, min_width: int = 200, default_width: int = 350):
        super().__init__(parent, corner_radius=0)

        self.tab_id = tab_id
        self.title = title
        self.on_close = on_close
        self.on_resize_callback = on_resize
        self.min_width = min_width
        self.current_width = default_width

        # Configure grid
        self.grid_rowconfigure(1, weight=1)  # Content area expands
        self.grid_columnconfigure(0, weight=1)

        # Header with title and close button
        self.header = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.header.grid(row=0, column=0, sticky=EW, padx=0, pady=0)
        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header,
            text=title,
            font=ctk.CTkFont(family="Courier", size=14, weight="bold"),
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, padx=12, sticky="w")

        self.close_button = ctk.CTkButton(
            self.header,
            text="◀",
            width=30,
            height=30,
            command=self._on_close_clicked,
            font=ctk.CTkFont(family="Courier", size=16),
            fg_color="transparent",
            hover_color=("gray70", "gray30")
        )
        self.close_button.grid(row=0, column=1, padx=8)

        # Content area (where tab content goes)
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=1, column=0, sticky=NSEW, padx=0, pady=0)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Resize handle (right edge)
        self.resize_handle = ctk.CTkFrame(self, width=4, cursor="sb_h_double_arrow")
        self.resize_handle.grid(row=0, column=1, rowspan=2, sticky="ns")

        # Bind drag events to resize handle
        self.resize_handle.bind("<Button-1>", self._start_resize)
        self.resize_handle.bind("<B1-Motion>", self._do_resize)

        self._drag_start_x = 0
        self._drag_start_width = 0

    def apply_theme(self, palette: dict):
        """Apply theme colors and ornate styling to this tab."""
        is_ornate = palette.get("ornate", False)
        border_color = palette.get("border", palette.get("accent", "#C4A574"))
        border_accent = palette.get("border_accent", palette.get("muted", "#9B7D54"))

        # Configure main frame
        if is_ornate:
            self.configure(
                fg_color=palette.get("panel", "#2D1B3D"),
                border_width=2,
                border_color=border_color,
                corner_radius=2
            )
        else:
            self.configure(
                fg_color=palette.get("panel", "#161a20"),
                border_width=0,
                corner_radius=0
            )

        # Configure header
        if is_ornate:
            self.header.configure(
                fg_color=palette.get("input", "#4A2B5C"),
                border_width=1,
                border_color=border_accent
            )
            self.title_label.configure(text_color=border_color)  # Gold title in ornate
            self.close_button.configure(
                text_color=border_color,
                hover_color=palette.get("accent_hi", "#D499B9")
            )
        else:
            self.header.configure(fg_color=palette.get("input", "#1a1f26"), border_width=0)
            self.title_label.configure(text_color=palette.get("text", "#e7e7e7"))
            self.close_button.configure(text_color=palette.get("text", "#e7e7e7"))

        # Configure content frame
        if is_ornate:
            self.content_frame.configure(
                fg_color=palette.get("panel", "#2D1B3D"),
                border_width=1,
                border_color=border_accent,
                corner_radius=2
            )
        else:
            self.content_frame.configure(
                fg_color=palette.get("panel", "#161a20"),
                border_width=0,
                corner_radius=0
            )

        # Configure resize handle
        if is_ornate:
            self.resize_handle.configure(fg_color=border_color)
        else:
            self.resize_handle.configure(fg_color=palette.get("accent", "#00bcd4"))

    def _on_close_clicked(self):
        """Handle close button click."""
        self.on_close(self.tab_id)

    def _start_resize(self, event):
        """Start resizing operation."""
        self._drag_start_x = event.x_root
        self._drag_start_width = self.current_width

    def _do_resize(self, event):
        """Perform resize based on drag."""
        delta = event.x_root - self._drag_start_x
        new_width = max(self.min_width, self._drag_start_width + delta)

        if new_width != self.current_width:
            self.current_width = new_width
            self.on_resize_callback()

    def get_content_frame(self) -> ctk.CTkFrame:
        """Get the frame where tab content should be placed."""
        return self.content_frame

    def set_width(self, width: int):
        """Set the tab width."""
        self.current_width = max(self.min_width, width)


class TabContainer(ctk.CTkFrame):
    """
    Container that manages multiple resizable tabs.
    Tabs are displayed side-by-side with resize handles.
    """

    def __init__(self, parent, on_layout_change: Optional[Callable] = None):
        super().__init__(parent, corner_radius=0, fg_color="transparent")

        self.on_layout_change = on_layout_change
        self.tabs: Dict[str, ResizableTab] = {}
        self.tab_order = []  # Track order of tabs

        # Grid configuration - tabs will be added to columns dynamically
        self.grid_rowconfigure(0, weight=1)

    def add_tab(self, tab_id: str, title: str, content_widget_factory: Callable,
                min_width: int = 200, default_width: int = 350) -> ctk.CTkFrame:
        """
        Add a new tab or return existing tab's content frame.

        Args:
            tab_id: Unique identifier for the tab
            title: Display title for the tab
            content_widget_factory: Function that creates the tab content widget
            min_width: Minimum width in pixels
            default_width: Default width in pixels

        Returns:
            Content frame where widgets should be placed
        """
        if tab_id in self.tabs:
            # Tab already exists, just return its content frame
            return self.tabs[tab_id].get_content_frame()

        # Create new tab
        tab = ResizableTab(
            self,
            tab_id=tab_id,
            title=title,
            on_close=self.remove_tab,
            on_resize=self._handle_resize,
            min_width=min_width,
            default_width=default_width
        )

        self.tabs[tab_id] = tab
        self.tab_order.append(tab_id)

        # Apply stored theme to new tab if available
        if hasattr(self, '_current_palette') and self._current_palette:
            tab.apply_theme(self._current_palette)

        # Create content using factory
        content_frame = tab.get_content_frame()
        content_widget = content_widget_factory(content_frame)

        if content_widget:
            content_widget.pack(fill="both", expand=True)

        # Re-layout all tabs
        self._layout_tabs()

        return content_frame

    def remove_tab(self, tab_id: str):
        """Remove a tab from the container."""
        if tab_id not in self.tabs:
            return

        tab = self.tabs[tab_id]
        tab.grid_forget()
        tab.destroy()

        del self.tabs[tab_id]
        self.tab_order.remove(tab_id)

        # Re-layout remaining tabs
        self._layout_tabs()

    def toggle_tab(self, tab_id: str, title: str, content_widget_factory: Callable,
                   min_width: int = 200, default_width: int = 350) -> bool:
        """
        Toggle a tab (add if not present, remove if present).

        Returns:
            True if tab is now open, False if closed
        """
        if tab_id in self.tabs:
            self.remove_tab(tab_id)
            return False
        else:
            self.add_tab(tab_id, title, content_widget_factory, min_width, default_width)
            return True

    def has_tab(self, tab_id: str) -> bool:
        """Check if a tab is currently open."""
        return tab_id in self.tabs

    def get_total_width(self) -> int:
        """Get total width of all tabs."""
        return sum(tab.current_width for tab in self.tabs.values())

    def _layout_tabs(self):
        """Re-layout all tabs in grid."""
        # Clear current layout
        for tab in self.tabs.values():
            tab.grid_forget()

        # CRITICAL FIX: Reset ALL column configurations to prevent ghost spacing
        # Clear more columns than we could ever have to ensure old configs are removed
        max_columns = 10
        for col in range(max_columns):
            self.grid_columnconfigure(col, minsize=0, weight=0)

        # Re-grid tabs in order with their configurations
        for col, tab_id in enumerate(self.tab_order):
            tab = self.tabs[tab_id]
            tab.grid(row=0, column=col, sticky=NSEW)

            # Configure column width based on tab's current width
            self.grid_columnconfigure(col, minsize=tab.current_width, weight=0)

        # If no tabs remain, ensure container collapses
        if not self.tabs:
            self.configure(width=1)

        # Notify parent of layout change
        if self.on_layout_change:
            self.on_layout_change()

    def _handle_resize(self):
        """Handle when a tab is resized."""
        self._layout_tabs()

    def get_tab_widths(self) -> Dict[str, int]:
        """Get current widths of all tabs."""
        return {tab_id: tab.current_width for tab_id, tab in self.tabs.items()}

    def restore_tab_widths(self, widths: Dict[str, int]):
        """Restore tab widths from saved state."""
        for tab_id, width in widths.items():
            if tab_id in self.tabs:
                self.tabs[tab_id].set_width(width)
        self._layout_tabs()

    def close_all_tabs(self):
        """Close all tabs."""
        for tab_id in list(self.tabs.keys()):
            self.remove_tab(tab_id)

    def apply_theme(self, palette: dict):
        """Apply theme colors and ornate styling to all tabs."""
        is_ornate = palette.get("ornate", False)
        border_color = palette.get("border", palette.get("accent", "#C4A574"))

        # Store palette for new tabs
        self._current_palette = palette

        # Configure container itself
        if is_ornate:
            self.configure(
                fg_color=palette.get("bg", "#1A0F24"),
                border_width=2,
                border_color=border_color
            )
        else:
            self.configure(fg_color="transparent", border_width=0)

        # Apply to all existing tabs
        for tab in self.tabs.values():
            tab.apply_theme(palette)


# Example usage in documentation:
"""
# In your main UI class:

def __init__(self):
    # ... existing setup ...

    # Create tab container between sidebar and output
    self.tab_container = TabContainer(
        self,
        on_layout_change=self._adjust_output_area
    )
    self.tab_container.grid(row=0, column=1, sticky=NSEW)

    # Adjust output area to column 2
    self.chat_log.grid(row=0, column=2, sticky=NSEW)

def open_settings_tab(self):
    # Toggle settings tab
    def create_settings_content(parent):
        # Create your settings widgets here
        frame = ctk.CTkFrame(parent)
        # ... add settings controls ...
        return frame

    self.tab_container.toggle_tab(
        "settings",
        "Settings",
        create_settings_content,
        min_width=250,
        default_width=350
    )

def _adjust_output_area(self):
    # Called when tabs change - adjust output area width
    total_tab_width = self.tab_container.get_total_width()
    # Grid will automatically handle the adjustment
    self.update_idletasks()
"""
