"""
Quick test for Reed's bug fixes:
1. Entity graph glyph filtering
2. Emotion intensity extraction improvements
"""

from engines.entity_graph import EntityGraph
from engines.emotion_extractor import EmotionExtractor

print("="*60)
print("TESTING ENTITY GRAPH GLYPH FILTERING")
print("="*60)

eg = EntityGraph()

# Test cases: (name, should_be_valid)
entity_tests = [
    ("Re", True),
    ("Kay Zero", True),
    ("K", True),           # Single letter should be valid
    ("Chrome", True),
    ("***", False),        # Pure symbols
    ("...", False),        # Dots only
    ("@#$", False),        # Special chars
    ("*", False),          # Asterisk
    ("", False),           # Empty
    ("   ", False),        # Whitespace only
    ("!!!", False),        # Multiple symbols
    ("Kay123", True),      # Mixed - has alphanumeric
    ("123", True),         # Numbers are valid
]

passed = 0
failed = 0
for name, expected in entity_tests:
    result = eg._is_valid_entity_name(name)
    status = "PASS" if result == expected else "FAIL"
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f"  {status} '{name}': got {result}, expected {expected}")

print(f"\nEntity tests: {passed}/{len(entity_tests)} passed")

print("\n" + "="*60)
print("TESTING EMOTION INTENSITY EXTRACTION")
print("="*60)

ee = EmotionExtractor()

# Test cases: (text, emotion_keyword, expected_intensity_type)
intensity_tests = [
    # Numeric patterns
    ("curiosity sitting at 0.68", "curiosity", "0.68"),
    ("tracking 0.7 curiosity right now", "curiosity", "0.7"),
    ("I feel curious, about 0.5", "curious", "0.5"),
    
    # Qualitative - strong
    ("I feel fucking excited about this", "excited", "strong"),
    ("Really intense curiosity here", "curiosity", "strong"),
    
    # Qualitative - high
    ("I'm really curious about it", "curious", "high"),
    ("Pretty excited actually", "excited", "high"),
    
    # Qualitative - moderate (implicit assertions)
    ("I feel curious", "curious", "moderate"),
    ("There's this curiosity", "curiosity", "moderate"),
    ("I'm feeling anxious", "anxious", "moderate"),
    
    # Qualitative - mild
    ("Slightly curious about that", "curious", "mild"),
    ("A hint of frustration", "frustration", "mild"),
]

passed = 0
failed = 0
for text, keyword, expected in intensity_tests:
    result = ee._extract_intensity(text, keyword)
    # For numeric, check exact match; for qualitative, check category
    if expected in ["0.68", "0.7", "0.5"]:
        match = result == expected
    else:
        match = result == expected
    
    status = "PASS" if match else "FAIL"
    if match:
        passed += 1
    else:
        failed += 1
    print(f"  {status} '{text[:40]}...' -> got '{result}', expected '{expected}'")

print(f"\nIntensity tests: {passed}/{len(intensity_tests)} passed")

print("\n" + "="*60)
print("FULL EMOTION EXTRACTION TEST")  
print("="*60)

test_responses = [
    "I feel really curious about this whole thing",
    "There's some excitement building, tracking it around 0.65",
    "I'm pretty solid right now, less of that scattered feeling",
    "Not much emotional texture right now",
]

for response in test_responses:
    print(f"\nInput: \"{response[:50]}...\"")
    result = ee.extract_emotions(response)
    states = result.get('extracted_states', {})
    if states:
        for emotion, details in states.items():
            print(f"  -> {emotion}: {details.get('intensity', '?')}")
    else:
        print(f"  -> (minimal/no emotions detected)")
