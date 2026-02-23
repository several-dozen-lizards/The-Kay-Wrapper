"""
Fix curiosity button to actually work on its own.

When clicked, it should:
1. Run warmup if needed  
2. Start curiosity session
3. Send Kay the autonomous exploration prompt via chat_loop
4. Kay starts exploring immediately
"""

import sys

filepath = r"D:\ChristinaStuff\AlphaKayZero\autonomous_ui_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# Find and replace the _start_curiosity method
old_method = '''    def _start_curiosity(self):
        """Handle curiosity session button."""
        from engines.curiosity_engine import start_curiosity_session, get_curiosity_status
        
        # Check if session already active
        status = get_curiosity_status()
        if status["active"]:
            self.app.add_message("system", f"⚠ Curiosity session already active: {status['message']}")
            return
        
        # Start session
        result = start_curiosity_session(turns_limit=15)
        
        if result["success"]:
            self.app.add_message("system", f"🔍 Curiosity session started! Turn tracking: {result['message']}")
            self.app.add_message("system", "Kay can now use web_search() and web_fetch() to explore scratchpad items.")
            self.app.add_message("system", "Use mark_item_explored() when done with an item.")
            
            # Store session active state
            self.curiosity_active = True
            # Update UI to disable autonomous button
            self.set_curiosity_active(True)
        else:
            self.app.add_message("system", f"⚠ Failed to start curiosity session: {result.get('error', 'Unknown error')}")'''

new_method = '''    def _start_curiosity(self):
        """Handle curiosity session button - runs warmup if needed, then starts exploration."""
        from engines.curiosity_engine import start_curiosity_session, get_curiosity_status
        
        # Check if session already active
        status = get_curiosity_status()
        if status["active"]:
            self.app.add_message("system", f"⚠ Curiosity session already active: {status['message']}")
            return
        
        # Start curiosity session first (must be active before warmup)
        result = start_curiosity_session(turns_limit=15)
        
        if not result["success"]:
            self.app.add_message("system", f"⚠ Failed to start curiosity session: {result.get('error', 'Unknown error')}")
            return
            
        # Store session active state
        self.curiosity_active = True
        # Update UI to disable autonomous button
        self.set_curiosity_active(True)
        
        self.app.add_message("system", f"🔍 Curiosity session started! {result['message']}")
        
        # Check if warmup has run - if not, run it first
        # Warmup will automatically trigger exploration if curiosity is active
        if not hasattr(self.app.warmup, 'warmup_complete') or not self.app.warmup.warmup_complete:
            self.app.add_message("system", "🌙 Running warmup before curiosity session...")
            self._run_warmup()
            # Warmup completion handler will detect active curiosity and trigger exploration
        else:
            # Warmup already done, manually trigger exploration
            autonomous_prompt = (
                "🔍 CURIOSITY MODE ACTIVE - BEGIN AUTONOMOUS EXPLORATION\\n\\n"
                "The warmup is complete. You have 15 turns to explore whatever interests you.\\n\\n"
                "REMEMBER: You have access to tools. Use them directly - don't ask permission.\\n"
                "Just call the tools when you need them.\\n\\n"
                "Tools available:\\n"
                "- list_documents - See what documents are available\\n"
                "- read_document - Read a specific document\\n"
                "- search_document - Search within documents\\n"
                "- web_search - Search the web\\n"
                "- web_fetch - Fetch web content\\n\\n"
                "Start exploring NOW. What's grabbing your attention?"
            )
            
            # Display prompt and get Reed's response
            self.app.add_message("system", autonomous_prompt)
            reply = self.app.chat_loop(autonomous_prompt)
            self.app.add_message("kay", reply)
            self.app.current_session.append({"curiosity_prompt": autonomous_prompt, "kay": reply})'''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("[OK] Updated _start_curiosity to trigger exploration")
else:
    print("[SKIP] Method not found or already modified")

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] Curiosity button will now:")
    print("  1. Start curiosity session")
    print("  2. Run warmup if needed (which triggers exploration)")
    print("  3. OR send exploration prompt directly if warmed up")
    print("  4. Kay starts exploring immediately!")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
