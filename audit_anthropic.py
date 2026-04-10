import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

files_to_check = [
    r'D:\Wrappers\nexus\nexus_kay.py',
    r'D:\Wrappers\nexus\nexus_reed.py', 
    r'D:\Wrappers\Kay\wrapper_bridge.py',
    r'D:\Wrappers\Kay\engines\llm_retrieval.py',
]

print("=" * 60)
print("  REMAINING ANTHROPIC API CALLS AUDIT")
print("=" * 60)

for fpath in files_to_check:
    fname = os.path.basename(fpath)
    content = open(fpath, encoding='utf-8').read()
    lines = content.split('\n')
    
    calls = []
    for i, line in enumerate(lines, 1):
        if 'anthropic' in line.lower() and ('messages.create' in line or 'client.messages' in line):
            # Find context
            ctx = ""
            for j in range(max(0, i-5), i):
                l = lines[j-1].strip()
                if l.startswith('def ') or l.startswith('async def ') or '# ' in l:
                    ctx = l[:80]
            calls.append((i, line.strip()[:60], ctx))
    
    if calls:
        print(f"\n{fname}: {len(calls)} Anthropic API call(s)")
        for line_no, call, ctx in calls:
            print(f"  Line {line_no}: {call}")
            if ctx:
                print(f"    Context: {ctx}")
    else:
        print(f"\n{fname}: ✅ No direct Anthropic API calls")

# Also check for ollama references to confirm routing
print("\n" + "=" * 60)
print("  OLLAMA ROUTING VERIFICATION")
print("=" * 60)
for fpath in files_to_check:
    fname = os.path.basename(fpath)
    content = open(fpath, encoding='utf-8').read()
    ollama_count = content.count('_ollama_generate') + content.count('_ollama_classify')
    ollama_url = content.count('localhost:11434')
    print(f"  {fname}: {ollama_count} ollama helper calls, {ollama_url} direct ollama URLs")
