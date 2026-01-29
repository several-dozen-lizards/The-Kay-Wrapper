"""
Quick script to check the actual structure of your memory files.
This helps debug why the cleanup script can't find memories.
"""

import json
import os

MEMORY_FILE = "memory/memory_layers.json"
ENTITY_FILE = "memory/entity_graph.json"

print("="*60)
print("MEMORY STRUCTURE DEBUGGER")
print("="*60)

# Check memory file
print("\n1. MEMORY FILE STRUCTURE:")
print(f"   File: {MEMORY_FILE}")

try:
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   Type: {type(data)}")
    
    if isinstance(data, dict):
        print(f"   Top-level keys: {list(data.keys())}")
        
        for key in data.keys():
            value = data[key]
            if isinstance(value, list):
                print(f"     - {key}: list with {len(value)} items")
                if len(value) > 0:
                    print(f"       First item type: {type(value[0])}")
                    if isinstance(value[0], dict):
                        print(f"       First item keys: {list(value[0].keys())[:10]}")
            elif isinstance(value, dict):
                print(f"     - {key}: dict with {len(value)} items")
            else:
                print(f"     - {key}: {type(value)}")
    
    elif isinstance(data, list):
        print(f"   List with {len(data)} items")
        if len(data) > 0:
            print(f"   First item type: {type(data[0])}")
            if isinstance(data[0], dict):
                print(f"   First item keys: {list(data[0].keys())}")

except Exception as e:
    print(f"   ERROR: {e}")

# Check entity file
print("\n2. ENTITY FILE STRUCTURE:")
print(f"   File: {ENTITY_FILE}")

try:
    with open(ENTITY_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   Type: {type(data)}")
    
    if isinstance(data, dict):
        print(f"   Top-level keys: {list(data.keys())}")
        
        # Check entities
        if 'entities' in data:
            entities = data['entities']
            print(f"   Entities type: {type(entities)}")
            if isinstance(entities, dict):
                print(f"   Entities count: {len(entities)}")
                if entities:
                    first_key = list(entities.keys())[0]
                    print(f"   Sample entity ID: {first_key}")
                    print(f"   Sample entity structure: {type(entities[first_key])}")
                    if isinstance(entities[first_key], dict):
                        print(f"   Sample entity keys: {list(entities[first_key].keys())}")
        
        # Check relationships
        if 'relationships' in data:
            relationships = data['relationships']
            print(f"   Relationships type: {type(relationships)}")
            if isinstance(relationships, dict):
                print(f"   Relationships count: {len(relationships)}")
                if relationships:
                    first_key = list(relationships.keys())[0]
                    print(f"   Sample relationship ID: {first_key}")
                    print(f"   Sample relationship type: {type(relationships[first_key])}")
                    if isinstance(relationships[first_key], dict):
                        print(f"   Sample relationship keys: {list(relationships[first_key].keys())}")
                    elif isinstance(relationships[first_key], str):
                        print(f"   Sample relationship value: {relationships[first_key]}")

except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "="*60)
print("Run this to see what structure you have, then we can fix cleanup script")
print("="*60)