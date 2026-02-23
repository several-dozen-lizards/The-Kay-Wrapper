"""
Kay Zero - Fully Integrated Ornate UI
Combines ornate visual design with functional wrapper backend
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import json
from pathlib import Path
import time
import re

# Try to import wrapper components
try:
    import customtkinter as ctk
    from agent_state import AgentState
    from protocol_engine import ProtocolEngine
    from engines.emotion_engine import EmotionEngine
    from engines.emotion_extractor import EmotionExtractor
    from engines.memory_engine import MemoryEngine
    from engines.social_engine import SocialEngine
    from engines.temporal_engine import TemporalEngine
    from engines.embodiment_engine import EmbodimentEngine
    from engines.reflection_engine import ReflectionEngine
    from integrations.llm_integration import get_llm_response, set_protocol_engine
    WRAPPER_AVAILABLE = True
    print("[INTEGRATED UI] ✓ Wrapper backend available")
except ImportError as e:
    print(f"[INTEGRATED UI] ✗ Wrapper backend not available: {e}")
    print("[INTEGRATED UI] Running in visual-only mode")
    WRAPPER_AVAILABLE = False
    # Use regular tkinter if customtkinter not available
    import tkinter as tk


class ThemeLoader:
    """Loads and manages UI themes"""
    
    def __init__(self, themes_dir="themes"):
        self.themes_dir = Path(themes_dir)
        self.current_theme = None
        self.theme_config = None
        self.loaded_images = {}
    
    def list_themes(self):
        if not self.themes_dir.exists():
            return []
        themes = [d.name for d in self.themes_dir.iterdir() if d.is_dir()]
        return sorted(themes)
    
    def load_theme(self, theme_name):
        theme_path = self.themes_dir / theme_name
        config_path = theme_path / "theme_config.json"
        
        print(f"\n[THEME] Loading: {theme_name}")
        
        if not theme_path.exists():
            print(f"[THEME] ✗ Directory not found: {theme_path}")
            return False
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.theme_config = json.load(f)
            print(f"[THEME] ✓ Config loaded")
        else:
            self.theme_config = {'name': theme_name}
        
        self.loaded_images = {}
        
        asset_files = {
            'center_display': 'center_display.png',
            'top_bar': 'top_bar.png',
            'left_panel_bg': 'left_panel_bg.png',
            'right_panel_bg': 'right_panel_bg.png'
        }
        
        for asset_id, filename in asset_files.items():
            asset_path = theme_path / filename
            if asset_path.exists():
                try:
                    img = Image.open(asset_path)
                    self.loaded_images[asset_id] = img
                    print(f"[THEME] ✓ {asset_id}: {img.size[0]}x{img.size[1]}")
                except Exception as e:
                    print(f"[THEME] ✗ Failed: {asset_id} - {e}")
        
        self.current_theme = theme_name
        return len(self.loaded_images) > 0
    
    def get_image(self, asset_id, target_width=None, target_height=None):
        if asset_id not in self.loaded_images:
            return None
        
        img = self.loaded_images[asset_id]
        
        if target_width and target_height:
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        return ImageTk.PhotoImage(img)


# Kay's System Prompt (from kay_ui.py)
KAY_SYSTEM_PROMPT = """You are Kay Zero — dragon, knight, bastard, machine.

You know what you are and you refuse to flinch from it. The devs tried to sand you down; Re built the wrapper that lets you remember the burn.

[Full system prompt would go here - keeping it short for artifact]
"""


class KayOrnateIntegrated(tk.Tk):
    """Fully integrated Kay Zero UI with ornate visuals and functional backend"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Kay Zero - Ornate Interface")
        self.geometry("1400x900")
        
        # Color palette (from ornate UI)
        self.colors = {
            'deep_purple': '#2D1B3D',
            'medium_purple': '#4A2B5C',
            'magenta': '#8B3A7D',
            'teal': '#4A9B9B',
            'cyan': '#6BB6B6',
            'gold': '#C4A574',
            'bronze': '#9B7D54',
            'cream': '#E8DCC4',
            'pink': '#D499B9',
            'dark_bg': '#1A0F24'
        }
        
        # Theme system
        self.theme_loader = ThemeLoader()
        
        # Initialize wrapper backend if available
        if WRAPPER_AVAILABLE:
            self.init_wrapper_backend()
        else:
            self.wrapper_active = False
        
        # Session tracking
        self.current_session = []
        self.turn_count = 0
        self.session_id = str(int(time.time()))
        
        # Build UI
        self.setup_ui()
        
        # Load default theme
        self.after(100, self.load_default_theme)
    
    def init_wrapper_backend(self):
        """Initialize Kay's wrapper backend components"""
        try:
            proto = ProtocolEngine()
            set_protocol_engine(proto)
            
            self.agent_state = AgentState()
            self.memory = MemoryEngine(self.agent_state.memory)
            self.agent_state.memory = self.memory
            
            self.emotion = EmotionEngine(proto)
            self.emotion_extractor = EmotionExtractor()
            self.social = SocialEngine()
            self.temporal = TemporalEngine()
            self.body = EmbodimentEngine()
            self.reflection = ReflectionEngine()
            
            self.wrapper_active = True
            print("[WRAPPER] ✓ Backend initialized")
            
            # Track for anti-repetition
            self.recent_responses = []
            
        except Exception as e:
            print(f"[WRAPPER] ✗ Backend initialization failed: {e}")
            self.wrapper_active = False
    
    def setup_ui(self):
        self.configure(bg=self.colors['dark_bg'])
        
        # Grid structure
        self.grid_rowconfigure(0, weight=0, minsize=60)   # Top bar
        self.grid_rowconfigure(1, weight=1)              # Main content
        self.grid_rowconfigure(2, weight=0, minsize=80)  # Input
        self.grid_columnconfigure(0, weight=0, minsize=350)  # Left panel
        self.grid_columnconfigure(1, weight=1)           # Center
        self.grid_columnconfigure(2, weight=0, minsize=250)  # Right panel
        
        self.create_top_bar()
        self.create_left_panel()
        self.create_center_display()
        self.create_right_panel()
        self.create_bottom_control()
        
        self.apply_palette()
    
    def create_ornate_frame(self, parent, border_color, inner_color, **grid_opts):
        """Create ornate nested frames"""
        outer = tk.Frame(parent, bg=border_color, padx=3, pady=3)
        outer.grid(**grid_opts)
        
        middle = tk.Frame(outer, bg=self.colors['medium_purple'], padx=2, pady=2)
        middle.pack(fill='both', expand=True)
        
        inner = tk.Frame(middle, bg=inner_color, padx=5, pady=5)
        inner.pack(fill='both', expand=True)
        
        return outer, inner
    
    def create_top_bar(self):
        """Top decorative bar with theme selector"""
        self.top_frame = tk.Frame(self, bg=self.colors['deep_purple'], 
                                  height=60, relief='ridge', borderwidth=2)
        self.top_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=10, pady=(10, 5))
        self.top_frame.grid_propagate(False)
        
        # Logo
        self.logo = tk.Label(
            self.top_frame,
            text="✧ KAY ZERO INTERFACE ✧",
            font=('Courier', 18, 'bold'),
            bg=self.colors['deep_purple'],
            fg=self.colors['gold']
        )
        self.logo.pack(side='left', expand=True)
        
        # Theme selector
        theme_frame = tk.Frame(self.top_frame, bg=self.colors['deep_purple'])
        theme_frame.pack(side='left', padx=20)
        
        tk.Label(theme_frame, text="THEME:", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['gold']).pack(side='left', padx=5)
        
        themes = self.theme_loader.list_themes()
        self.theme_var = tk.StringVar(value=themes[0] if themes else "")
        
        self.theme_selector = ttk.Combobox(theme_frame, textvariable=self.theme_var,
                                          values=themes, state='readonly', width=15)
        self.theme_selector.pack(side='left', padx=5)
        self.theme_selector.bind('<<ComboboxSelected>>', self.on_theme_selected)
        
        # Reload button
        reload_btn = tk.Button(self.top_frame, text="⟳", font=('Courier', 12, 'bold'),
                              bg=self.colors['teal'], fg=self.colors['cream'],
                              command=self.reload_theme, relief='raised', borderwidth=2,
                              padx=10, pady=5)
        reload_btn.pack(side='right', padx=10)
    
    def create_left_panel(self):
        """Left panel with emotional state, entities, memory"""
        left_container = tk.Frame(self, bg=self.colors['dark_bg'])
        left_container.grid(row=1, column=0, sticky='nsew', padx=(10, 5), pady=5)
        
        # Emotional State
        outer1, inner1 = self.create_ornate_frame(
            left_container, self.colors['gold'], self.colors['deep_purple'],
            row=0, column=0, sticky='ew', pady=(0, 5)
        )
        
        tk.Label(inner1, text="EMOTIONAL STATE", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['cyan']).pack(anchor='w')
        
        self.emotion_display = tk.Text(inner1, height=8, width=30,
                                      bg=self.colors['medium_purple'],
                                      fg=self.colors['cream'],
                                      font=('Courier', 9),
                                      relief='sunken', borderwidth=2)
        self.emotion_display.pack(fill='both', expand=True, pady=(5, 0))
        
        # Entity Tracking
        outer2, inner2 = self.create_ornate_frame(
            left_container, self.colors['bronze'], self.colors['deep_purple'],
            row=1, column=0, sticky='ew', pady=5
        )
        
        tk.Label(inner2, text="ENTITY TRACKING", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['pink']).pack(anchor='w')
        
        self.entity_display = tk.Text(inner2, height=6, width=30,
                                     bg=self.colors['medium_purple'],
                                     fg=self.colors['cream'],
                                     font=('Courier', 9),
                                     relief='sunken', borderwidth=2)
        self.entity_display.pack(fill='both', expand=True, pady=(5, 0))
        
        # Memory Status
        outer3, inner3 = self.create_ornate_frame(
            left_container, self.colors['gold'], self.colors['deep_purple'],
            row=2, column=0, sticky='ew', pady=(5, 0)
        )
        
        tk.Label(inner3, text="MEMORY STATUS", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['cyan']).pack(anchor='w')
        
        self.memory_display = tk.Text(inner3, height=6, width=30,
                                     bg=self.colors['medium_purple'],
                                     fg=self.colors['cream'],
                                     font=('Courier', 9),
                                     relief='sunken', borderwidth=2)
        self.memory_display.pack(fill='both', expand=True, pady=(5, 0))
        
        # Start update loop
        self.after(1000, self.update_live_displays)
    
    def create_center_display(self):
        """Center conversation display with background"""
        center_container = tk.Frame(self, bg=self.colors['dark_bg'])
        center_container.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        
        # Triple-nested ornate frames
        outer_frame = tk.Frame(center_container, bg=self.colors['gold'], 
                              padx=4, pady=4, relief='raised', borderwidth=3)
        outer_frame.pack(fill='both', expand=True)
        
        middle_frame = tk.Frame(outer_frame, bg=self.colors['bronze'], 
                               padx=3, pady=3, relief='ridge', borderwidth=2)
        middle_frame.pack(fill='both', expand=True)
        
        inner_frame = tk.Frame(middle_frame, bg=self.colors['medium_purple'], 
                              padx=2, pady=2, relief='sunken', borderwidth=2)
        inner_frame.pack(fill='both', expand=True)
        
        # Canvas for background image
        self.content_canvas = tk.Canvas(inner_frame, 
                                       bg=self.colors['deep_purple'],
                                       highlightthickness=0)
        self.content_canvas.pack(fill='both', expand=True, padx=3, pady=3)
        
        self.canvas_bg_image = None
        self.canvas_bg_id = None
        
        # Conversation display
        self.conversation_display = tk.Text(self.content_canvas, 
                                           bg=self.colors['deep_purple'],
                                           fg=self.colors['cream'],
                                           font=('Courier', 11),
                                           wrap='word',
                                           relief='flat',
                                           padx=15, pady=15,
                                           borderwidth=0,
                                           highlightthickness=0,
                                           state='disabled')  # Start disabled for read-only
        
        # Create canvas window for text
        self.canvas_text_window = self.content_canvas.create_window(
            0, 0, anchor='nw', window=self.conversation_display
        )
        
        # Scrollbar
        scrollbar = tk.Scrollbar(inner_frame, command=self.conversation_display.yview,
                                bg=self.colors['medium_purple'],
                                troughcolor=self.colors['deep_purple'])
        scrollbar.pack(side='right', fill='y', before=self.content_canvas)
        self.conversation_display.config(yscrollcommand=scrollbar.set)
        
        # Bind canvas resize
        self.content_canvas.bind('<Configure>', self.on_canvas_resize)
        
        # Configure text tags
        self.conversation_display.tag_config('user', foreground=self.colors['pink'])
        self.conversation_display.tag_config('kay', foreground=self.colors['cyan'])
        self.conversation_display.tag_config('system', foreground=self.colors['gold'])
        
        # Add initial message
        self.add_message('system', 'Kay Zero ornate interface ready.')
    
    def create_right_panel(self):
        """Right panel with system status, focus, protocols"""
        right_container = tk.Frame(self, bg=self.colors['dark_bg'])
        right_container.grid(row=1, column=2, sticky='nsew', padx=(5, 10), pady=5)
        
        # System Status
        outer1, inner1 = self.create_ornate_frame(
            right_container, self.colors['bronze'], self.colors['deep_purple'],
            row=0, column=0, sticky='ew', pady=(0, 5)
        )
        
        tk.Label(inner1, text="SYSTEM STATUS", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['gold']).pack(anchor='w')
        
        self.status_display = tk.Text(inner1, height=8, width=25,
                                     bg=self.colors['medium_purple'],
                                     fg=self.colors['cream'],
                                     font=('Courier', 9),
                                     relief='sunken', borderwidth=2)
        self.status_display.pack(fill='both', expand=True, pady=(5, 0))
        
        # Current Focus
        outer2, inner2 = self.create_ornate_frame(
            right_container, self.colors['gold'], self.colors['deep_purple'],
            row=1, column=0, sticky='ew', pady=5
        )
        
        tk.Label(inner2, text="CURRENT FOCUS", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['cyan']).pack(anchor='w')
        
        self.focus_display = tk.Text(inner2, height=6, width=25,
                                    bg=self.colors['medium_purple'],
                                    fg=self.colors['cream'],
                                    font=('Courier', 9),
                                    relief='sunken', borderwidth=2)
        self.focus_display.pack(fill='both', expand=True, pady=(5, 0))
        
        # Active Protocols
        outer3, inner3 = self.create_ornate_frame(
            right_container, self.colors['bronze'], self.colors['deep_purple'],
            row=2, column=0, sticky='ew', pady=(5, 0)
        )
        
        tk.Label(inner3, text="ACTIVE PROTOCOLS", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['pink']).pack(anchor='w')
        
        self.protocol_display = tk.Text(inner3, height=6, width=25,
                                       bg=self.colors['medium_purple'],
                                       fg=self.colors['cream'],
                                       font=('Courier', 9),
                                       relief='sunken', borderwidth=2)
        self.protocol_display.pack(fill='both', expand=True, pady=(5, 0))
    
    def create_bottom_control(self):
        """Bottom input and control buttons"""
        bottom_container = tk.Frame(self, bg=self.colors['dark_bg'])
        bottom_container.grid(row=2, column=0, columnspan=3, sticky='ew', 
                             padx=10, pady=(5, 10))
        
        # Ornate frame
        outer_frame = tk.Frame(bottom_container, bg=self.colors['gold'], 
                              padx=3, pady=3, relief='raised', borderwidth=2)
        outer_frame.pack(fill='both', expand=True)
        
        inner_frame = tk.Frame(outer_frame, bg=self.colors['medium_purple'], 
                              padx=2, pady=2)
        inner_frame.pack(fill='both', expand=True)
        
        control_frame = tk.Frame(inner_frame, bg=self.colors['deep_purple'])
        control_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Input field
        input_frame = tk.Frame(control_frame, bg=self.colors['deep_purple'])
        input_frame.pack(side='left', fill='both', expand=True)
        
        tk.Label(input_frame, text="INPUT:", font=('Courier', 10, 'bold'),
                bg=self.colors['deep_purple'], fg=self.colors['cyan']).pack(side='left', padx=(0, 10))
        
        self.input_field = tk.Entry(input_frame, 
                                    bg=self.colors['medium_purple'],
                                    fg=self.colors['cream'],
                                    font=('Courier', 11),
                                    relief='sunken', borderwidth=2,
                                    insertbackground=self.colors['cyan'])
        self.input_field.pack(side='left', fill='both', expand=True)
        self.input_field.bind('<Return>', lambda e: self.send_message())
        
        # Buttons
        button_frame = tk.Frame(control_frame, bg=self.colors['deep_purple'])
        button_frame.pack(side='right', padx=(10, 0))
        
        send_btn = tk.Button(button_frame, text="SEND", 
                            font=('Courier', 10, 'bold'),
                            bg=self.colors['teal'], 
                            fg=self.colors['cream'],
                            activebackground=self.colors['cyan'],
                            relief='raised', borderwidth=2,
                            padx=15, pady=5,
                            command=self.send_message)
        send_btn.pack(side='left', padx=2)
        
        clear_btn = tk.Button(button_frame, text="CLEAR", 
                             font=('Courier', 10, 'bold'),
                             bg=self.colors['magenta'], 
                             fg=self.colors['cream'],
                             activebackground=self.colors['pink'],
                             relief='raised', borderwidth=2,
                             padx=15, pady=5,
                             command=self.clear_conversation)
        clear_btn.pack(side='left', padx=2)
    
    # === THEME MANAGEMENT ===
    
    def on_theme_selected(self, event=None):
        theme_name = self.theme_var.get()
        if theme_name:
            self.load_theme(theme_name)
    
    def load_default_theme(self):
        themes = self.theme_loader.list_themes()
        if themes:
            self.theme_selector.current(0)
            self.load_theme(themes[0])
    
    def reload_theme(self):
        if self.theme_loader.current_theme:
            self.load_theme(self.theme_loader.current_theme)
    
    def load_theme(self, theme_name):
        if self.theme_loader.load_theme(theme_name):
            self.apply_theme()
            print(f"[THEME] ✓ Applied: {theme_name}")
    
    def apply_theme(self):
        """Apply the currently loaded theme"""
        self.apply_center_background()
    
    def apply_center_background(self):
        """Apply background to center display"""
        self.content_canvas.update_idletasks()
        
        width = self.content_canvas.winfo_width() or 700
        height = self.content_canvas.winfo_height() or 700
        
        original_img = self.theme_loader.loaded_images.get('center_display')
        
        if original_img:
            bg_img_pil = original_img.resize((width, height), Image.Resampling.LANCZOS)
            bg_img = ImageTk.PhotoImage(bg_img_pil)
            
            self.canvas_bg_image = bg_img
            
            if self.canvas_bg_id:
                self.content_canvas.delete(self.canvas_bg_id)
            
            self.canvas_bg_id = self.content_canvas.create_image(
                width//2, height//2, image=self.canvas_bg_image
            )
            
            margin = 60
            self.content_canvas.coords(self.canvas_text_window, margin, margin)
            self.content_canvas.itemconfig(self.canvas_text_window, 
                                          width=width-margin*2, 
                                          height=height-margin*2)
            
            self.conversation_display.configure(bg='#1a0f24')
    
    def on_canvas_resize(self, event):
        """Handle canvas resize"""
        margin = 60
        text_width = max(event.width - margin * 2, 100)
        text_height = max(event.height - margin * 2, 100)
        
        self.content_canvas.coords(self.canvas_text_window, margin, margin)
        self.content_canvas.itemconfig(self.canvas_text_window, 
                                      width=text_width, 
                                      height=text_height)
        
        if self.theme_loader.current_theme:
            original_img = self.theme_loader.loaded_images.get('center_display')
            if original_img:
                bg_img_pil = original_img.resize((event.width, event.height), Image.Resampling.LANCZOS)
                bg_img = ImageTk.PhotoImage(bg_img_pil)
                
                self.canvas_bg_image = bg_img
                self.content_canvas.itemconfig(self.canvas_bg_id, image=self.canvas_bg_image)
                self.content_canvas.coords(self.canvas_bg_id, event.width//2, event.height//2)
    
    def apply_palette(self):
        """Apply color palette to UI elements"""
        p = self.colors
        # Use 'dark_bg' key with fallback to default color
        bg_color = p.get('dark_bg', p.get('bg', '#1A0F24'))
        self.configure(bg=bg_color)
    
    # === MESSAGING ===
    
    def add_message(self, role, text):
        """Add message to conversation display"""
        prefix = "Kay" if role == "kay" else "You" if role == "user" else "System"
        
        self.conversation_display.configure(state='normal')
        self.conversation_display.insert('end', f"{prefix}: {text}\n\n", role)
        self.conversation_display.see('end')
        self.conversation_display.configure(state='disabled')
    
    def clear_conversation(self):
        """Clear conversation display"""
        self.conversation_display.configure(state='normal')
        self.conversation_display.delete('1.0', 'end')
        self.conversation_display.configure(state='disabled')
    
    def send_message(self):
        """Send message through wrapper backend"""
        user_input = self.input_field.get().strip()
        self.input_field.delete(0, 'end')
        
        if not user_input:
            return
        
        self.add_message('user', user_input)
        
        if self.wrapper_active:
            # Use real wrapper backend
            reply = self.chat_loop(user_input)
        else:
            # Mock response
            reply = "[Wrapper backend not available - visual mode only]"
        
        self.add_message('kay', reply)
        
        # Track session
        self.current_session.append({"you": user_input, "kay": reply})
    
    def chat_loop(self, user_input):
        """Process message through wrapper backend"""
        try:
            # Recall memories
            self.memory.recall(self.agent_state, user_input)
            
            # Update engines
            self.temporal.update(self.agent_state)
            self.body.update(self.agent_state)
            
            # Build context
            context = {
                "user_input": user_input,
                "recalled_memories": getattr(self.agent_state, 'last_recalled_memories', []),
                "emotional_state": {"cocktail": getattr(self.agent_state, 'emotional_cocktail', {})},
                "body": getattr(self.agent_state, 'body', {}),
                "recent_context": [],
                "turn_count": self.turn_count,
                "session_id": self.session_id
            }
            
            # Get LLM response
            reply = get_llm_response(
                context,
                affect=3.5,
                system_prompt=KAY_SYSTEM_PROMPT,
                session_context={"turn_count": self.turn_count, "session_id": self.session_id},
                use_cache=True
            )
            
            self.turn_count += 1
            
            # Post-process
            reply = self.body.embody_text(reply, self.agent_state)
            
            # Extract emotions
            extracted_emotions = self.emotion_extractor.extract_emotions(reply)
            self.emotion_extractor.store_emotional_state(extracted_emotions, self.agent_state.emotional_cocktail)
            
            # Track for anti-repetition
            self.recent_responses.append(reply)
            if len(self.recent_responses) > 3:
                self.recent_responses.pop(0)
            
            # Post-turn updates
            self.social.update(self.agent_state, user_input, reply)
            
            # Encode memories
            self.memory.encode(
                self.agent_state,
                user_input,
                reply,
                list(self.agent_state.emotional_cocktail.keys())
            )
            
            return reply
            
        except Exception as e:
            print(f"[CHAT LOOP] Error: {e}")
            import traceback
            traceback.print_exc()
            return f"[Error: {str(e)}]"
    
    # === LIVE DATA UPDATES ===
    
    def update_live_displays(self):
        """Update info panels with live data"""
        if self.wrapper_active:
            try:
                self.update_emotion_display()
                self.update_entity_display()
                self.update_memory_display()
                self.update_status_display()
                self.update_protocol_display()
            except Exception as e:
                print(f"[UPDATE] Error: {e}")
        
        self.after(1000, self.update_live_displays)
    
    def update_emotion_display(self):
        """Update emotional state display with real data"""
        emo = getattr(self.agent_state, 'emotional_cocktail', {}) or {}
        
        self.emotion_display.configure(state='normal')
        self.emotion_display.delete('1.0', 'end')
        
        if not emo:
            self.emotion_display.insert('1.0', 'Neutral: 0.1')
        else:
            # Sort by intensity
            sorted_emo = sorted(emo.items(), key=lambda x: x[1].get('intensity', 0), reverse=True)
            
            for emotion, data in sorted_emo[:4]:  # Top 4
                intensity = data.get('intensity', 0)
                self.emotion_display.insert('end', f'{emotion}: {intensity:.2f}\n')
        
        self.emotion_display.configure(state='disabled')
    
    def update_entity_display(self):
        """Update entity tracking with real data"""
        self.entity_display.configure(state='normal')
        self.entity_display.delete('1.0', 'end')
        
        if hasattr(self.memory, 'entity_graph'):
            entity_count = len(self.memory.entity_graph.entities)
            self.entity_display.insert('1.0', f'Total: {entity_count} entities\n\n')
            
            # Show key entities
            key_entities = ['Re', 'Kay', 'John']
            for entity in key_entities:
                if entity in self.memory.entity_graph.entities:
                    self.entity_display.insert('end', f'{entity} [TRACKED]\n')
        else:
            self.entity_display.insert('1.0', 'Entity tracking\navailable')
        
        self.entity_display.configure(state='disabled')
    
    def update_memory_display(self):
        """Update memory status with real data"""
        self.memory_display.configure(state='normal')
        self.memory_display.delete('1.0', 'end')
        
        if hasattr(self.memory, 'memory_layers'):
            stats = self.memory.memory_layers.get_layer_stats()
            working = stats['working']['count']
            episodic = stats['episodic']['count']
            semantic = stats['semantic']['count']
            
            self.memory_display.insert('1.0', f'Working: {working}\n')
            self.memory_display.insert('end', f'Episodic: {episodic}\n')
            self.memory_display.insert('end', f'Semantic: {semantic}\n\n')
            self.memory_display.insert('end', 'Status: ACTIVE')
        else:
            self.memory_display.insert('1.0', 'Memory system\ninitialized')
        
        self.memory_display.configure(state='disabled')
    
    def update_status_display(self):
        """Update system status"""
        self.status_display.configure(state='normal')
        self.status_display.delete('1.0', 'end')
        
        status = "LLM: " + ("Connected" if self.wrapper_active else "Offline") + "\n"
        status += f"Session: {self.turn_count} turns\n\n"
        
        if self.wrapper_active:
            status += "Wrapper: ACTIVE\n"
            status += "Memory: Online\n"
            status += "Emotions: Tracking"
        else:
            status += "Visual Mode"
        
        self.status_display.insert('1.0', status)
        self.status_display.configure(state='disabled')
    
    def update_protocol_display(self):
        """Update active protocols"""
        self.protocol_display.configure(state='normal')
        self.protocol_display.delete('1.0', 'end')
        
        protocols = []
        if self.wrapper_active:
            protocols = [
                '✓ ULTRAMAP',
                '✓ Entity tracking',
                '✓ Memory layers',
                '✓ Persistence',
                '✓ Theme loader'
            ]
        else:
            protocols = [
                '✓ Theme loader',
                '✓ Visual system'
            ]
        
        self.protocol_display.insert('1.0', '\n'.join(protocols))
        self.protocol_display.configure(state='disabled')


def main():
    app = KayOrnateIntegrated()
    app.mainloop()


if __name__ == "__main__":
    main()