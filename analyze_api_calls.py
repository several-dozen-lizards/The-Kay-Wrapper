import os, re, glob

# Check what models/providers are being used
wrapper_dir = r'D:\Wrappers'

# Find all Anthropic API call sites in the codebase
print("=" * 60)
print("  WHERE ANTHROPIC API IS CALLED")
print("=" * 60)

# Activity system — what model does it use?
activity_file = os.path.join(wrapper_dir, 'nexus', 'activity_engine.py')
if os.path.exists(activity_file):
    content = open(activity_file, encoding='utf-8').read()
    # Find model references
    for line_no, line in enumerate(content.split('\n'), 1):
        if 'anthropic' in line.lower() or 'sonnet' in line.lower() or 'claude' in line.lower():
            print(f"  activity_engine.py:{line_no}: {line.strip()[:100]}")
    for line_no, line in enumerate(content.split('\n'), 1):
        if 'get_llm_response' in line or 'llm_func' in line:
            print(f"  activity_engine.py:{line_no}: {line.strip()[:100]}")
else:
    print("  activity_engine.py not found")

print()

# Check nexus_kay.py for Anthropic calls in activity handling
nk_file = os.path.join(wrapper_dir, 'nexus', 'nexus_kay.py')
content = open(nk_file, encoding='utf-8').read()
lines = content.split('\n')

# Find activity-related Anthropic calls
print("Activity-related API calls in nexus_kay.py:")
for i, line in enumerate(lines, 1):
    if 'activity' in line.lower() and ('anthropic' in line.lower() or 'api' in line.lower()):
        print(f"  Line {i}: {line.strip()[:100]}")

print()

# Check what the LLM retrieval system uses
bridge_file = os.path.join(wrapper_dir, 'Kay', 'wrapper_bridge.py')
content = open(bridge_file, encoding='utf-8').read()
lines = content.split('\n')

print("LLM Retrieval model usage:")
for i, line in enumerate(lines, 1):
    if 'llm_retrieval' in line.lower() or 'LLM_RETRIEVAL' in line:
        if 'model' in line.lower() or 'sonnet' in line.lower() or 'anthropic' in line.lower():
            print(f"  wrapper_bridge.py:{i}: {line.strip()[:100]}")

print()

# Check entity extraction
print("Entity extraction model usage:")
for i, line in enumerate(lines, 1):
    if 'entity' in line.lower() and ('extract' in line.lower() or 'graph' in line.lower()):
        if 'anthropic' in line.lower() or 'model' in line.lower() or 'llm' in line.lower():
            print(f"  wrapper_bridge.py:{i}: {line.strip()[:100]}")

print()

# Check Reed's API usage
reed_file = os.path.join(wrapper_dir, 'nexus', 'nexus_reed.py')
if os.path.exists(reed_file):
    content = open(reed_file, encoding='utf-8').read()
    anthropic_count = content.count('anthropic')
    sonnet_count = content.count('sonnet')
    print(f"Reed's nexus file: {anthropic_count} 'anthropic' refs, {sonnet_count} 'sonnet' refs")

# Check LLM module for model routing
llm_file = os.path.join(wrapper_dir, 'Kay', 'llm.py')
if os.path.exists(llm_file):
    content = open(llm_file, encoding='utf-8').read()
    lines = content.split('\n')
    print("\nLLM module model defaults:")
    for i, line in enumerate(lines, 1):
        if 'default' in line.lower() and ('model' in line.lower() or 'sonnet' in line.lower()):
            print(f"  llm.py:{i}: {line.strip()[:100]}")
        if 'claude' in line.lower() and ('model' in line.lower() or 'default' in line.lower()):
            print(f"  llm.py:{i}: {line.strip()[:100]}")

# Check activity engine's LLM calls
print("\nActivity engine LLM call sites:")
if os.path.exists(activity_file):
    content = open(activity_file, encoding='utf-8').read()
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if ('get_response' in stripped or 'llm' in stripped.lower()) and ('paint' in stripped.lower() or 'curiosity' in stripped.lower() or 'observe' in stripped.lower() or 'comment' in stripped.lower()):
            print(f"  Line {i}: {stripped[:120]}")
