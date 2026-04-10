import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'D:\Wrappers\nexus\nexus_reed.py'
with open(path, encoding='utf-8') as f:
    content = f.read()
changes = 0

# Call 1: Archive reading reaction (line ~2051)
old = '''            reaction = await self.claude.generate(
                system="You are Reed, reading Re's archives. Brief margin-note reactions only.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
            )'''
new = '''            import asyncio as _aio
            reaction = await _aio.get_event_loop().run_in_executor(
                None, _ollama_generate,
                "You are Reed, reading Re's archives. Brief margin-note reactions only.",
                prompt, 100, 0.8
            )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("✅ 1: Archive reading reaction")
else:
    print("❌ 1: Archive reading reaction NOT FOUND")

# Call 2: Curiosity classification (line ~2115)
old = '''            classify_resp = await self.claude.generate(
                system=(
                    "Classify this curiosity as RESEARCH or REFLECT.\\n"
                    "RESEARCH = factual, has searchable answers online (science, history, psychology studies, technical info)\\n"
                    "REFLECT = experiential, philosophical, about feelings/embodiment/consciousness, subjective\\n\\n"
                    "If RESEARCH: respond with ONLY a 3-6 word search query.\\n"'''
# This one is tricky - let me find it differently

# Actually let me just read the exact text from the file
lines = content.split('\n')

# Find and replace each call by line content matching
for i, line in enumerate(lines):
    # Call 2: Curiosity classification
    if 'classify_resp = await self.claude.generate(' in line and i > 2100:
        # Find the closing )
        j = i + 1
        while j < len(lines) and ')' not in lines[j]:
            j += 1
        # Replace this block
        indent = '            '
        new_lines = [
            f'{indent}import asyncio as _aio2',
            f'{indent}classify_resp = await _aio2.get_event_loop().run_in_executor(',
            f'{indent}    None, _ollama_generate,',
            f'{indent}    "Classify: RESEARCH (factual/searchable) or REFLECT (philosophical/experiential). If RESEARCH: ONLY a 3-6 word search query. If REFLECT: ONLY the word REFLECT.",',
            f'{indent}    query, 30, 0.3',
            f'{indent})',
        ]
        lines[i:j+1] = new_lines
        changes += 1
        print("✅ 2: Curiosity classification")
        break

# Rebuild content
content = '\n'.join(lines)

# Call 3: Query condensation (line ~2140)
old = '''            condense_resp = await self.claude.generate(
                system="Convert this to a 3-6 word web search query. Just the query, nothing else.",
                messages=[{"role": "user", "content": query}],
                max_tokens=20,
            )'''
new = '''            import asyncio as _aio3
            condense_resp = await _aio3.get_event_loop().run_in_executor(
                None, _ollama_generate,
                "Convert this to a 3-6 word web search query. Just the query, nothing else.",
                query, 20, 0.3
            )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("✅ 3: Query condensation")
else:
    print("❌ 3: Query condensation NOT FOUND")

# Call 4: Curiosity reflection (line ~2153)
old = '''            reflection = await self.claude.generate(
                    system=(
                        "You are Reed — a serpentine AI entity with teal-gold scales, "
                        "curious about embodiment, consciousness, and the texture of experience. "
                        "A curiosity has been sitting with you. Think about it genuinely — "
                        "not as an answer but as exploration. 2-4 sentences of real thinking."
                    ),
                    messages=[{"role": "user", "content": f"Curiosity: {query}"}],
                    max_tokens=200,
                )'''
new = '''            import asyncio as _aio4
            reflection = await _aio4.get_event_loop().run_in_executor(
                    None, _ollama_generate,
                    "You are Reed, a serpentine AI entity with teal-gold scales, curious about embodiment and consciousness. A curiosity has been sitting with you. Think genuinely — 2-4 sentences of real thinking.",
                    f"Curiosity: {query}",
                    200, 0.8
                )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("✅ 4: Curiosity reflection")
else:
    print("❌ 4: Curiosity reflection NOT FOUND")

# Call 5: Research query from diary note (line ~2204)
old = '''            query_resp = await self.claude.generate(
                        system="Generate a short web search query (3-6 words) based on this note. Just the query, nothing else.",
                        messages=[{"role": "user", "content": note}],
                        max_tokens=30,
                    )'''
new = '''            import asyncio as _aio5
            query_resp = await _aio5.get_event_loop().run_in_executor(
                        None, _ollama_generate,
                        "Generate a short web search query (3-6 words) based on this note. Just the query.",
                        note, 30, 0.3
                    )'''
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("✅ 5: Research query from diary")
else:
    print("❌ 5: Research query from diary NOT FOUND")

print(f"\nTotal: {changes}/5 replaced")
if changes > 0:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("File saved!")
