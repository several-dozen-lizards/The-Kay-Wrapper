#!/usr/bin/env python3
"""
Entity Graph Cleanup Script

Removes garbage entities and camera-derived attributes from entity graphs.
Creates backups before modifying.

Run with: python cleanup_entity_graph.py [--dry-run]
"""

import json
import os
import sys
import shutil
from datetime import datetime
from typing import Dict, Any, Set, List, Tuple


# ============================================================================
# NOISE PATTERNS - Entities matching these should be removed
# ============================================================================

ENTITY_NOISE_PATTERNS = {
    # Days of the week / time references
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'today', 'tomorrow', 'yesterday', 'tonight', 'morning', 'afternoon', 'evening',
    'weekend', 'weekday', 'week', 'month', 'year', 'day', 'night', 'hour', 'minute',

    # Common food items (transient mentions)
    'pizza', 'sandwich', 'coffee', 'tea', 'dinner', 'lunch', 'breakfast', 'snack',
    'food', 'meal', 'drink', 'water', 'soda', 'beer', 'wine', 'juice',
    'burger', 'salad', 'soup', 'pasta', 'rice', 'bread', 'chicken', 'beef',
    'margherita', 'pepperoni', 'cheese', 'sauce', 'toppings',

    # Common appliances/furniture (unless specifically named/important)
    'oven', 'microwave', 'fridge', 'refrigerator', 'stove', 'dishwasher', 'toaster',
    'desk', 'chair', 'table', 'couch', 'sofa', 'bed', 'lamp', 'light',
    'screen', 'monitor', 'keyboard', 'mouse', 'computer', 'laptop', 'phone',
    'tv', 'television', 'remote', 'speaker', 'headphones', 'earbuds', 'headset',

    # Room/environment elements
    'room', 'environment', 'atmosphere', 'workspace', 'backdrop', 'curtain',
    'fabric', 'wall', 'floor', 'ceiling', 'window', 'door',
    'scene', 'frame', 'background', 'foreground', 'camera frame',
    'fabric backdrop', 'colored light', 'computing session',

    # Abstract/generic concepts that aren't trackable entities
    'issue', 'problem', 'thing', 'stuff', 'something', 'nothing', 'everything',
    'article', 'blog', 'post', 'comment', 'message', 'text', 'email',
    'system', 'feature', 'bug', 'fix', 'error', 'question', 'answer',
    'idea', 'thought', 'concept', 'topic', 'subject', 'matter',
    'way', 'method', 'approach', 'solution', 'option', 'choice',
    'reason', 'cause', 'effect', 'result', 'outcome', 'consequence',
    'work', 'session', 'activity', 'process', 'task', 'shared activity',
    'files', 'meaning', 'context', 'document', 'joke', 'wiring', 'compression',
    'coherence', 'substrate', 'path', 'sunset', 'branches', 'camera',
    'artwork', 'abstract art', 'art piece', 'art', 'animals', 'woman', 'partner',

    # Self-referential system terms
    'recognition system', 'mislabeling issue', 'memory system', 'entity graph',
    'extraction', 'processing', 'pipeline', 'module', 'engine', 'handler',
    'affective layer',

    # Camera-derived scene attributes (should NOT become entities)
    'environment lighting', 'light source', 'screen light', 'gaze direction',
    'lighting', 'illumination', 'brightness', 'darkness', 'shadow', 'ambient',
    'position', 'posture', 'stance', 'facing', 'looking', 'sitting', 'standing',

    # Common pronouns/determiners that might slip through
    'someone', 'anyone', 'everyone', 'nobody', 'somebody',
    'this', 'that', 'these', 'those', 'here', 'there', 'where', 'when',
    'it', 'we', 'they', 'he', 'she', 'me', 'you', 'us', 'them',
}

# Camera-derived attribute patterns to remove from Re/Kay/Reed entities
CAMERA_ATTRIBUTE_PATTERNS = {
    'gaze_direction', 'environment_lighting', 'light_source', 'screen_position',
    'posture', 'facing_direction', 'body_position', 'head_position',
    'ambient_lighting', 'illumination_type', 'shadow_direction',
    'gaze', 'facing', 'position', 'illumination',
    'alone_status', 'environment_sound', 'people_count', 'animals_count',
    'scene_mood', 'activity_flow', 'visual_feed', 'camera_data',
}

# Core entities that should never be removed
PROTECTED_ENTITIES = {'Re', 'Kay', 'Reed', 'Nexus'}


def is_noise_entity(name: str) -> bool:
    """Check if entity name matches noise patterns."""
    if not name:
        return True

    name_lower = name.lower().strip()

    # Direct match
    if name_lower in ENTITY_NOISE_PATTERNS:
        return True

    # Multi-word patterns
    words = name_lower.split()
    if len(words) >= 1:
        if words[-1] in ENTITY_NOISE_PATTERNS:
            return True
        if words[0] in ENTITY_NOISE_PATTERNS:
            return True

    # Very short generic names
    if len(name_lower) <= 2 and not name_lower.isalpha():
        return True

    # Generic pronouns
    generic_singles = {'it', 'he', 'she', 'they', 'we', 'you', 'me', 'us', 'them'}
    if name_lower in generic_singles:
        return True

    return False


def is_camera_attribute(attr: str) -> bool:
    """Check if attribute is camera-derived."""
    if not attr:
        return False

    attr_lower = attr.lower().strip()

    # Direct match
    if attr_lower in CAMERA_ATTRIBUTE_PATTERNS:
        return True

    # Partial match
    camera_keywords = ['gaze', 'lighting', 'illumination', 'posture', 'facing', 'position']
    for keyword in camera_keywords:
        if keyword in attr_lower:
            return True

    return False


def is_camera_species_value(value: Any) -> bool:
    """Check if a species value is a camera detection artifact."""
    if not isinstance(value, str):
        return False

    value_lower = value.lower().strip()
    return value_lower in ('human', 'person', 'adult', 'male', 'female')


def cleanup_entity_graph(file_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Clean up an entity graph file.

    Args:
        file_path: Path to entity_graph.json
        dry_run: If True, don't modify files, just report what would be done

    Returns:
        Dict with cleanup statistics
    """
    stats = {
        'file': file_path,
        'entities_before': 0,
        'entities_after': 0,
        'entities_removed': [],
        'relationships_removed': 0,
        'attributes_removed': [],
        'backed_up': False,
    }

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"  File not found: {file_path}")
        return stats

    # Load the graph
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Error loading {file_path}: {e}")
        return stats

    entities = data.get('entities', {})
    relationships = data.get('relationships', {})

    stats['entities_before'] = len(entities)

    # Track entities to remove
    entities_to_remove = set()

    # Pass 1: Identify noise entities
    for name, entity_data in entities.items():
        # Skip protected entities
        if name in PROTECTED_ENTITIES:
            continue

        # Check noise patterns
        if is_noise_entity(name):
            entities_to_remove.add(name)
            stats['entities_removed'].append(f"{name} (noise pattern)")
            continue

        # Check unknown type with low access count
        entity_type = entity_data.get('entity_type', 'unknown')
        access_count = entity_data.get('access_count', 0)

        if entity_type == 'unknown' and access_count <= 2:
            # Additional check: is this a meaningful entity?
            # Keep it if it has attributes or relationships
            attrs = entity_data.get('attributes', {})
            rels = entity_data.get('relationships', [])

            # If no meaningful content, remove it
            if len(attrs) <= 1 and len(rels) == 0:
                entities_to_remove.add(name)
                stats['entities_removed'].append(f"{name} (unknown type, access_count={access_count})")

    # Pass 2: Clean up attributes on core entities
    for name in ['Re', 'Kay', 'Reed']:
        if name not in entities:
            continue

        entity_data = entities[name]
        attrs = entity_data.get('attributes', {})

        attrs_to_remove = []
        for attr_name, attr_history in attrs.items():
            # Remove camera-derived attributes
            if is_camera_attribute(attr_name):
                attrs_to_remove.append(attr_name)
                stats['attributes_removed'].append(f"{name}.{attr_name} (camera attribute)")
                continue

            # Clean up species attribute if it has camera values
            if attr_name == 'species':
                new_history = []
                for entry in attr_history:
                    if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                        value = entry[0]
                        if not is_camera_species_value(value):
                            new_history.append(entry)
                        else:
                            stats['attributes_removed'].append(f"{name}.species={value} (camera detection)")
                    else:
                        new_history.append(entry)

                if new_history:
                    attrs[attr_name] = new_history
                else:
                    attrs_to_remove.append(attr_name)

        # Remove identified attributes
        for attr_name in attrs_to_remove:
            if attr_name in attrs:
                del attrs[attr_name]

    # Pass 3: Remove entities and clean up relationships
    if not dry_run:
        # Remove entities
        for name in entities_to_remove:
            if name in entities:
                del entities[name]

        # Clean up relationships that reference removed entities
        rels_to_remove = []
        for rel_id, rel_data in relationships.items():
            entity1 = rel_data.get('entity1', '')
            entity2 = rel_data.get('entity2', '')

            if entity1 in entities_to_remove or entity2 in entities_to_remove:
                rels_to_remove.append(rel_id)

        for rel_id in rels_to_remove:
            if rel_id in relationships:
                del relationships[rel_id]

        stats['relationships_removed'] = len(rels_to_remove)

    stats['entities_after'] = len(entities)

    # Backup and save
    if not dry_run and (entities_to_remove or stats['attributes_removed']):
        # Create backup
        backup_path = file_path + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        try:
            shutil.copy2(file_path, backup_path)
            stats['backed_up'] = True
            print(f"  Backup created: {backup_path}")
        except Exception as e:
            print(f"  Warning: Could not create backup: {e}")

        # Save cleaned data
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"  Saved cleaned graph: {file_path}")
        except Exception as e:
            print(f"  Error saving {file_path}: {e}")

    return stats


def main():
    """Main entry point."""
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 60)
    else:
        print("=" * 60)
        print("ENTITY GRAPH CLEANUP")
        print("=" * 60)

    # Find entity graph files
    base_dir = os.path.dirname(os.path.abspath(__file__))
    graph_files = [
        os.path.join(base_dir, 'Kay', 'memory', 'entity_graph.json'),
        os.path.join(base_dir, 'Reed', 'memory', 'entity_graph.json'),
    ]

    all_stats = []

    for file_path in graph_files:
        print(f"\nProcessing: {file_path}")
        stats = cleanup_entity_graph(file_path, dry_run=dry_run)
        all_stats.append(stats)

        # Print summary for this file
        print(f"  Entities: {stats['entities_before']} -> {stats['entities_after']}")
        print(f"  Entities removed: {len(stats['entities_removed'])}")
        print(f"  Attributes removed: {len(stats['attributes_removed'])}")
        print(f"  Relationships removed: {stats['relationships_removed']}")

        if stats['entities_removed'] and len(stats['entities_removed']) <= 20:
            print("  Removed entities:")
            for entity in stats['entities_removed']:
                print(f"    - {entity}")
        elif stats['entities_removed']:
            print(f"  Removed entities (showing first 20 of {len(stats['entities_removed'])}):")
            for entity in stats['entities_removed'][:20]:
                print(f"    - {entity}")

    # Overall summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_removed = sum(len(s['entities_removed']) for s in all_stats)
    total_attrs = sum(len(s['attributes_removed']) for s in all_stats)
    total_rels = sum(s['relationships_removed'] for s in all_stats)

    print(f"Total entities removed: {total_removed}")
    print(f"Total attributes removed: {total_attrs}")
    print(f"Total relationships removed: {total_rels}")

    if dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply changes.")


if __name__ == '__main__':
    main()
