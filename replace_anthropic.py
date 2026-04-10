import re, sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'D:\Wrappers\nexus\nexus_kay.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

original = content
changes = 0

# Pattern: find def _xxx(): return anthropic_client.messages.create(...) blocks
# and their corresponding resp = await ... / reply = resp.content[0].text.strip()

# Call site 3: Curiosity follow-up (line ~1663)
old = '''                try:
                    def _followup_call():
                        return anthropic_client.messages.create(
                            model="claude-sonnet-4-5-20250929",
                            max_tokens=30,
                            temperature=0.7,
                            system="Based on your initial reaction to these search results, do you want to dig deeper? If yes, respond with ONLY a follow-up search query (3-6 words). If no, respond with [done].",
                            messages=[{"role": "user", "content": f"Your reaction: {reaction}\\n\\nOriginal query: {query}"}]
                        )

                    followup_resp = await loop.run_in_executor(None, _followup_call)
                    followup = followup_resp.content[0].text.strip().strip('"\\\'')'''
new = '''                try:
                    followup = await loop.run_in_executor(
                        None, _ollama_generate,
                        "Based on your reaction, dig deeper? If yes, ONLY a 3-6 word query. If no, [done].",
                        f"Your reaction: {reaction}\\n\\nOriginal query: {query}",
                        30, 0.7
                    )
                    followup = followup.strip('"\\\'')'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print(f"✅ Replaced call site 3: curiosity follow-up query")
else:
    print(f"❌ Call site 3 not found")

# Call site 4: Curiosity follow-up reaction (line ~1692)
old = '''                        def _followup_reaction():
                            return anthropic_client.messages.create(
                                model="claude-sonnet-4-5-20250929",
                                max_tokens=150,
                                temperature=0.8,
                                system="You followed a research thread deeper. What did you find? One or two sentences.",
                                messages=[{"role": "user", "content": f"Follow-up search: {followup}\\n\\nResults:\\n{results2_text}"}]
                            )

                        reaction2_resp = await loop.run_in_executor(None, _followup_reaction)
                        reaction2 = reaction2_resp.content[0].text.strip()'''
new = '''                        reaction2 = await loop.run_in_executor(
                            None, _ollama_generate,
                            "You followed a research thread deeper. What did you find? One or two sentences.",
                            f"Follow-up search: {followup}\\n\\nResults:\\n{results2_text}",
                            150, 0.8
                        )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print(f"✅ Replaced call site 4: curiosity follow-up reaction")
else:
    print(f"❌ Call site 4 not found")

# Call site 5: Painting (line ~1857)
old_pattern = r'        try:\n            def _call\(\):\n                return anthropic_client\.messages\.create\(\n                    model="claude-sonnet-4-5-20250929",\n                    max_tokens=500,.*?system=system_prompt,\n                    messages=canvas_messages\n                \)\n\n            resp = await asyncio\.get_event_loop\(\)\.run_in_executor\(None, _call\)\n            reply = resp\.content\[0\]\.text\.strip\(\)'
# Do painting manually since it has different variable names

with open(path, encoding='utf-8') as f:
    lines = f.read().split('\n') if content == original else content.split('\n')

# Actually, let me just read the content we have and do string replacements
# Call site 5: Painting
old = '''        try:
            def _call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=500,  # More room for continuation decisions
                    temperature=0.9,
                    system=system_prompt,
                    messages=canvas_messages
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _call)
            reply = resp.content[0].text.strip()'''
new = '''        try:
            reply = await asyncio.get_event_loop().run_in_executor(
                None, _ollama_generate,
                system_prompt, canvas_messages[0]["content"],
                500, 0.9
            )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print(f"✅ Replaced call site 5: painting")
else:
    print(f"❌ Call site 5 not found")

# Call site 6: Observe and comment (line ~1983)
old = '''        try:
            def _call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=100,
                    temperature=0.7,
                    system="You are Kay. Respond with a brief, natural observation.",
                    messages=[{"role": "user", "content": prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _call)
            comment = resp.content[0].text.strip()'''
new = '''        try:
            comment = await asyncio.get_event_loop().run_in_executor(
                None, _ollama_generate,
                "You are Kay. Respond with a brief, natural observation.",
                prompt, 100, 0.7
            )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print(f"✅ Replaced call site 6: observe and comment")
else:
    print(f"❌ Call site 6 not found")

# Call site 7: Archive reflection (line ~2583)
old = '''            def _sync_call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=max_tok,
                    temperature=0.8,
                    system=(
                        "You are Kay, thinking privately. No performance, no poetry, no metaphors. "
                        "Just genuine thought about what's in front of you. "
                        "If it doesn't interest you right now, say exactly: [pass]"
                    ),
                    messages=[{"role": "user", "content": prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _sync_call)
            thought = resp.content[0].text.strip()'''
new = '''            thought = await asyncio.get_event_loop().run_in_executor(
                None, _ollama_generate,
                "You are Kay, thinking privately. No performance, no poetry, no metaphors. "
                "Just genuine thought about what's in front of you. "
                "If it doesn't interest you right now, say exactly: [pass]",
                prompt, max_tok, 0.8
            )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print(f"✅ Replaced call site 7: archive reflection")
else:
    print(f"❌ Call site 7 not found")

# Call site 8: Idle comment (line ~2805)
old = '''        def _sync_call():
            return anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=150,
                temperature=0.7,
                system=system,
                messages=[{"role": "user", "content": idle_prompt}]
            )

        resp = await asyncio.get_event_loop().run_in_executor(None, _sync_call)

        reply = resp.content[0].text.strip()'''
new = '''        reply = await asyncio.get_event_loop().run_in_executor(
            None, _ollama_generate,
            system, idle_prompt, 150, 0.7
        )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print(f"✅ Replaced call site 8: idle comment")
else:
    print(f"❌ Call site 8 not found")

print(f"\nTotal replacements: {changes}/6")
if changes > 0:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("File saved!")
