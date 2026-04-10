"""
Companion Manager Tab — Create, manage, and launch companion wrappers from the UI.

Add this to TabMethods class (tab_methods.py) or import as a mixin.
Provides a tab for:
  - Viewing all existing companions (scans Wrappers directory)
  - Creating new companions (launches setup wizard inline)
  - Quick-launching companions
  - Viewing companion status (has .env? persona configured? running?)

INTEGRATION:
  1. Copy this file into your wrapper directory
  2. Import in tab_methods.py: from companion_tab import CompanionTabMixin
  3. Add to TabMethods inheritance: class TabMethods(CompanionTabMixin):
  4. Add sidebar button in kay_ui.py pointing to self.toggle_companions_tab
  
  OR: Just paste toggle_companions_tab() into TabMethods directly.
"""

import os
import json
import subprocess
import sys
from pathlib import Path

try:
    import customtkinter as ctk
except ImportError:
    ctk = None


# Discover the Wrappers root from any wrapper directory
def get_wrappers_root():
    """Find D:/Wrappers/ (or equivalent) by walking up from current dir."""
    current = Path(os.path.dirname(os.path.abspath(__file__)))
    # We're inside a wrapper like D:/Wrappers/Kay/ — go up one level
    parent = current.parent
    # Verify this looks like the Wrappers root (has shared/ or multiple wrapper dirs)
    if (parent / "shared").exists() or (parent / "Template").exists():
        return parent
    # Fallback: try D:/Wrappers explicitly
    fallback = Path("D:/Wrappers")
    if fallback.exists():
        return fallback
    return parent  # Best guess


def scan_companions(wrappers_root: Path):
    """Scan for companion directories. Returns list of companion info dicts."""
    companions = []
    skip_dirs = {"shared", "resonant_core", "Template", "data", "docs",
                 "memory", "Graphics", "Music", "nexus", ".git", "__pycache__",
                 "ReedMemory"}

    for entry in sorted(wrappers_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name in skip_dirs:
            continue

        # Check if this looks like a wrapper (has main.py or persona/)
        has_main = (entry / "main.py").exists()
        has_persona_dir = (entry / "persona").exists()
        has_persona_config = (entry / "persona" / "persona_config.json").exists()
        has_env = (entry / ".env").exists()
        has_memory = (entry / "memory").exists()
        has_prompts = (
            (entry / "kay_prompts.py").exists() or
            (entry / "entity_prompts.py").exists() or
            has_persona_config
        )

        if not (has_main or has_persona_dir or has_prompts):
            continue

        # Try to load persona info
        info = {
            "name": entry.name,
            "display_name": entry.name,
            "path": str(entry),
            "has_env": has_env,
            "has_persona": has_persona_config,
            "has_memory": has_memory,
            "has_main": has_main,
            "configured": has_env and (has_prompts or has_persona_config),
            "is_template": entry.name == "Template",
            "entity_id": entry.name.lower(),
        }

        # Load persona details if available
        if has_persona_config:
            try:
                with open(entry / "persona" / "persona_config.json", 'r') as f:
                    pconfig = json.load(f)
                info["display_name"] = pconfig.get("entity", {}).get("display_name", entry.name)
                info["entity_id"] = pconfig.get("entity", {}).get("entity_id", entry.name.lower())
                pronouns = pconfig.get("entity", {}).get("pronouns", {})
                info["pronouns"] = f'{pronouns.get("subject", "they")}/{pronouns.get("object", "them")}'
            except Exception:
                pass

        companions.append(info)

    return companions


class CompanionTabMixin:
    """Mixin for TabMethods that adds a Companions tab."""

    def toggle_companions_tab(self):
        """Toggle the companion manager tab."""

        def create_companions_content(parent):
            frame = ctk.CTkScrollableFrame(parent)
            wrappers_root = get_wrappers_root()

            # === HEADER ===
            header = ctk.CTkLabel(
                frame, text="🐍 Companions",
                font=ctk.CTkFont(size=20, weight="bold")
            )
            header.pack(anchor="w", padx=20, pady=(20, 5))

            subtitle = ctk.CTkLabel(
                frame,
                text=f"Manage wrapper companions  •  {wrappers_root}",
                font=ctk.CTkFont(size=11), text_color="gray"
            )
            subtitle.pack(anchor="w", padx=20, pady=(0, 15))

            # === CREATE NEW SECTION ===
            create_frame = ctk.CTkFrame(frame, corner_radius=8)
            create_frame.pack(fill="x", padx=15, pady=(0, 15))

            create_label = ctk.CTkLabel(
                create_frame, text="Create New Companion",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            create_label.pack(anchor="w", padx=15, pady=(12, 5))

            # Name input row
            input_row = ctk.CTkFrame(create_frame, fg_color="transparent")
            input_row.pack(fill="x", padx=15, pady=(0, 10))

            name_entry = ctk.CTkEntry(
                input_row, placeholder_text="Companion name...",
                font=ctk.CTkFont(size=13), height=35, width=200
            )
            name_entry.pack(side="left", padx=(0, 8))

            def on_create():
                name = name_entry.get().strip()
                if not name:
                    status_label.configure(text="Enter a name first", text_color="orange")
                    return
                # Check if already exists
                target = wrappers_root / name
                if target.exists():
                    status_label.configure(text=f"{name} already exists!", text_color="red")
                    return

                status_label.configure(text=f"Creating {name}...", text_color="yellow")
                frame.update()

                try:
                    script = str(wrappers_root / "create_companion.py")
                    result = subprocess.run(
                        [sys.executable, script, name],
                        cwd=str(wrappers_root),
                        capture_output=True, text=True, timeout=60
                    )
                    if result.returncode == 0:
                        status_label.configure(
                            text=f"✓ {name} created! Run setup wizard to configure.",
                            text_color="green"
                        )
                        # Refresh the companion list
                        refresh_companion_list()
                    else:
                        err = result.stderr[:200] if result.stderr else "Unknown error"
                        status_label.configure(text=f"Error: {err}", text_color="red")
                except Exception as e:
                    status_label.configure(text=f"Error: {str(e)[:100]}", text_color="red")

            create_btn = ctk.CTkButton(
                input_row, text="Create", command=on_create,
                font=ctk.CTkFont(size=13), height=35, width=80
            )
            create_btn.pack(side="left", padx=(0, 8))

            status_label = ctk.CTkLabel(
                create_frame, text="", font=ctk.CTkFont(size=11),
                text_color="gray"
            )
            status_label.pack(anchor="w", padx=15, pady=(0, 10))

            # === COMPANION LIST ===
            list_header = ctk.CTkLabel(
                frame, text="Existing Companions",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            list_header.pack(anchor="w", padx=20, pady=(10, 8))

            # Container for companion cards (refreshable)
            list_container = ctk.CTkFrame(frame, fg_color="transparent")
            list_container.pack(fill="x", padx=10, pady=(0, 10))

            def build_companion_card(parent, info):
                """Build a single companion card widget."""
                card = ctk.CTkFrame(parent, corner_radius=8)
                card.pack(fill="x", padx=5, pady=4)

                # Top row: name + status indicators
                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=12, pady=(8, 2))

                # Name
                name_label = ctk.CTkLabel(
                    top_row, text=info["display_name"],
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w"
                )
                name_label.pack(side="left")

                # Status dots
                indicators = []
                if info["has_env"]:
                    indicators.append("🔑")  # Has API key
                if info["has_persona"]:
                    indicators.append("👤")  # Has persona config
                if info["has_memory"]:
                    indicators.append("🧠")  # Has memory
                if info["configured"]:
                    indicators.append("✓")

                status_text = " ".join(indicators) if indicators else "⚠️ Not configured"
                status_label_card = ctk.CTkLabel(
                    top_row, text=status_text,
                    font=ctk.CTkFont(size=12), text_color="gray"
                )
                status_label_card.pack(side="right")

                # Info row
                info_text = f"{info['entity_id']}"
                if info.get("pronouns"):
                    info_text += f"  •  {info['pronouns']}"
                info_label = ctk.CTkLabel(
                    card, text=info_text,
                    font=ctk.CTkFont(size=11), text_color="gray", anchor="w"
                )
                info_label.pack(anchor="w", padx=12, pady=(0, 4))

                # Button row
                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=12, pady=(0, 8))

                def launch_companion(path=info["path"]):
                    """Launch this companion in a new terminal."""
                    try:
                        launch_bat = os.path.join(path, "launch.bat")
                        main_py = os.path.join(path, "main.py")
                        if os.path.exists(launch_bat):
                            subprocess.Popen(
                                ["cmd", "/c", "start", launch_bat],
                                cwd=path
                            )
                        elif os.path.exists(main_py):
                            subprocess.Popen(
                                ["cmd", "/c", "start", "cmd", "/k",
                                 sys.executable, main_py],
                                cwd=path
                            )
                    except Exception as e:
                        print(f"[COMPANIONS] Launch error: {e}")

                def run_wizard(path=info["path"]):
                    """Run setup wizard for this companion."""
                    wizard = os.path.join(path, "setup_wizard.py")
                    if os.path.exists(wizard):
                        subprocess.Popen(
                            ["cmd", "/c", "start", "cmd", "/k",
                             sys.executable, wizard],
                            cwd=path
                        )

                def open_folder(path=info["path"]):
                    """Open companion folder in Explorer."""
                    os.startfile(path)

                # Only show Launch if configured
                if info["configured"] and not info["is_template"]:
                    launch_btn = ctk.CTkButton(
                        btn_row, text="▶ Launch", width=80, height=28,
                        font=ctk.CTkFont(size=11),
                        command=launch_companion
                    )
                    launch_btn.pack(side="left", padx=(0, 5))

                # Setup wizard button
                wizard_path = os.path.join(info["path"], "setup_wizard.py")
                if os.path.exists(wizard_path):
                    wizard_btn = ctk.CTkButton(
                        btn_row, text="🔧 Setup", width=80, height=28,
                        font=ctk.CTkFont(size=11),
                        fg_color="transparent", border_width=1,
                        command=run_wizard
                    )
                    wizard_btn.pack(side="left", padx=(0, 5))

                # Open folder button
                folder_btn = ctk.CTkButton(
                    btn_row, text="📁", width=35, height=28,
                    font=ctk.CTkFont(size=11),
                    fg_color="transparent", border_width=1,
                    command=open_folder
                )
                folder_btn.pack(side="left")

            def refresh_companion_list():
                """Rebuild the companion list."""
                # Clear existing cards
                for widget in list_container.winfo_children():
                    widget.destroy()

                companions = scan_companions(wrappers_root)
                if not companions:
                    empty = ctk.CTkLabel(
                        list_container,
                        text="No companions found. Create one above!",
                        font=ctk.CTkFont(size=12), text_color="gray"
                    )
                    empty.pack(pady=20)
                    return

                for comp in companions:
                    build_companion_card(list_container, comp)

            # Initial population
            refresh_companion_list()

            # Refresh button
            refresh_btn = ctk.CTkButton(
                frame, text="↻ Refresh", width=100, height=28,
                font=ctk.CTkFont(size=11),
                fg_color="transparent", border_width=1,
                command=refresh_companion_list
            )
            refresh_btn.pack(anchor="e", padx=20, pady=(5, 15))

            return frame

        # Register the tab
        is_open = self.tab_container.toggle_tab(
            "companions",
            "Companions",
            create_companions_content,
            min_width=300,
            default_width=420
        )

        # Update button appearance if we have a companions button
        if hasattr(self, 'companions_button'):
            if is_open:
                self.companions_button.configure(fg_color=("gray75", "gray25"))
            else:
                self.companions_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])
