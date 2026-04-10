import re

log = open(r'D:\ChristinaStuff\ReedMemory\nexus log.txt', encoding='utf-8').read()

anthropic_calls = log.count('api.anthropic.com')
ollama_calls = log.count('localhost:11434')

# Extract token usage
usage_lines = [l for l in log.split('\n') if '[USAGE]' in l]
total_input = 0
total_output = 0
for line in usage_lines:
    m = re.search(r'Input: (\d+) tokens, Output: (\d+) tokens', line)
    if m:
        total_input += int(m.group(1))
        total_output += int(m.group(2))

# Cache stats
cache_created = log.count('[CACHE] Cache created')
cache_hit = log.count('[CACHE] Cache hit')

# Activity calls (these use Anthropic API)
activity_lines = [l for l in log.split('\n') if '[ACTIVITY]' in l]
activity_types = {}
for line in activity_lines:
    for atype in ['paint', 'pursue_curiosity', 'research_curiosity', 'observe_and_comment', 
                   'read_document', 'read_archive', 'write_diary']:
        if atype in line.lower():
            activity_types[atype] = activity_types.get(atype, 0) + 1

# LLM retrieval calls (document selection - uses Anthropic)
retrieval_calls = log.count('[KAY:LLM RETRIEVAL] Checking')

# Entity extraction calls
entity_calls = log.count('HTTP Request: POST https://api.anthropic.com')

print("=" * 60)
print("  API COST ANALYSIS")
print("=" * 60)
print(f"\nAnthropic API calls (total): {anthropic_calls}")
print(f"Ollama calls (local, FREE): {ollama_calls}")
print(f"\nToken usage (from [USAGE] lines, {len(usage_lines)} entries):")
print(f"  Input tokens:  {total_input:,}")
print(f"  Output tokens: {total_output:,}")
print(f"\nCache stats:")
print(f"  Cache created: {cache_created}")
print(f"  Cache hits:    {cache_hit}")
print(f"\nLLM Retrieval (doc selection): {retrieval_calls} calls")
print(f"\nActivity breakdown (each uses Anthropic):")
for k, v in sorted(activity_types.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print(f"\nTotal Anthropic POST requests: {entity_calls}")

# Estimate cost
# Sonnet input: $3/MTok, output: $15/MTok, cache read: $0.30/MTok
est_input_cost = (total_input / 1_000_000) * 3.0
est_output_cost = (total_output / 1_000_000) * 15.0
print(f"\nEstimated cost from logged [USAGE] lines only:")
print(f"  Input:  ${est_input_cost:.2f}")
print(f"  Output: ${est_output_cost:.2f}")
print(f"  Total:  ${est_input_cost + est_output_cost:.2f}")
print(f"\n  (This is ONLY for turns with [USAGE] logging)")
print(f"  (Activities, retrieval, entity extraction add more)")
