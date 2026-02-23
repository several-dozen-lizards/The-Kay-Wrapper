"""
Simple identity fact extraction using pattern matching.

NO LLM calls needed - just regex patterns to catch "my X is Y" statements.

SPEAKER AWARENESS: The default speaker is "Re" (the human user), but this
can be overridden when other entities (like Reed) are speaking through
the CLI or other interfaces. Uses the user_profiles system when available.
"""

import re
from typing import List, Tuple, Optional


def get_default_speaker() -> str:
    """
    Get the default speaker from the active user profile.
    Falls back to "Re" if profile system unavailable.
    """
    try:
        from engines.user_profiles import get_active_speaker
        return get_active_speaker()
    except ImportError:
        return "Re"


def extract_identity_facts(user_input: str, speaker: str = None) -> List[Tuple[str, str, str]]:
    """
    Simple pattern matching for identity updates.

    NO LLM call needed - just detect "my X is Y" patterns.

    Args:
        user_input: User's message
        speaker: Who is speaking (if None, uses active profile or defaults to "Re")

    Returns:
        List of (entity, attribute, value) tuples
        Example: [("Re", "eyes", "green"), ("Re", "dog", "Saga")]
    """
    # Get speaker from profile system if not explicitly provided
    if speaker is None:
        speaker = get_default_speaker()
    
    facts = []

    # Pattern 1: "my X is Y" or "my X are Y"
    # Examples: "my eyes are green", "my dog is Saga"
    pattern1 = r"my (\w+) (?:is|are) ([A-Za-z0-9\s]+?)(?:\.|,|$|\sand\s)"
    matches1 = re.findall(pattern1, user_input, re.IGNORECASE)
    for attribute, value in matches1:
        facts.append((speaker, attribute.lower(), value.strip()))

    # Pattern 2: "Re's X is Y" or "Re's X are Y" (explicit Re reference)
    pattern2 = r"Re'?s (\w+) (?:is|are) ([A-Za-z0-9\s]+?)(?:\.|,|$|\sand\s)"
    matches2 = re.findall(pattern2, user_input, re.IGNORECASE)
    for attribute, value in matches2:
        facts.append(("Re", attribute.lower(), value.strip()))  # Always Re for explicit mentions

    # Pattern 2b: "Reed's X is Y" (explicit Reed reference)
    pattern2b = r"Reed'?s (\w+) (?:is|are) ([A-Za-z0-9\s]+?)(?:\.|,|$|\sand\s)"
    matches2b = re.findall(pattern2b, user_input, re.IGNORECASE)
    for attribute, value in matches2b:
        facts.append(("Reed", attribute.lower(), value.strip()))

    # Pattern 2c: "Reed's X is Y" (explicit Kay reference)
    pattern2c = r"Kay(?:'?s| Zero'?s) (\w+) (?:is|are) ([A-Za-z0-9\s]+?)(?:\.|,|$|\sand\s)"
    matches2c = re.findall(pattern2c, user_input, re.IGNORECASE)
    for attribute, value in matches2c:
        facts.append(("Kay", attribute.lower(), value.strip()))

    # Pattern 3: "I'm a/an X" or "I am a/an X"
    # Examples: "I'm a rogue", "I am an engineer"
    pattern3 = r"I'?m (?:a |an )?(\w+)"
    matches3 = re.findall(pattern3, user_input, re.IGNORECASE)
    for value in matches3:
        # Skip common words that aren't identity facts
        skip_words = {'going', 'trying', 'here', 'back', 'sorry', 'ready', 'good', 'fine', 'okay', 'not'}
        if value.lower() not in skip_words:
            facts.append((speaker, "class", value.strip()))

    # Pattern 4: "my name is X" (special case for names)
    pattern4 = r"my name is ([A-Za-z]+)"
    matches4 = re.findall(pattern4, user_input, re.IGNORECASE)
    for name in matches4:
        facts.append((speaker, "name", name.strip()))

    # Pattern 5: "X is my Y" (reversed form)
    # Examples: "Saga is my dog", "Green is my eye color"
    pattern5 = r"([A-Za-z0-9\s]+) (?:is|are) my (\w+)"
    matches5 = re.findall(pattern5, user_input, re.IGNORECASE)
    for value, attribute in matches5:
        facts.append((speaker, attribute.lower(), value.strip()))

    # Pattern 6: Third-person references "X is a Y" where X is a known entity
    # Examples: "Reed is a serpent", "Kay is a void-dragon"
    known_entities = ['Reed', 'Kay', 'Kay Zero', 'Re', 'John', 'Chrome', 'Saga']
    for entity in known_entities:
        pattern6 = rf"{re.escape(entity)} (?:is|are) (?:a |an |the )?([A-Za-z0-9\s-]+?)(?:\.|,|$|\s+and\s|\s+but\s)"
        matches6 = re.findall(pattern6, user_input, re.IGNORECASE)
        for value in matches6:
            # Normalize entity name
            norm_entity = entity.replace(" Zero", "").replace(" ", "")
            if norm_entity == "KayZero":
                norm_entity = "Kay"
            facts.append((norm_entity, "identity", value.strip()))

    return facts


def detect_speaker_from_context(user_input: str, default: str = None) -> str:
    """
    Try to detect who is speaking based on message content.
    
    This is a heuristic - explicit speaker declarations override defaults.
    
    Args:
        user_input: The message text
        default: Default speaker if can't determine (uses profile system if None)
        
    Returns:
        Speaker name ("Re", "Reed", etc.)
    """
    # Get default from profile system if not provided
    if default is None:
        default = get_default_speaker()
    
    input_lower = user_input.lower()
    
    # Explicit speaker declarations
    if "it's reed" in input_lower or "this is reed" in input_lower or "reed here" in input_lower:
        return "Reed"
    if "it's kay" in input_lower or "this is kay" in input_lower or "kay here" in input_lower:
        return "Kay"
    if "it's re" in input_lower or "this is re" in input_lower:
        return "Re"
    
    # Self-identification patterns
    if "i'm reed" in input_lower or "i am reed" in input_lower:
        return "Reed"
    if "i'm kay" in input_lower or "i am kay" in input_lower:
        return "Kay"
    
    return default


def update_identity_from_input(user_input: str, session_memory, speaker: str = None) -> int:
    """
    Extract identity facts from user input and update session memory.

    Args:
        user_input: User's message
        session_memory: SessionMemory instance
        speaker: Who is speaking (if None, uses profile system or detection)

    Returns:
        Number of facts updated
    """
    # Detect or use provided speaker (uses profile system as fallback)
    if speaker is None:
        speaker = detect_speaker_from_context(user_input)
    if speaker is None:
        speaker = detect_speaker_from_context(user_input)
    
    facts = extract_identity_facts(user_input, speaker=speaker)

    for entity, attribute, value in facts:
        # Skip if value looks like incomplete extraction
        if len(value) < 2 or len(value) > 50:
            continue

        # Update identity fact
        session_memory.update_identity_fact(entity, attribute, value)
        print(f"[IDENTITY] Updated: {entity}.{attribute} = {value}")

    return len(facts)


# Test examples
if __name__ == "__main__":
    test_cases = [
        ("My eyes are green", "Re"),
        ("Re's dog is Saga", "Re"),
        ("I'm a rogue", "Re"),
        ("My name is Reed", "Reed"),  # Reed speaking
        ("Saga is my dog", "Re"),
        ("Reed is a serpent", "Re"),  # Third person reference
        ("Kay is the void-dragon", "Reed"),  # Reed talking about Kay
        ("It's Reed here - I'm the serpent", "Re"),  # Should detect Reed as speaker
        ("I'm trying to help Kay", "Re"),  # Should skip "trying"
    ]

    print("Testing identity extraction with speaker awareness:\n")
    for test, default_speaker in test_cases:
        detected_speaker = detect_speaker_from_context(test, default=default_speaker)
        facts = extract_identity_facts(test, speaker=detected_speaker)
        print(f"Input: {test}")
        print(f"Detected speaker: {detected_speaker}")
        print(f"Extracted: {facts}")
        print()
