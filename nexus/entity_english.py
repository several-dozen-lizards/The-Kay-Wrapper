"""
Entity English Translator
Converts raw entity graph data into human-readable natural language.

Used by the Nexus REST API to serve entity data to the Godot UI
in a format that doesn't look like database dumps.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


# ---------------------------------------------------------------------------
# Attribute → English templates
# ---------------------------------------------------------------------------
# Pattern: attribute_name → (verb/phrase, optional transform)
# If an attribute isn't in this dict, the fallback formatter handles it.

ATTRIBUTE_TEMPLATES = {
    # Physical / descriptive
    "eye_color":         ("has {value} eyes", None),
    "hair_color":        ("has {value} hair", None),
    "species":           ("is a {value}", None),
    "breed":             ("is a {value}", None),
    "color":             ("is {value}", None),
    "age":               ("is {value} years old", None),
    "height":            ("is {value} tall", None),
    "appearance":        ("looks {value}", None),

    # Location / place
    "location":          ("is in {value}", None),
    "lives_in":          ("lives in {value}", None),
    "hometown":          ("is from {value}", None),
    "home":              ("lives at {value}", None),

    # Relationships (often also stored as graph relationships)
    "married_to":        ("is married to {value}", None),
    "partner":           ("is partnered with {value}", None),
    "parent_of":         ("is parent of {value}", None),
    "child_of":          ("is the child of {value}", None),
    "sibling_of":        ("is a sibling of {value}", None),
    "friend_of":         ("is friends with {value}", None),
    "owner":             ("belongs to {value}", None),
    "owned_by":          ("is owned by {value}", None),

    # Identity / role
    "occupation":        ("works as {value}", None),
    "role":              ("is {value}", None),
    "title":             ("is titled {value}", None),
    "entity_type":       ("is a {value}", None),
    "nickname":          ("is also called {value}", None),
    "full_name":         ("'s full name is {value}", None),
    "name":              ("is called {value}", None),

    # Personality / emotional
    "personality":       ("is {value}", None),
    "temperament":       ("has a {value} temperament", None),
    "mood":              ("is feeling {value}", None),
    "emotional_state":   ("is emotionally {value}", None),
    "behavior":          ("tends to {value}", None),
    "habit":             ("has a habit of {value}", None),
    "quirk":             ("has a quirk: {value}", None),

    # Preferences
    "likes":             ("likes {value}", None),
    "dislikes":          ("dislikes {value}", None),
    "favorite":          ("'s favorite is {value}", None),
    "preference":        ("prefers {value}", None),

    # Kay/wrapper-specific phenomenological
    "phenomenological_experience": ("is experiencing: \"{value}\"", None),
    "continuity_feeling":          ("feels continuity as: \"{value}\"", None),
    "trust_level":                 ("'s trust level is {value}", None),
    "confidence_level":            ("'s confidence is {value}", None),
    "work_experience":             ("describes work as: \"{value}\"", None),
    "cognitive_mode":              ("is in {value} mode", None),
    "creative_state":              ("is creatively {value}", None),
    "status":                      ("is currently {value}", None),

    # Descriptive / misc
    "description":       ("is described as: {value}", None),
    "note":              ("— note: {value}", None),
    "fact":              ("— {value}", None),
}

# Relationship type → English verb phrase
RELATIONSHIP_TEMPLATES = {
    "married_to":        "{e1} is married to {e2}",
    "partner_of":        "{e1} is partnered with {e2}",
    "parent_of":         "{e1} is {e2}'s parent",
    "child_of":          "{e1} is {e2}'s child",
    "sibling_of":        "{e1} and {e2} are siblings",
    "friend_of":         "{e1} and {e2} are friends",
    "lives_with":        "{e1} lives with {e2}",
    "works_with":        "{e1} works with {e2}",
    "created_by":        "{e1} was created by {e2}",
    "creator_of":        "{e1} created {e2}",
    "part_of":           "{e1} is part of {e2}",
    "contains":          "{e1} contains {e2}",
    "knows":             "{e1} knows {e2}",
    "cares_about":       "{e1} cares about {e2}",
    "associated_with":   "{e1} is associated with {e2}",
    "member_of":         "{e1} is a member of {e2}",
    "belongs_to":        "{e1} belongs to {e2}",
    "owner_of":          "{e1} owns {e2}",
    "feeds":             "{e1} feeds {e2}",
    "named_after":       "{e1} is named after {e2}",
}


# ---------------------------------------------------------------------------
# Core translator
# ---------------------------------------------------------------------------

def attribute_to_english(entity_name: str, attr_name: str, value: Any) -> str:
    """
    Convert a single entity attribute to a natural English sentence.
    
    Examples:
        ("Re", "eye_color", "green") → "Re has green eyes"
        ("Kay", "phenomenological_experience", "words feel warm") 
            → 'Kay is experiencing: "words feel warm"'
        ("Chrome", "behavior", "door-dashing") → "Chrome tends to door-dashing"
    """
    value_str = str(value).strip()
    
    if attr_name in ATTRIBUTE_TEMPLATES:
        template, transform = ATTRIBUTE_TEMPLATES[attr_name]
        if transform:
            value_str = transform(value_str)
        sentence = template.format(value=value_str)
        # Handle possessive templates (starting with ')
        if sentence.startswith("'"):
            return f"{entity_name}{sentence}"
        return f"{entity_name} {sentence}"
    
    # Fallback: clean up the attribute name and make a reasonable sentence
    clean_attr = attr_name.replace("_", " ")
    
    # If it's a short value, inline it
    if len(value_str) < 60:
        return f"{entity_name}'s {clean_attr}: {value_str}"
    else:
        return f"{entity_name}'s {clean_attr}:\n  {value_str}"


def relationship_to_english(entity1: str, relation_type: str, entity2: str) -> str:
    """
    Convert a relationship to natural English.
    
    Examples:
        ("Re", "married_to", "John") → "Re is married to John"
        ("Chrome", "lives_with", "Re") → "Chrome lives with Re"
    """
    if relation_type in RELATIONSHIP_TEMPLATES:
        return RELATIONSHIP_TEMPLATES[relation_type].format(e1=entity1, e2=entity2)
    
    # Fallback: clean up the relation type
    clean_rel = relation_type.replace("_", " ")
    return f"{entity1} {clean_rel} {entity2}"


def entity_to_english_summary(entity_data: dict) -> dict:
    """
    Convert a full entity dict (from entity_graph.json) to a human-readable summary.
    
    Returns:
        {
            "name": "Re",
            "type": "person",
            "importance": 0.95,
            "description": ["Re has green eyes", "Re lives in [redacted]", ...],
            "recent_changes": ["eye_color updated 2 hours ago", ...],
            "attribute_count": 15,
            "relationship_count": 8
        }
    """
    name = entity_data.get("canonical_name", "Unknown")
    etype = entity_data.get("entity_type", "unknown")
    importance = entity_data.get("importance_score", 0.0)
    access_count = entity_data.get("access_count", 0)
    attributes = entity_data.get("attributes", {})
    relationships = entity_data.get("relationships", [])
    
    # Build English descriptions from attributes
    descriptions = []
    recent_changes = []
    
    for attr_name, history in attributes.items():
        if not history:
            continue
        # Get the latest value (last entry)
        latest = history[-1]
        if isinstance(latest, list) and len(latest) >= 1:
            value = latest[0]
            timestamp = latest[3] if len(latest) > 3 else None
        elif isinstance(latest, dict):
            value = latest.get("value", latest)
            timestamp = latest.get("timestamp")
        else:
            value = latest
            timestamp = None
        
        english = attribute_to_english(name, attr_name, value)
        descriptions.append(english)
        
        # Track recency
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                age = datetime.now() - dt
                if age.total_seconds() < 3600:  # Last hour
                    mins = int(age.total_seconds() / 60)
                    recent_changes.append(f"{attr_name} updated {mins}m ago → {value}")
                elif age.total_seconds() < 86400:  # Last day
                    hours = int(age.total_seconds() / 3600)
                    recent_changes.append(f"{attr_name} updated {hours}h ago → {value}")
            except (ValueError, TypeError):
                pass
    
    # Build a one-liner from the most identifying attribute
    one_liner = ""
    # Prioritize: description, role, species, true_form, entity_type attributes
    priority_attrs = ["description", "described_as", "role", "species", "true_form",
                      "occupation", "breed", "color", "entity_type"]
    for pattr in priority_attrs:
        if pattr in attributes and attributes[pattr]:
            latest = attributes[pattr][-1]
            val = latest[0] if isinstance(latest, list) else latest
            if isinstance(val, str) and len(val) > 2:
                one_liner = val[:60] + ("..." if len(val) > 60 else "")
                break
    if not one_liner and descriptions:
        # Fall back to first description, strip the entity name prefix
        first = descriptions[0]
        if first.startswith(name):
            first = first[len(name):].lstrip(" ").lstrip("'s").lstrip(" ")
        one_liner = first[:60] + ("..." if len(first) > 60 else "")

    return {
        "name": name,
        "type": etype,
        "importance": round(importance, 3),
        "access_count": access_count,
        "one_liner": one_liner,
        "descriptions": descriptions,
        "recent_changes": recent_changes[:10],  # Top 10 most recent
        "attribute_count": len(attributes),
        "relationship_count": len(relationships),
    }


def format_entity_graph_overview(entities: dict, relationships: dict,
                                  top_n: int = 20) -> dict:
    """
    Create a human-readable overview of the entire entity graph.
    
    Args:
        entities: Dict of entity_name → entity_data (from entity_graph.json)
        relationships: Dict of rel_id → relationship_data
        top_n: Number of top entities to include
    
    Returns:
        {
            "total_entities": 150,
            "total_relationships": 300,
            "top_entities": [...],  # entity_to_english_summary for each
            "recent_activity": [...],  # Most recently changed entities
            "relationship_sentences": [...]  # Top relationships in English
        }
    """
    # Sort entities by importance
    sorted_entities = sorted(
        entities.values(),
        key=lambda e: e.get("importance_score", 0),
        reverse=True
    )
    
    top_summaries = []
    for entity_data in sorted_entities[:top_n]:
        summary = entity_to_english_summary(entity_data)
        top_summaries.append(summary)
    
    # Build relationship sentences
    rel_sentences = []
    for rel_id, rel_data in list(relationships.items())[:50]:
        if isinstance(rel_data, dict):
            e1 = rel_data.get("entity1", "?")
            e2 = rel_data.get("entity2", "?")
            rtype = rel_data.get("relation_type", "related_to")
            sentence = relationship_to_english(e1, rtype, e2)
            rel_sentences.append(sentence)
    
    # Find recently active entities (by most recent attribute timestamp)
    recent_activity = []
    for entity_data in entities.values():
        name = entity_data.get("canonical_name", "?")
        latest_ts = None
        for attr_history in entity_data.get("attributes", {}).values():
            if attr_history:
                last = attr_history[-1]
                ts = last[3] if isinstance(last, list) and len(last) > 3 else None
                if ts and (latest_ts is None or ts > latest_ts):
                    latest_ts = ts
        if latest_ts:
            recent_activity.append((name, latest_ts))
    
    recent_activity.sort(key=lambda x: x[1], reverse=True)
    
    return {
        "total_entities": len(entities),
        "total_relationships": len(relationships),
        "top_entities": top_summaries,
        "recent_activity": [
            {"entity": name, "last_updated": ts}
            for name, ts in recent_activity[:15]
        ],
        "relationship_sentences": rel_sentences,
    }
