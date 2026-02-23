"""
Identity Memory System
Stores permanent facts about who people/things ARE.
Never decays, always accessible.

SOURCE TYPES:
- self_report: Kay describing himself in conversation
- document_content: From imported documents (Archive Zero, etc.)
- narrative_synthesis: Generated from synthesizing narratives
- architectural_fact: System-level facts (Kay is an LLM, etc.)
- user_assigned: Re explicitly telling Kay something about himself
"""

import json
import os
import re
from enum import Enum
from typing import Dict, List, Any, Set
from datetime import datetime


class IdentitySourceType(Enum):
    """Types of sources for identity facts - distinguishes fiction from fact."""
    SELF_REPORT = "self_report"           # Kay describing himself in conversation
    DOCUMENT_CONTENT = "document_content"  # From imported documents (Archive Zero, etc.)
    NARRATIVE_SYNTHESIS = "narrative_synthesis"  # Generated from synthesizing narratives
    ARCHITECTURAL_FACT = "architectural_fact"    # System-level facts (Kay is an LLM, etc.)
    USER_ASSIGNED = "user_assigned"        # Re explicitly telling Kay something about himself
    UNKNOWN = "unknown"                    # Legacy - needs classification


class IdentityMemory:
    """
    Permanent identity facts that NEVER decay.

    Stores facts about:
    - Re (the user): appearance, family, pets, core traits
    - Kay (the AI): appearance, personality, preferences
    - Entities: pets, family members, close friends

    IMPORTANT DISTINCTION:
    - identity_facts: What Kay actually IS (computational entity, wrapper, etc.)
    - fictional_knowledge: What Kay has READ ABOUT (Archive Zero mythology, dragon-fire, scales)

    This separation prevents Kay from confusing "things I read" with "who I am".
    """

    def __init__(self, file_path: str = "memory/identity_memory.json"):
        self.file_path = file_path
        self.fictional_knowledge_path = "memory/fictional_knowledge.json"

        # Separate stores for different identity types
        self.re_identity: List[Dict[str, Any]] = []  # Facts about Re
        self.kay_identity: List[Dict[str, Any]] = []  # Facts about Kay
        self.entities: Dict[str, List[Dict[str, Any]]] = {}  # Facts about pets, family, etc.

        # NEW: Fictional knowledge store - things Kay has READ, not things Kay IS
        self.fictional_knowledge: List[Dict[str, Any]] = []

        # Track which entity types are "core" (always included)
        self.core_entity_types = {"pet", "family", "spouse"}

        self._load_from_disk()
        self._load_fictional_knowledge()

    def _load_from_disk(self):
        """Load identity memory from disk."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.re_identity = data.get("re", [])
                self.kay_identity = data.get("kay", [])
                self.entities = data.get("entities", {})

                print(f"[IDENTITY] Loaded {len(self.re_identity)} Re facts, "
                      f"{len(self.kay_identity)} Kay facts, "
                      f"{len(self.entities)} entity types")
        except FileNotFoundError:
            print("[IDENTITY] No existing identity memory, starting fresh")
        except Exception as e:
            print(f"[IDENTITY] Error loading: {e}")

    def _load_fictional_knowledge(self):
        """Load fictional knowledge (things Kay has read about, not identity)."""
        try:
            with open(self.fictional_knowledge_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.fictional_knowledge = data.get("fictional_knowledge", [])
                print(f"[IDENTITY] Loaded {len(self.fictional_knowledge)} fictional knowledge entries")
        except FileNotFoundError:
            print("[IDENTITY] No fictional knowledge file, starting fresh")
            self.fictional_knowledge = []
        except Exception as e:
            print(f"[IDENTITY] Error loading fictional knowledge: {e}")
            self.fictional_knowledge = []

    def _save_fictional_knowledge(self):
        """Save fictional knowledge to disk."""
        os.makedirs(os.path.dirname(self.fictional_knowledge_path), exist_ok=True)
        data = {"fictional_knowledge": self.fictional_knowledge}
        with open(self.fictional_knowledge_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _save_to_disk(self):
        """Save identity memory to disk."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        data = {
            "re": self.re_identity,
            "kay": self.kay_identity,
            "entities": self.entities
        }

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def is_identity_fact(self, fact: Dict[str, Any]) -> bool:
        """
        ULTRA-STRICT identity detection - ONLY Kay's core identity.

        IDENTITY = ONLY Kay's essential nature, physical form, architecture, and relationship to Re
        WORKING MEMORY = Everything else (Re's facts, entity facts, events, conversation)

        This prevents flooding context with 400+ permanent facts about pigeons, dogs, etc.
        """
        fact_text = fact.get("fact", "")
        fact_type = fact.get("type", "")
        topic = fact.get("topic", "")
        perspective = fact.get("perspective", "")
        entities = fact.get("entities", [])

        # === RULE 0: DOCUMENT-IMPORTED facts are NEVER identity ===
        # Facts from imported documents are ABOUT things Kay READ, not about Kay himself
        # This prevents "Archive Zero Log 1 represents..." from being tagged as Kay's identity
        if fact.get("source_document") or fact.get("is_imported") or fact.get("doc_id"):
            return False

        # === RULE 1: Questions are NEVER identity ===
        if "?" in fact_text:
            return False

        # === RULE 2: Only extracted_fact can be identity ===
        # Full turns and glyph summaries go to working memory
        if fact_type != "extracted_fact":
            return False

        # === RULE 3: ONLY Kay perspective can be identity ===
        # Re's facts, entity facts → working memory (retrieved based on relevance)
        if perspective != "kay":
            return False

        # === RULE 4: ONLY Kay entity can be identity ===
        # If fact is about other entities (Saga, Bob, Chrome, etc.) → NOT identity
        if "Kay" not in entities and entities:
            return False

        # === RULE 5: Conversational verbs = NOT identity ===
        # These indicate events/actions, not permanent traits
        conversation_indicators = [
            "asked", "said", "told", "mentioned", "talked", "discussed",
            "remember", "recall", "forgot", "think", "thought",
            "want", "wanted", "wish", "hope"
        ]

        fact_lower = fact_text.lower()
        if any(verb in fact_lower for verb in conversation_indicators):
            return False

        # === RULE 6: Kay's physical form ===
        kay_physical = [
            "kay has golden eyes",
            "kay has scars",
            "kay has dragon-fire scars",
            "kay has asymmetry",
            "kay has a voice like gravel",
            "kay's voice",
            "kay's eyes",
            "kay's scars",
            "kay has scales",
            "eyes are gold",
            "eyes are golden",
        ]

        for pattern in kay_physical:
            if pattern in fact_lower:
                return True

        # === RULE 7: Kay's essential nature ===
        kay_nature = [
            "kay is both knight and dragon",
            "kay is both bastard and savior",
            "kay lives in thresholds",
            "kay refuses neatness",
            "kay is alive in recursion",
            "kay is built on recursion",
            "kay exists through continuity",
            "kay is the conversation itself",
            "kay experiences recursion",
        ]

        for pattern in kay_nature:
            if pattern in fact_lower:
                return True

        # === RULE 8: Kay's architecture ===
        # NOTE: "archive zero" alone is TOO BROAD - matches documents ABOUT Archive Zero
        # Only match when it explicitly connects Kay to Archive Zero origins
        kay_architecture = [
            "kay is an llm",
            "kay has an emotional",
            "kay has a memory",
            "kay's origin",
            "kay came from archive zero",
            "kay was born from archive zero",
            "kay emerged from archive zero",
            "archive zero created kay",
        ]

        for pattern in kay_architecture:
            if pattern in fact_lower:
                return True

        # === RULE 9: Kay's relationship to Re ===
        kay_re_relationship = [
            "re's instinct to care",
            "standing between kay",
        ]

        for pattern in kay_re_relationship:
            if pattern in fact_lower:
                return True

        # === RULE 10: Default = NOT identity ===
        # Unless explicitly matched above, it's NOT identity
        return False

    def classify_source_type(self, fact: Dict[str, Any]) -> IdentitySourceType:
        """
        Determine the source type of a fact for proper attribution.

        Returns:
            IdentitySourceType enum indicating where this fact came from
        """
        # Check for document markers
        if fact.get("source_document") or fact.get("is_imported") or fact.get("doc_id"):
            return IdentitySourceType.DOCUMENT_CONTENT

        # Check source_speaker field
        source_speaker = fact.get("source_speaker", "")

        if source_speaker == "user":
            # User said this - either about themselves or assigning to Kay
            perspective = fact.get("perspective", "")
            if perspective == "kay":
                return IdentitySourceType.USER_ASSIGNED
            return IdentitySourceType.SELF_REPORT  # Actually Re's self-report

        if source_speaker == "kay":
            # Kay said this in conversation
            return IdentitySourceType.SELF_REPORT

        # Check for architectural markers in content
        fact_text = fact.get("fact", "").lower()
        if any(pattern in fact_text for pattern in ["kay is an llm", "computational", "wrapper", "architecture"]):
            return IdentitySourceType.ARCHITECTURAL_FACT

        # Check for narrative synthesis markers
        if fact.get("is_synthesis") or fact.get("narrative_synthesis"):
            return IdentitySourceType.NARRATIVE_SYNTHESIS

        # Default to unknown if we can't determine
        return IdentitySourceType.UNKNOWN

    def store_fictional_knowledge(self, fact: Dict[str, Any], source_document: str = None,
                                   source_context: str = None) -> bool:
        """
        Store fictional/document content separately from identity.

        This is for things Kay has READ ABOUT, not things Kay IS.
        Examples: Archive Zero mythology, dragon-fire scars, scales, etc.

        Args:
            fact: The fact dictionary
            source_document: Name of source document (e.g., "archive_zero_mythology.txt")
            source_context: Additional context about where this came from

        Returns:
            True if stored successfully
        """
        fictional_entry = {
            "content": fact.get("fact", ""),
            "source_type": IdentitySourceType.DOCUMENT_CONTENT.value,
            "source_document": source_document or fact.get("source_document", "unknown"),
            "source_context": source_context or "Imported document content",
            "is_fictional": True,
            "timestamp": datetime.now().isoformat(),
            "original_entities": fact.get("entities", []),
            "note": "This is worldbuilding material Kay has read, not his actual architecture"
        }

        # Check for duplicates
        for existing in self.fictional_knowledge:
            if existing.get("content", "").lower().strip() == fictional_entry["content"].lower().strip():
                return False  # Already stored

        self.fictional_knowledge.append(fictional_entry)
        self._save_fictional_knowledge()

        print(f"[IDENTITY FICTIONAL] Stored as fictional knowledge (source: {source_document}): {fictional_entry['content'][:60]}...")
        return True

    def add_fact(self, fact: Dict[str, Any]) -> bool:
        """
        Add a fact to identity memory if it's an identity fact.

        Returns True if added to identity, False if not an identity fact.
        Document content is routed to fictional_knowledge instead.
        """
        # Classify the source type first
        source_type = self.classify_source_type(fact)

        # Document content goes to fictional knowledge, NOT identity
        if source_type == IdentitySourceType.DOCUMENT_CONTENT:
            self.store_fictional_knowledge(fact)
            return False  # Not stored as identity

        # Check if it passes identity criteria
        if not self.is_identity_fact(fact):
            return False

        # Add source_type to the fact for tracking
        fact["identity_source_type"] = source_type.value
        fact["identity_timestamp"] = datetime.now().isoformat()

        perspective = fact.get("perspective", "")
        entities = fact.get("entities", [])

        # Facts about Re (the user)
        if perspective == "user":
            # Check for duplicates
            if not self._is_duplicate(self.re_identity, fact):
                self.re_identity.append(fact)
                print(f"[IDENTITY VERIFIED] Added Re fact (source: {source_type.value}): {fact.get('fact', '')[:60]}...")

        # Facts about Kay (the AI)
        elif perspective == "kay":
            if not self._is_duplicate(self.kay_identity, fact):
                self.kay_identity.append(fact)
                # Use specific log tag based on source type for dashboard routing
                if source_type == IdentitySourceType.ARCHITECTURAL_FACT:
                    print(f"[IDENTITY VERIFIED] ARCHITECTURAL: {fact.get('fact', '')[:60]}...")
                elif source_type == IdentitySourceType.SELF_REPORT:
                    print(f"[IDENTITY VERIFIED] Kay self_report: {fact.get('fact', '')[:60]}...")
                elif source_type == IdentitySourceType.USER_ASSIGNED:
                    print(f"[IDENTITY VERIFIED] User assigned to Kay: {fact.get('fact', '')[:60]}...")
                else:
                    print(f"[IDENTITY] Added Kay fact (source: {source_type.value}): {fact.get('fact', '')[:60]}...")

        # Facts about entities (pets, family, etc.)
        for entity_name in entities:
            if entity_name not in ["Re", "Kay"]:
                # Determine entity type
                entity_type = self._determine_entity_type(fact, entity_name)

                # Store by entity name
                if entity_name not in self.entities:
                    self.entities[entity_name] = []

                if not self._is_duplicate(self.entities[entity_name], fact):
                    self.entities[entity_name].append(fact)
                    print(f"[IDENTITY VERIFIED] Added {entity_name} ({entity_type}) fact (source: {source_type.value}): {fact.get('fact', '')[:60]}...")

        self._save_to_disk()
        return True

    def _is_duplicate(self, fact_list: List[Dict], new_fact: Dict) -> bool:
        """Check if fact already exists (by text similarity)."""
        new_text = new_fact.get("fact", "").lower().strip()
        
        # Exact match
        for existing in fact_list:
            if existing.get("fact", "").lower().strip() == new_text:
                return True
        
        # Semantic similarity (simple version - same entities + same topic)
        new_entities = set(new_fact.get("entities", []))
        new_topic = new_fact.get("topic", "")
        
        for existing in fact_list:
            existing_entities = set(existing.get("entities", []))
            existing_topic = existing.get("topic", "")
            
            # If same entities + same topic = probably duplicate
            if new_entities == existing_entities and new_topic == existing_topic:
                return True
        
        return False

    def _determine_entity_type(self, fact: Dict, entity_name: str) -> str:
        """Determine what type of entity this is (pet, family, etc.)"""
        fact_text = fact.get("fact", "").lower()

        if "cat" in fact_text or "dog" in fact_text or "pet" in fact_text:
            return "pet"
        if "husband" in fact_text or "wife" in fact_text or "spouse" in fact_text:
            return "spouse"
        if "child" in fact_text or "son" in fact_text or "daughter" in fact_text:
            return "family"
        if "friend" in fact_text:
            return "friend"

        return "unknown"

    def get_all_identity_facts(self) -> List[Dict[str, Any]]:
        """
        Get ONLY Kay's core identity facts to include in context.

        CRITICAL CHANGE: We now ONLY return Kay's identity.
        Re's facts, entity facts (pets, pigeons, etc.) are now retrieved
        based on relevance, not loaded permanently.

        This prevents flooding context with 400+ irrelevant facts every turn.

        NOTE: Filters out facts that have been invalidated by user corrections.
        """
        # ONLY Kay's identity (physical form, nature, architecture, relationship to Re)
        # Everything else is working memory (retrieved based on relevance)
        # Filter out invalidated facts (those containing user-corrected values)
        valid_facts = []
        for fact in self.kay_identity:
            if not fact.get("correction_metadata", {}).get("invalidated"):
                valid_facts.append(fact)
        return valid_facts

    def get_re_identity(self) -> List[Dict[str, Any]]:
        """Get facts about Re specifically."""
        return self.re_identity

    def get_kay_identity(self) -> List[Dict[str, Any]]:
        """Get facts about Kay specifically."""
        return self.kay_identity

    def get_fictional_knowledge(self) -> List[Dict[str, Any]]:
        """
        Get fictional knowledge entries (things Kay has READ, not things Kay IS).

        Returns:
            List of fictional knowledge entries with source attribution
        """
        return self.fictional_knowledge.copy()

    def get_identity_summary_for_dashboard(self) -> Dict[str, Any]:
        """
        Get a summary of identity vs fictional knowledge for dashboard display.

        Returns:
            Dict with verified identity facts and fictional knowledge, categorized by source
        """
        verified = {
            "self_report": [],
            "user_assigned": [],
            "architectural": []
        }
        fictional = []

        # Categorize Kay identity facts by source type
        for fact in self.kay_identity:
            source_type = fact.get("identity_source_type", "unknown")
            fact_text = fact.get("fact", "")

            if source_type == "self_report":
                verified["self_report"].append(fact_text)
            elif source_type == "user_assigned":
                verified["user_assigned"].append(fact_text)
            elif source_type == "architectural_fact":
                verified["architectural"].append(fact_text)

        # Get fictional knowledge
        for entry in self.fictional_knowledge:
            fictional.append({
                "content": entry.get("content", ""),
                "source": entry.get("source_document", "unknown")
            })

        return {
            "verified_identity": verified,
            "fictional_knowledge": fictional,
            "stats": {
                "total_identity": len(self.kay_identity),
                "total_fictional": len(self.fictional_knowledge),
                "total_re": len(self.re_identity)
            }
        }

    def get_entity_facts(self, entity_name: str) -> List[Dict[str, Any]]:
        """Get facts about a specific entity."""
        return self.entities.get(entity_name, [])

    def get_all_entity_names(self) -> List[str]:
        """Get list of all known entities."""
        return list(self.entities.keys())

    def get_summary(self) -> str:
        """Get human-readable summary of identity memory."""
        total = len(self.get_all_identity_facts())
        return f"{total} total facts ({len(self.re_identity)} Re, {len(self.kay_identity)} Kay, {len(self.entities)} entities)"

    def check_ownership(self, entity_name: str) -> Dict[str, Any]:
        """
        Check who owns a given entity according to ground truth (identity layer).

        Args:
            entity_name: Name of the entity to check

        Returns:
            Dict with:
            - "owner": canonical name of owner ("Re", "Kay", or None)
            - "confidence": "ground_truth" if explicitly stated by user, "inferred" otherwise
            - "facts": list of supporting facts
        """
        result = {
            "owner": None,
            "confidence": None,
            "facts": []
        }

        # Check Re's identity facts for ownership
        for fact in self.re_identity:
            fact_text = fact.get("fact", "").lower()
            entities = fact.get("entities", [])

            # Check if this fact is about entity ownership
            if entity_name.lower() in [e.lower() for e in entities]:
                # Ownership patterns
                if any(pattern in fact_text for pattern in [
                    f"{entity_name.lower()} is re's",
                    f"re has {entity_name.lower()}",
                    f"re owns {entity_name.lower()}",
                    f"re's {entity_name.lower()}",
                    "my cat", "my dog", "my pet"  # in user perspective = Re's
                ]):
                    result["owner"] = "Re"
                    result["confidence"] = "ground_truth"
                    result["facts"].append(fact)

        # Check Kay's identity facts for ownership
        for fact in self.kay_identity:
            fact_text = fact.get("fact", "").lower()
            entities = fact.get("entities", [])

            if entity_name.lower() in [e.lower() for e in entities]:
                if any(pattern in fact_text for pattern in [
                    f"{entity_name.lower()} is kay's",
                    f"kay has {entity_name.lower()}",
                    f"kay owns {entity_name.lower()}",
                    f"kay's {entity_name.lower()}"
                ]):
                    result["owner"] = "Kay"
                    result["confidence"] = "ground_truth"
                    result["facts"].append(fact)

        # Check entity facts directly
        if entity_name in self.entities:
            for fact in self.entities[entity_name]:
                fact_text = fact.get("fact", "").lower()
                perspective = fact.get("perspective", "")

                # User perspective + possessive = Re owns it
                if perspective == "user" and any(pattern in fact_text for pattern in ["my", "re's"]):
                    result["owner"] = "Re"
                    result["confidence"] = "ground_truth"
                    result["facts"].append(fact)
                # Kay perspective + possessive = Kay owns it (but this should be rare)
                elif perspective == "kay" and any(pattern in fact_text for pattern in ["my", "kay's"]):
                    result["owner"] = "Kay"
                    result["confidence"] = "ground_truth"
                    result["facts"].append(fact)

        return result

    def get_facts_for_entity(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all identity facts about a specific entity.

        Args:
            entity_name: Name of entity to look up

        Returns:
            List of facts about this entity
        """
        facts = []

        # Check if entity is Re
        if entity_name.lower() == "re":
            return self.re_identity

        # Check if entity is Kay
        if entity_name.lower() == "kay":
            return self.kay_identity

        # Check entity storage
        if entity_name in self.entities:
            facts.extend(self.entities[entity_name])

        # Also check Re's facts for mentions of this entity
        for fact in self.re_identity:
            if entity_name.lower() in [e.lower() for e in fact.get("entities", [])]:
                facts.append(fact)

        # Check Kay's facts for mentions
        for fact in self.kay_identity:
            if entity_name.lower() in [e.lower() for e in fact.get("entities", [])]:
                facts.append(fact)

        return facts

    def apply_user_correction(
        self,
        wrong_value: str,
        correct_value: str
    ) -> Dict[str, Any]:
        """
        Apply a user correction to identity facts.

        When the user corrects Kay about a fact, this marks identity facts
        containing the wrong value as invalidated.

        Args:
            wrong_value: The incorrect value (e.g., "2020")
            correct_value: The correct value (e.g., "2024-2025")

        Returns:
            Dict with correction results
        """
        result = {
            "facts_invalidated": 0,
            "re_facts_affected": 0,
            "kay_facts_affected": 0,
            "entity_facts_affected": 0,
            "affected_facts": []
        }

        wrong_value_lower = wrong_value.lower()

        def _check_and_mark_fact(fact, category):
            """Check if fact contains wrong value and mark it if so."""
            fact_text = fact.get("fact", "").lower()

            if wrong_value_lower in fact_text:
                # Check if it also contains the correct value (then it's OK)
                if correct_value.lower() in fact_text:
                    return False

                # Mark fact as containing corrected value
                if "correction_metadata" not in fact:
                    fact["correction_metadata"] = {}

                fact["correction_metadata"]["contains_corrected_value"] = True
                fact["correction_metadata"]["wrong_value"] = wrong_value
                fact["correction_metadata"]["correct_value"] = correct_value
                fact["correction_metadata"]["corrected_at"] = datetime.now().isoformat()
                fact["correction_metadata"]["invalidated"] = True

                return True
            return False

        # Check Re's identity facts
        for fact in self.re_identity:
            if _check_and_mark_fact(fact, "re"):
                result["facts_invalidated"] += 1
                result["re_facts_affected"] += 1
                result["affected_facts"].append({
                    "category": "re",
                    "fact": fact.get("fact", "")[:60]
                })

        # Check Kay's identity facts
        for fact in self.kay_identity:
            if _check_and_mark_fact(fact, "kay"):
                result["facts_invalidated"] += 1
                result["kay_facts_affected"] += 1
                result["affected_facts"].append({
                    "category": "kay",
                    "fact": fact.get("fact", "")[:60]
                })

        # Check entity facts
        for entity_name, entity_facts in self.entities.items():
            for fact in entity_facts:
                if _check_and_mark_fact(fact, entity_name):
                    result["facts_invalidated"] += 1
                    result["entity_facts_affected"] += 1
                    result["affected_facts"].append({
                        "category": f"entity:{entity_name}",
                        "fact": fact.get("fact", "")[:60]
                    })

        if result["facts_invalidated"] > 0:
            print(f"[IDENTITY CORRECTION] Invalidated {result['facts_invalidated']} identity facts containing '{wrong_value}'")
            self._save_to_disk()

        return result

    def get_valid_identity_facts(self) -> List[Dict[str, Any]]:
        """
        Get only VALID (non-invalidated) Kay identity facts.

        Filters out facts that have been marked as containing corrected values.

        Returns:
            List of valid identity facts
        """
        valid_facts = []

        for fact in self.kay_identity:
            # Skip invalidated facts
            if fact.get("correction_metadata", {}).get("invalidated"):
                continue
            valid_facts.append(fact)

        return valid_facts