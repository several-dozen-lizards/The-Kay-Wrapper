# entity_prompts.py — Persona-driven identity prompts.
# Drop-in replacement for kay_prompts.py / reed_prompts.py.
# No GUI dependencies. Safe to import from server processes.
#
# Loads system prompt from persona/system_prompt.md via persona_loader.
# All template variables ({ENTITY_NAME}, {USER_NAME}, etc.) are resolved
# automatically.

from persona_loader import persona

# Backwards-compatible alias.
# Old code references KAY_SYSTEM_PROMPT or REED_SYSTEM_PROMPT.
# This provides the same interface regardless of entity name.
SYSTEM_PROMPT = persona.system_prompt if persona else "You are a helpful companion."

# Legacy aliases for code that imports KAY_SYSTEM_PROMPT directly.
# These all point to the same resolved prompt.
KAY_SYSTEM_PROMPT = SYSTEM_PROMPT
REED_SYSTEM_PROMPT = SYSTEM_PROMPT
ENTITY_SYSTEM_PROMPT = SYSTEM_PROMPT
