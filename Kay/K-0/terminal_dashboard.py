"""
Terminal Dashboard - Real-time System Log Display
Provides a collapsible bottom panel displaying organized log sections for Kay Zero's internal processes.
"""

import tkinter as tk
import customtkinter as ctk
from queue import Queue, Empty
from threading import Lock
import re
from datetime import datetime
from typing import Dict, Optional


class LogSection:
    """Individual log section with auto-scroll and color-coded output."""

    def __init__(self, parent, section_name: str, palette: dict, max_lines: int = 1000):
        self.section_name = section_name
        self.palette = palette
        self.max_lines = max_lines
        self.visible = True
        self.pinned = False
        self.line_count = 0

        # Section container
        self.container = ctk.CTkFrame(parent, fg_color=palette["panel"],
                                     corner_radius=0, border_width=1,
                                     border_color=palette["muted"])

        # Header bar
        self.header = ctk.CTkFrame(self.container, fg_color=palette["input"],
                                  corner_radius=0, height=30)
        self.header.pack(fill="x", padx=0, pady=0)
        self.header.pack_propagate(False)

        # Section title
        self.title_label = ctk.CTkLabel(self.header,
                                       text=f"▼ {section_name}",
                                       font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                                       text_color=palette["accent_hi"])
        self.title_label.pack(side="left", padx=10, pady=5)

        # Pin button
        self.pin_btn = ctk.CTkButton(self.header, text="📌", width=30, height=20,
                                    font=ctk.CTkFont(size=12),
                                    fg_color="transparent",
                                    hover_color=palette["accent"],
                                    command=self.toggle_pin)
        self.pin_btn.pack(side="right", padx=5, pady=5)

        # Toggle button
        self.toggle_btn = ctk.CTkButton(self.header, text="Hide", width=50, height=20,
                                       font=ctk.CTkFont(family="Courier", size=9),
                                       fg_color=palette["button"],
                                       hover_color=palette["accent"],
                                       command=self.toggle_visibility)
        self.toggle_btn.pack(side="right", padx=5, pady=5)

        # Clear button
        self.clear_btn = ctk.CTkButton(self.header, text="Clear", width=50, height=20,
                                      font=ctk.CTkFont(family="Courier", size=9),
                                      fg_color=palette["button"],
                                      hover_color=palette["user"],
                                      command=self.clear)
        self.clear_btn.pack(side="right", padx=5, pady=5)

        # Log display area (scrollable textbox)
        self.log_text = ctk.CTkTextbox(self.container, wrap="none",
                                      font=ctk.CTkFont(family="Courier", size=9),
                                      fg_color=palette["bg"],
                                      text_color=palette["text"],
                                      border_width=0,
                                      height=150)
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

        # Configure color tags for log levels
        self._setup_color_tags()

    def _setup_color_tags(self):
        """Configure text tags for color-coded log levels."""
        # Log level colors
        self.log_text.tag_config("INFO", foreground="#6BB6B6")  # Light blue/cyan
        self.log_text.tag_config("WARNING", foreground="#FFB84D")  # Yellow/orange
        self.log_text.tag_config("ERROR", foreground="#FF6B6B")  # Red
        self.log_text.tag_config("DEBUG", foreground="#B794F6")  # Purple/magenta
        self.log_text.tag_config("PERF_GOOD", foreground="#51CF66")  # Green
        self.log_text.tag_config("PERF_SLOW", foreground="#FFB84D")  # Orange
        self.log_text.tag_config("PERF_BAD", foreground="#FF6B6B")  # Red
        self.log_text.tag_config("SYSTEM", foreground="#C4A574")  # Gold

        # Identity tracking colors (NEW)
        self.log_text.tag_config("IDENTITY_VERIFIED", foreground="#51CF66")  # Green - verified self-report
        self.log_text.tag_config("IDENTITY_FICTIONAL", foreground="#FFB84D")  # Orange - document/fictional content
        self.log_text.tag_config("IDENTITY_REJECTED", foreground="#FF6B6B")  # Red - rejected source mismatch
        self.log_text.tag_config("IDENTITY_ARCH", foreground="#C4A574")  # Gold - architectural fact

        # Environmental sound colors
        self.log_text.tag_config("SOUND_DETECTED", foreground="#51CF66")  # Green - sound detected
        self.log_text.tag_config("SOUND_CLAP", foreground="#FF9F43")  # Orange - percussive
        self.log_text.tag_config("SOUND_KNOCK", foreground="#54A0FF")  # Blue - knock/tap
        self.log_text.tag_config("SOUND_AMBIENT", foreground="#B794F6")  # Purple - ambient/other

    def toggle_visibility(self):
        """Toggle section visibility."""
        if self.visible:
            self.log_text.pack_forget()
            self.title_label.configure(text=f"▶ {self.section_name}")
            self.toggle_btn.configure(text="Show")
            self.visible = False
        else:
            self.log_text.pack(fill="both", expand=True, padx=2, pady=2)
            self.title_label.configure(text=f"▼ {self.section_name}")
            self.toggle_btn.configure(text="Hide")
            self.visible = True

    def toggle_pin(self):
        """Toggle pin state."""
        self.pinned = not self.pinned
        self.pin_btn.configure(text="📍" if self.pinned else "📌")

    def clear(self):
        """Clear log content."""
        self.log_text.delete("1.0", "end")
        self.line_count = 0

    def add_log(self, message: str, log_level: str = "INFO"):
        """Add log message with color coding."""
        # Trim old lines if over limit
        if self.line_count >= self.max_lines:
            self.log_text.delete("1.0", "2.0")
            self.line_count -= 1

        # Insert message with appropriate color tag
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"

        self.log_text.insert("end", formatted_msg, log_level)
        self.log_text.see("end")  # Auto-scroll to bottom
        self.line_count += 1


class TerminalDashboard:
    """
    Collapsible terminal dashboard displaying real-time system logs.

    Features:
    - Bottom-sliding panel (like browser dev tools)
    - Multiple organized log sections
    - Thread-safe log message queue
    - Color-coded log levels
    - Section visibility toggles and pinning
    """

    def __init__(self, parent, palette: dict, max_section_lines: int = 1000):
        self.parent = parent
        self.palette = palette
        self.max_section_lines = max_section_lines

        # State
        self.is_open = False
        self.log_queue = Queue()
        self.queue_lock = Lock()
        self.sections: Dict[str, LogSection] = {}

        # Stats tracking
        self.stats = {
            "warnings": 0,
            "errors": 0,
            "total_logs": 0
        }

        # Build UI
        self._build_dashboard()

        # Start queue processing
        self._process_log_queue()

    def _build_dashboard(self):
        """Build the dashboard UI structure."""
        # Main container (initially hidden)
        self.container = ctk.CTkFrame(self.parent, fg_color=self.palette["bg"],
                                     corner_radius=0, border_width=2,
                                     border_color=self.palette["accent"])

        # Always-visible header bar
        self.header_bar = ctk.CTkFrame(self.container, fg_color=self.palette["panel"],
                                      corner_radius=0, height=35)
        self.header_bar.pack(fill="x", padx=0, pady=0)
        self.header_bar.pack_propagate(False)

        # Toggle button (left side)
        self.toggle_btn = ctk.CTkButton(self.header_bar,
                                       text="▲ TERMINAL DASHBOARD",
                                       font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
                                       fg_color=self.palette["accent"],
                                       hover_color=self.palette["accent_hi"],
                                       text_color=self.palette["text"],
                                       corner_radius=0,
                                       width=200, height=28,
                                       command=self.toggle_dashboard)
        self.toggle_btn.pack(side="left", padx=10, pady=3)

        # Stats display (center)
        self.stats_label = ctk.CTkLabel(self.header_bar,
                                       text="● 0 warnings  ● 0 errors",
                                       font=ctk.CTkFont(family="Courier", size=9),
                                       text_color=self.palette["muted"])
        self.stats_label.pack(side="left", padx=20, pady=3)

        # Section visibility controls (right side)
        controls_frame = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        controls_frame.pack(side="right", padx=10, pady=3)

        # Show All / Hide All buttons
        ctk.CTkButton(controls_frame, text="Show All", width=70, height=22,
                     font=ctk.CTkFont(family="Courier", size=9),
                     fg_color=self.palette["button"],
                     hover_color=self.palette["accent"],
                     command=self.show_all_sections).pack(side="left", padx=2)

        ctk.CTkButton(controls_frame, text="Hide All", width=70, height=22,
                     font=ctk.CTkFont(family="Courier", size=9),
                     fg_color=self.palette["button"],
                     hover_color=self.palette["accent"],
                     command=self.hide_all_sections).pack(side="left", padx=2)

        ctk.CTkButton(controls_frame, text="Clear All", width=70, height=22,
                     font=ctk.CTkFont(family="Courier", size=9),
                     fg_color=self.palette["button"],
                     hover_color=self.palette["user"],
                     command=self.clear_all_sections).pack(side="left", padx=2)

        # Scrollable content area (hidden initially)
        self.content_area = ctk.CTkScrollableFrame(self.container,
                                                   fg_color=self.palette["bg"],
                                                   scrollbar_button_color=self.palette["accent"],
                                                   scrollbar_button_hover_color=self.palette["accent_hi"],
                                                   height=400)

        # Create log sections
        self._create_log_sections()

    def _create_log_sections(self):
        """Create all log sections."""
        section_names = [
            "Memory Operations",
            "Emotional State",
            "Entity Graph",
            "Identity Tracking",  # Kay's identity vs fictional knowledge
            "Environmental Sounds",  # Detected non-speech sounds (claps, knocks, etc.)
            "Glyph Compression",
            "Emergence Metrics",
            "System Status"
        ]

        for section_name in section_names:
            section = LogSection(self.content_area, section_name, self.palette, self.max_section_lines)
            section.container.pack(fill="both", expand=True, padx=5, pady=3)
            self.sections[section_name] = section

    def toggle_dashboard(self):
        """Toggle dashboard open/closed."""
        if self.is_open:
            self.close_dashboard()
        else:
            self.open_dashboard()

    def open_dashboard(self):
        """Expand dashboard."""
        if not self.is_open:
            self.content_area.pack(fill="both", expand=True, padx=5, pady=5)
            self.toggle_btn.configure(text="▼ TERMINAL DASHBOARD")
            self.is_open = True

    def close_dashboard(self):
        """Collapse dashboard."""
        if self.is_open:
            self.content_area.pack_forget()
            self.toggle_btn.configure(text="▲ TERMINAL DASHBOARD")
            self.is_open = False

    def show_all_sections(self):
        """Show all log sections."""
        for section in self.sections.values():
            if not section.visible and not section.pinned:
                section.toggle_visibility()

    def hide_all_sections(self):
        """Hide all unpinned log sections."""
        for section in self.sections.values():
            if section.visible and not section.pinned:
                section.toggle_visibility()

    def clear_all_sections(self):
        """Clear all log sections."""
        for section in self.sections.values():
            section.clear()
        self.stats["warnings"] = 0
        self.stats["errors"] = 0
        self.stats["total_logs"] = 0
        self._update_stats_display()

    def log(self, message: str, section: str = "System Status", level: str = "INFO"):
        """
        Add log message to queue (thread-safe).

        Args:
            message: Log message text
            section: Section name to route to
            level: Log level (INFO, WARNING, ERROR, DEBUG, PERF_GOOD, PERF_SLOW, PERF_BAD, SYSTEM)
        """
        with self.queue_lock:
            self.log_queue.put((message, section, level))

    def _process_log_queue(self):
        """Process queued log messages (runs periodically)."""
        try:
            # Process up to 50 messages per cycle to avoid UI freezing
            for _ in range(50):
                try:
                    message, section, level = self.log_queue.get_nowait()
                    self._add_log_to_section(message, section, level)
                except Empty:
                    break
        except Exception as e:
            print(f"[DASHBOARD ERROR] Queue processing failed: {e}")

        # Schedule next processing cycle
        self.parent.after(100, self._process_log_queue)

    def _add_log_to_section(self, message: str, section_name: str, level: str):
        """Add log message to appropriate section."""
        # Update stats
        self.stats["total_logs"] += 1
        if level == "WARNING":
            self.stats["warnings"] += 1
        elif level == "ERROR":
            self.stats["errors"] += 1

        self._update_stats_display()

        # Route to section
        if section_name in self.sections:
            self.sections[section_name].add_log(message, level)
        else:
            # Default to System Status if section not found
            self.sections["System Status"].add_log(message, level)

    def _update_stats_display(self):
        """Update stats label in header."""
        self.stats_label.configure(
            text=f"● {self.stats['warnings']} warnings  ● {self.stats['errors']} errors  ● {self.stats['total_logs']} total"
        )

    def parse_and_route_log(self, log_line: str):
        """
        Parse terminal log line and route to appropriate section.

        Example formats:
        [MEMORY 2-TIER] SEMANTIC extracted_fact: ...
        [EMOTION STATE] ========== CURRENT EMOTIONAL COCKTAIL ==========
        [ENTITY GRAPH] NEW CONTRADICTIONS DETECTED (1 new, 763 total active)
        [PERF] memory_multi_factor: 354.2ms [SLOW] (target: 150ms)
        [LLM] Anthropic client initialized with model claude-sonnet-4-20250514
        """
        # Extract tag and content
        tag_match = re.match(r'^\[([^\]]+)\]\s*(.*)', log_line)
        if not tag_match:
            # No tag - route to System Status
            self.log(log_line, "System Status", "INFO")
            return

        tag = tag_match.group(1)
        content = tag_match.group(2)

        # Determine section and level
        section, level = self._classify_log(tag, content)

        # Log to appropriate section
        self.log(content, section, level)

    def _classify_log(self, tag: str, content: str) -> tuple:
        """Classify log line to determine section and level."""
        tag_upper = tag.upper()
        content_upper = content.upper()

        # Identity Tracking (NEW - check first for priority routing)
        if any(kw in tag_upper for kw in ["IDENTITY", "IDENTITY SKIP", "IDENTITY VERIFIED",
                                           "IDENTITY FICTIONAL", "IDENTITY REJECTED"]):
            # Determine identity-specific level
            if "SKIP" in tag_upper or "FICTIONAL" in content_upper or "DOCUMENT" in content_upper:
                level = "IDENTITY_FICTIONAL"  # Document/fictional content (orange)
            elif "REJECT" in tag_upper or "MISMATCH" in content_upper:
                level = "IDENTITY_REJECTED"  # Rejected source (red)
            elif "ARCH" in content_upper or "ARCHITECTURAL" in content_upper:
                level = "IDENTITY_ARCH"  # Architectural fact (gold)
            elif "SELF_REPORT" in content_upper or "VERIFIED" in content_upper:
                level = "IDENTITY_VERIFIED"  # Self-report verified (green)
            else:
                # Default: determine by source in content
                if "source: user" in content.lower() or "self_report" in content.lower():
                    level = "IDENTITY_VERIFIED"
                elif "source: document" in content.lower() or "document_content" in content.lower():
                    level = "IDENTITY_FICTIONAL"
                elif "source: unknown" in content.lower():
                    level = "WARNING"  # Unknown source should be warning
                else:
                    level = "INFO"
            return ("Identity Tracking", level)

        # Contradiction detection - route to Entity Graph
        if any(kw in tag_upper for kw in ["CONTRADICTION FLAGGED", "CONTRADICTION BLOCKED",
                                           "MEMORY CONTRADICTION"]):
            level = "WARNING"  # Contradictions are always warnings, not errors
            return ("Entity Graph", level)

        # Environmental Sounds (claps, knocks, footsteps, etc.)
        if "ENVIRONMENTAL" in tag_upper:
            # Classify by sound type for color-coding
            content_lower = content.lower()
            if "detected" in content_lower:
                if "clap" in content_lower or "door" in content_lower:
                    level = "SOUND_CLAP"  # Percussive sounds - orange
                elif "knock" in content_lower or "tap" in content_lower:
                    level = "SOUND_KNOCK"  # Knock/tap sounds - blue
                elif "footstep" in content_lower:
                    level = "SOUND_AMBIENT"  # Ambient sounds - purple
                else:
                    level = "SOUND_DETECTED"  # Generic detected - green
            else:
                level = "INFO"
            return ("Environmental Sounds", level)

        # Memory Operations
        if any(kw in tag_upper for kw in ["MEMORY", "RECALL", "STORE", "LAYER"]):
            level = "ERROR" if "ERROR" in content_upper or "FAIL" in content_upper else "INFO"
            return ("Memory Operations", level)

        # Emotional State
        if any(kw in tag_upper for kw in ["EMOTION", "FEELING", "ULTRAMAP", "COCKTAIL"]):
            level = "INFO"
            return ("Emotional State", level)

        # Entity Graph
        if any(kw in tag_upper for kw in ["ENTITY", "GRAPH", "CONTRADICTION", "RELATIONSHIP"]):
            level = "WARNING" if "CONTRADICTION" in content_upper else "INFO"
            return ("Entity Graph", level)

        # Glyph Compression
        if any(kw in tag_upper for kw in ["GLYPH", "COMPRESS", "SYMBOLIC", "ENCODE"]):
            level = "DEBUG"
            return ("Glyph Compression", level)

        # Emergence Metrics
        if any(kw in tag_upper for kw in ["E-SCORE", "EMERGENCE", "SYNTHESIS", "NOVELTY"]):
            level = "INFO"
            return ("Emergence Metrics", level)

        # Performance
        if "PERF" in tag_upper:
            if "[SLOW]" in content or "[BAD]" in content:
                level = "PERF_SLOW"
            elif "[GOOD]" in content or "[OK]" in content:
                level = "PERF_GOOD"
            else:
                level = "INFO"
            return ("System Status", level)

        # System/LLM/Errors
        if any(kw in tag_upper for kw in ["ERROR", "FAIL", "EXCEPTION"]):
            return ("System Status", "ERROR")
        elif "WARNING" in tag_upper or "WARN" in tag_upper:
            return ("System Status", "WARNING")
        elif "DEBUG" in tag_upper:
            return ("System Status", "DEBUG")
        else:
            return ("System Status", "INFO")

    def pack(self, **kwargs):
        """Pack dashboard into parent."""
        self.container.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid dashboard into parent."""
        self.container.grid(**kwargs)
