"""
Tab Toggle Methods for Reed UI

Add these methods to your KayUI class to enable tab functionality.
These replace the popup window methods.
"""

import customtkinter as ctk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kay_ui import KayUI


# Palette definitions (copy from reed_ui.py if not accessible)
PALETTES = {
    "Cyan": {"bg": "#1a1a2e", "sidebar": "#0f3460", "output": "#16213e", "accent": "#00d9ff", "text": "#eaeaea"},
    "Green": {"bg": "#0d1b2a", "sidebar": "#1b263b", "output": "#1c2541", "accent": "#52b788", "text": "#e0e1dd"},
    # ... add other palettes as needed
}


class TabMethods:
    """Mixin class containing all tab toggle methods."""

    def toggle_settings_tab(self):
        """Toggle settings tab."""
        def create_settings_content(parent):
            frame = ctk.CTkScrollableFrame(parent)

            # Header
            header_label = ctk.CTkLabel(
                frame,
                text="⚙️ Settings",
                font=ctk.CTkFont(size=20, weight="bold")
            )
            header_label.pack(anchor="w", padx=20, pady=(20, 10))

            # Affect Section
            affect_section = ctk.CTkLabel(
                frame,
                text="Response Affect",
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w"
            )
            affect_section.pack(anchor="w", padx=20, pady=(15, 5), fill="x")

            affect_desc = ctk.CTkLabel(
                frame,
                text="Controls emotional intensity in responses (0-5)",
                font=ctk.CTkFont(size=12),
                text_color="gray",
                anchor="w"
            )
            affect_desc.pack(anchor="w", padx=20, pady=(0, 10), fill="x")

            affect_value_label = ctk.CTkLabel(
                frame,
                text=f"Current: {self.affect_var.get():.1f}",
                font=ctk.CTkFont(size=14)
            )
            affect_value_label.pack(anchor="w", padx=20, pady=(0, 5))

            def update_affect_label(value):
                affect_value_label.configure(text=f"Current: {float(value):.1f}")
                self._on_affect_change(value)

            affect_slider = ctk.CTkSlider(
                frame,
                from_=0.0,
                to=5.0,
                variable=self.affect_var,
                command=update_affect_label,
                width=300
            )
            affect_slider.pack(fill="x", padx=20, pady=(0, 20))

            # Palette Section
            palette_section = ctk.CTkLabel(
                frame,
                text="Color Palette",
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w"
            )
            palette_section.pack(anchor="w", padx=20, pady=(15, 5), fill="x")

            palette_desc = ctk.CTkLabel(
                frame,
                text="Choose UI color theme",
                font=ctk.CTkFont(size=12),
                text_color="gray",
                anchor="w"
            )
            palette_desc.pack(anchor="w", padx=20, pady=(0, 10), fill="x")

            # Get palettes from main file if possible
            try:
                from kay_ui import PALETTES
                palette_list = list(PALETTES.keys())
            except:
                palette_list = ["Cyan", "Green", "Hot Magenta", "Jewel", "Neon"]

            palette_menu = ctk.CTkOptionMenu(
                frame,
                values=palette_list,
                command=self.change_palette,
                font=ctk.CTkFont(size=14),
                width=300
            )
            palette_menu.set(self.palette_name)
            palette_menu.pack(fill="x", padx=20, pady=(0, 20))

            # Voice Settings (if available)
            if hasattr(self, 'voice_ui'):
                voice_section = ctk.CTkLabel(
                    frame,
                    text="Voice Settings",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    anchor="w"
                )
                voice_section.pack(anchor="w", padx=20, pady=(15, 5), fill="x")

                voice_enabled_var = ctk.BooleanVar(value=True)
                voice_checkbox = ctk.CTkCheckBox(
                    frame,
                    text="Enable voice input",
                    variable=voice_enabled_var,
                    font=ctk.CTkFont(size=14)
                )
                voice_checkbox.pack(anchor="w", padx=20, pady=5)

            return frame

        is_open = self.tab_container.toggle_tab(
            "settings",
            "Settings",
            create_settings_content,
            min_width=250,
            default_width=350
        )

        # Update button appearance
        if hasattr(self, 'settings_button'):
            if is_open:
                self.settings_button.configure(fg_color=("gray75", "gray25"))
            else:
                self.settings_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])

    def toggle_import_tab(self):
        """Toggle import memories tab."""
        def create_import_content(parent):
            # Check if ImportWindow supports embedded mode
            try:
                from import_window import ImportWindow

                # Try to create embedded version
                import_content = ImportWindow(
                    parent,
                    memory_engine=self.memory,
                    entity_graph=self.memory.entity_graph,
                    agent_state=self.agent_state,
                    affect_var=self.affect_var
                )
                return import_content
            except Exception as e:
                # Fallback: create simple message
                fallback_frame = ctk.CTkFrame(parent)
                error_label = ctk.CTkLabel(
                    fallback_frame,
                    text="Import feature requires popup mode.\nClick button again to use popup.",
                    font=ctk.CTkFont(size=14),
                    text_color="orange"
                )
                error_label.pack(expand=True, pady=50)

                open_popup_btn = ctk.CTkButton(
                    fallback_frame,
                    text="Open in Popup",
                    command=lambda: self._open_import_popup_fallback(),
                    font=ctk.CTkFont(size=14)
                )
                open_popup_btn.pack(pady=10)

                return fallback_frame

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
            try:
                from document_manager_ui import DocumentManagerWindow

                doc_manager = DocumentManagerWindow(
                    parent,
                    memory_engine=self.memory,
                    entity_graph=self.memory.entity_graph
                )
                return doc_manager
            except Exception as e:
                # Fallback
                fallback_frame = ctk.CTkFrame(parent)
                error_label = ctk.CTkLabel(
                    fallback_frame,
                    text="Document manager requires popup mode.\nClick button again to use popup.",
                    font=ctk.CTkFont(size=14),
                    text_color="orange"
                )
                error_label.pack(expand=True, pady=50)

                open_popup_btn = ctk.CTkButton(
                    fallback_frame,
                    text="Open in Popup",
                    command=lambda: self._open_document_popup_fallback(),
                    font=ctk.CTkFont(size=14)
                )
                open_popup_btn.pack(pady=10)

                return fallback_frame

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
            frame = ctk.CTkScrollableFrame(parent)

            # Header
            header_label = ctk.CTkLabel(
                frame,
                text="📚 Session Browser",
                font=ctk.CTkFont(size=20, weight="bold")
            )
            header_label.pack(anchor="w", padx=20, pady=(20, 10))

            desc_label = ctk.CTkLabel(
                frame,
                text="Browse and manage saved sessions",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            )
            desc_label.pack(anchor="w", padx=20, pady=(0, 20))

            # Session browser integration
            if hasattr(self, 'session_browser'):
                # Try to embed session browser UI
                try:
                    # This would require session_browser to support embedded mode
                    # For now, show available sessions as a list
                    import os
                    session_dir = "saved_sessions"

                    if os.path.exists(session_dir):
                        sessions = [f for f in os.listdir(session_dir) if f.endswith('.json')]

                        for session_file in sorted(sessions, reverse=True):
                            session_btn = ctk.CTkButton(
                                frame,
                                text=session_file.replace('.json', ''),
                                command=lambda sf=session_file: self._load_session_from_tab(sf),
                                font=ctk.CTkFont(size=14)
                            )
                            session_btn.pack(fill="x", padx=20, pady=5)
                    else:
                        no_sessions = ctk.CTkLabel(
                            frame,
                            text="No saved sessions found",
                            font=ctk.CTkFont(size=14),
                            text_color="gray"
                        )
                        no_sessions.pack(pady=30)

                except Exception as e:
                    error_label = ctk.CTkLabel(
                        frame,
                        text=f"Error loading sessions: {str(e)}",
                        font=ctk.CTkFont(size=12),
                        text_color="red"
                    )
                    error_label.pack(pady=20)

            # Fallback button to open full browser
            open_browser_btn = ctk.CTkButton(
                frame,
                text="Open Full Session Browser",
                command=lambda: self._open_session_browser_popup(),
                font=ctk.CTkFont(size=14)
            )
            open_browser_btn.pack(fill="x", padx=20, pady=(20, 10))

            return frame

        is_open = self.tab_container.toggle_tab(
            "sessions",
            "Sessions",
            create_sessions_content,
            min_width=400,
            default_width=450
        )

        # Update button appearance
        if is_open:
            self.browse_sessions_button.configure(fg_color=("gray75", "gray25"))
        else:
            self.browse_sessions_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])

    def toggle_stats_tab(self):
        """Toggle memory/emotion stats tab."""
        def create_stats_content(parent):
            frame = ctk.CTkScrollableFrame(parent)

            # Header
            header_label = ctk.CTkLabel(
                frame,
                text="📊 Stats & Info",
                font=ctk.CTkFont(size=20, weight="bold")
            )
            header_label.pack(anchor="w", padx=20, pady=(20, 10))

            # Memory Stats
            memory_section = ctk.CTkLabel(
                frame,
                text="Memory Statistics",
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w"
            )
            memory_section.pack(anchor="w", padx=20, pady=(15, 10), fill="x")

            if hasattr(self, 'memory'):
                # Get current memory stats
                stats_text = self._get_detailed_memory_stats()
                stats_label = ctk.CTkLabel(
                    frame,
                    text=stats_text,
                    font=ctk.CTkFont(size=13, family="Courier"),
                    justify="left",
                    anchor="w"
                )
                stats_label.pack(anchor="w", padx=20, pady=5, fill="x")

            # Emotion Stats
            emotion_section = ctk.CTkLabel(
                frame,
                text="Emotional State",
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w"
            )
            emotion_section.pack(anchor="w", padx=20, pady=(20, 10), fill="x")

            if hasattr(self, 'agent_state'):
                emotion_text = self._get_emotion_details()
                emotion_label = ctk.CTkLabel(
                    frame,
                    text=emotion_text,
                    font=ctk.CTkFont(size=13, family="Courier"),
                    justify="left",
                    anchor="w"
                )
                emotion_label.pack(anchor="w", padx=20, pady=5, fill="x")

            # Refresh button
            refresh_btn = ctk.CTkButton(
                frame,
                text="🔄 Refresh Stats",
                command=lambda: self._refresh_stats_tab(),
                font=ctk.CTkFont(size=14)
            )
            refresh_btn.pack(fill="x", padx=20, pady=20)

            return frame

        is_open = self.tab_container.toggle_tab(
            "stats",
            "Stats",
            create_stats_content,
            min_width=300,
            default_width=400
        )

    # Helper methods
    def _on_tabs_changed(self):
        """Called when tabs are opened/closed/resized."""
        if hasattr(self, 'tab_container'):
            self.tab_widths = self.tab_container.get_tab_widths()
            self.update_idletasks()

    def _load_session_from_tab(self, session_file):
        """Load a session from the sessions tab."""
        import json
        import os

        try:
            session_path = os.path.join("saved_sessions", session_file)
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Use existing load logic
            # This would call your existing session loading code
            self.load_session_data(session_data)

        except Exception as e:
            print(f"[ERROR] Failed to load session: {e}")

    def _open_session_browser_popup(self):
        """Fallback to open session browser as popup."""
        if hasattr(self, 'session_browser'):
            self.session_browser.open_browser()

    def _open_import_popup_fallback(self):
        """Fallback to open import window as popup."""
        self.tab_container.remove_tab("import")  # Close tab first
        self.open_import_window()  # Open original popup

    def _open_document_popup_fallback(self):
        """Fallback to open document manager as popup."""
        self.tab_container.remove_tab("documents")
        self.open_document_manager()

    def _get_detailed_memory_stats(self) -> str:
        """Get detailed memory statistics as formatted string."""
        if not hasattr(self, 'memory'):
            return "Memory engine not initialized"

        try:
            total = len(self.memory.memories)
            layers = ""

            if hasattr(self.memory, 'memory_layers'):
                working = len(self.memory.memory_layers.working_memory)
                episodic = len(self.memory.memory_layers.episodic_memory)
                semantic = len(self.memory.memory_layers.semantic_memory)

                layers = f"""
Working:   {working:4d} memories
Episodic:  {episodic:4d} memories
Semantic:  {semantic:4d} memories
                """.strip()

            return f"Total: {total} memories\n\n{layers}"

        except Exception as e:
            return f"Error: {str(e)}"

    def _get_emotion_details(self) -> str:
        """Get emotion details as formatted string."""
        if not hasattr(self, 'agent_state'):
            return "Agent state not initialized"

        try:
            cocktail = self.agent_state.emotional_cocktail

            if not cocktail:
                return "No active emotions"

            emotion_lines = []
            for emotion, data in sorted(cocktail.items(), key=lambda x: x[1].get('intensity', 0), reverse=True):
                intensity = data.get('intensity', 0)
                age = data.get('age', 0)
                emotion_lines.append(f"{emotion:12s} {intensity:4.2f} (age: {age})")

            return "\n".join(emotion_lines)

        except Exception as e:
            return f"Error: {str(e)}"

    def _refresh_stats_tab(self):
        """Refresh the stats tab content."""
        # Close and reopen to refresh
        if self.tab_container.has_tab("stats"):
            self.tab_container.remove_tab("stats")
            self.toggle_stats_tab()
