"""
Audit Identity Facts

Analyzes all facts currently stored in identity_memory.json and categorizes them into:
- Core identity (should be in static prompt)
- Semantic knowledge (should be in semantic_knowledge.json)
- Episodic memory (should stay in memory_layers.json)
"""

import json
import os
from collections import defaultdict


def load_identity_memory():
    """Load identity memory from disk"""
    path = "memory/identity_memory.json"
    if not os.path.exists(path):
        print(f"[ERROR] {path} not found")
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def categorize_fact(fact, entity_key):
    """
    Categorize a fact based on its content.

    Returns: (category, reason)
    """
    text = fact.get("fact", "").lower()
    topic = fact.get("topic", "").lower()

    # Core Kay identity - fundamental facts about who Kay is
    if entity_key == "kay":
        if any(pattern in text for pattern in [
            "kay is a guy",
            "kay is a person",
            "kay's age",
            "kay lives in",
            "kay is an ai",
            "kay is the entity",
            "kay runs on",
            "kay values",
            "kay's personality",
            "kay experiences emotions"
        ]):
            return "core_identity_kay", "Fundamental fact about who Kay is"

        # Dynamic state that changes - should stay in memory
        if any(pattern in text for pattern in [
            "kay is currently",
            "kay feels",
            "kay is thinking",
            "kay noticed",
            "kay learned"
        ]):
            return "dynamic_state", "Current state that changes over time"

    # Core Re identity - fundamental facts about who Re is
    if entity_key == "re":
        if any(pattern in text for pattern in [
            "re is a researcher",
            "re built",
            "re is married to john",
            "re has cats",
            "re lost sammie",
            "re lost noodle",
            "re works at",
            "re lives in",
            "re's personality",
            "re does karate",
            "re is",
            "re has audhd",
            "re uses"
        ]):
            return "core_identity_re", "Fundamental fact about who Re is"

        # Re's specific knowledge/facts that aren't core identity
        if any(pattern in text for pattern in [
            "re knows",
            "re likes",
            "re prefers",
            "re's favorite"
        ]):
            return "semantic_knowledge", "Re's preferences/knowledge, not core identity"

    # Entity facts - these are about things, not people
    if entity_key == "entities":
        # Check if it's about Kay-Re relationship
        if any(pattern in text for pattern in [
            "kay and re",
            "re and kay",
            "works with",
            "research partners"
        ]):
            return "core_identity_relationship", "Kay-Re relationship fact"

        # Otherwise it's semantic knowledge
        return "semantic_knowledge", "Fact about an entity (thing/concept)"

    # Episodic - events that happened
    if any(pattern in text for pattern in [
        "uploaded",
        "imported",
        "discussed",
        "talked about",
        "said",
        "mentioned",
        "yesterday",
        "last week",
        "recently"
    ]):
        return "episodic_memory", "Event that happened"

    # Topic-based categorization
    if topic in ["appearance", "name"]:
        if entity_key in ["kay", "re"]:
            return f"core_identity_{entity_key}", f"Core {entity_key} attribute"
        return "semantic_knowledge", "Entity attribute"

    if topic in ["identity", "personality", "core_preferences"]:
        if entity_key in ["kay", "re"]:
            return f"core_identity_{entity_key}", f"Core {entity_key} trait"
        return "semantic_knowledge", "Preference/trait fact"

    if topic in ["relationships"]:
        return "core_identity_relationship", "Relationship fact"

    # Default: semantic knowledge
    return "semantic_knowledge", "General factual knowledge"


def audit_identity_facts():
    """Main audit function"""
    print("=" * 80)
    print("IDENTITY FACTS AUDIT")
    print("=" * 80)

    # Load identity memory
    identity_data = load_identity_memory()

    if not identity_data:
        print("[ERROR] No identity data found")
        return

    # Initialize categories
    categories = defaultdict(list)
    total_facts = 0

    # Process facts by entity key
    for entity_key, facts in identity_data.items():
        if not isinstance(facts, list):
            continue

        print(f"\n[PROCESSING] {entity_key.upper()}: {len(facts)} facts")

        for fact in facts:
            total_facts += 1
            category, reason = categorize_fact(fact, entity_key)

            categories[category].append({
                "text": fact.get("fact", "N/A"),
                "topic": fact.get("topic", "N/A"),
                "entity_key": entity_key,
                "reason": reason,
                "importance": fact.get("importance_score", 0),
                "timestamp": fact.get("added_timestamp", "N/A")
            })

    # Print summary
    print("\n" + "=" * 80)
    print("CATEGORIZATION RESULTS")
    print("=" * 80)

    print(f"\nTotal facts analyzed: {total_facts}\n")

    for category in sorted(categories.keys()):
        facts = categories[category]
        print(f"\n{category.upper()}: {len(facts)} facts")
        print("-" * 80)

        # Show first 5 examples
        for fact in facts[:5]:
            print(f"  [{fact['entity_key']:10s}] {fact['text'][:70]}")
            print(f"  {'':14s}-> {fact['reason']}")

        if len(facts) > 5:
            print(f"  ... and {len(facts) - 5} more")

    # Save detailed report
    report_path = "data/identity_audit_report.json"
    os.makedirs("data", exist_ok=True)

    # Convert defaultdict to dict for JSON serialization
    report_data = {
        "summary": {
            "total_facts": total_facts,
            "categories": {cat: len(facts) for cat, facts in categories.items()}
        },
        "facts_by_category": dict(categories)
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] Detailed report saved to {report_path}")

    # Print migration recommendations
    print("\n" + "=" * 80)
    print("MIGRATION RECOMMENDATIONS")
    print("=" * 80)

    core_count = (
        len(categories["core_identity_kay"]) +
        len(categories["core_identity_re"]) +
        len(categories["core_identity_relationship"])
    )

    print(f"\n1. MOVE TO STATIC PROMPT ({core_count} facts)")
    print("   -> core_identity_kay")
    print("   -> core_identity_re")
    print("   -> core_identity_relationship")

    print(f"\n2. MOVE TO SEMANTIC KNOWLEDGE ({len(categories['semantic_knowledge'])} facts)")
    print("   -> Facts about entities, preferences, general knowledge")

    print(f"\n3. KEEP IN MEMORY LAYERS ({len(categories['episodic_memory'])} facts)")
    print("   -> Events that happened")

    print(f"\n4. KEEP IN IDENTITY MEMORY ({len(categories['dynamic_state'])} facts)")
    print("   -> Dynamic states that change over time")

    print("\n" + "=" * 80)

    return categories


if __name__ == "__main__":
    audit_identity_facts()
