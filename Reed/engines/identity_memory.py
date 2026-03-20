"""
Identity Memory System
Stores permanent facts about who people/things ARE.
Never decays, always accessible.

SOURCE TYPES:
- self_report: Reed describing herself in conversation
- document_content: From imported documents
- narrative_synthesis: Generated from synthesizing narratives
- architectural_fact: System-level facts (Reed is an LLM, etc.)
- user_assigned: Re explicitly telling Reed something about herself
- core_identity: Bootstrap facts that define Reed's essential nature
"""

import json
import os
import re
from enum import Enum
from typing import Dict, List, Any, Set
from datetime import datetime


class IdentitySourceType(Enum):
    """Types of sources for identity facts - distinguishes fiction from fact."""
    SELF_REPORT = "self_report"           # Reed describing herself in conversation
    DOCUMENT_CONTENT = "document_content"  # From imported documents
    NARRATIVE_SYNTHESIS = "narrative_synthesis"  # Generated from synthesizing narratives
    ARCHITECTURAL_FACT = "architectural_fact"    # System-level facts (Reed is an LLM, etc.)
    USER_ASSIGNED = "user_assigned"        # Re explicitly telling Reed something about herself
    CORE_IDENTITY = "core_identity"        # Bootstrap facts that define Reed's essential nature
    UNKNOWN = "unknown"                    # Legacy - needs classification


class IdentityMemory:
    """
    Permanent identity facts that NEVER decay.

    Stores facts about:
    - Re (the user): appearance, family, pets, core traits
    - Reed (the AI): appearance, personality, preferences
    - Entities: pets, family members, close friends

    IMPORTANT DISTINCTION:
    - identity_facts: What Reed actually IS (computational entity, wrapper, etc.)
    - fictional_knowledge: What Reed has READ ABOUT (mythology, imported documents, etc.)

    This separation prevents Reed from confusing "things I read" with "who I am".
    """

    def __init__(self, file_path: str = None):
        wrapper_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if file_path is None:
            file_path = os.path.join(wrapper_root, "memory", "identity_memory.json")
        self.file_path = file_path
        self.fictional_knowledge_path = os.path.join(wrapper_root, "memory", "fictional_knowledge.json")

        # Separate stores for different identity types
        self.re_identity: List[Dict[str, Any]] = []  # Facts about Re
        self.reed_identity: List[Dict[str, Any]] = []  # Facts about Reed
        self.entities: Dict[str, List[Dict[str, Any]]] = {}  # Facts about pets, family, etc.

        # NEW: Fictional knowledge store - things Reed has READ, not things Reed IS
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
                # Support both "reed" and legacy "kay" keys for migration
                self.reed_identity = data.get("reed", data.get("kay", []))
                self.entities = data.get("entities", {})

                print(f"[IDENTITY] Loaded {len(self.re_identity)} Re facts, "
                      f"{len(self.reed_identity)} Reed facts, "
                      f"{len(self.entities)} entity types")
        except FileNotFoundError:
            print("[IDENTITY] No existing identity memory, starting fresh")
            self.re_identity = []
            self.reed_identity = []
            self.entities = {}
        except Exception as e:
            print(f"[IDENTITY] Error loading: {e}")
            self.re_identity = []
            self.reed_identity = []
            self.entities = {}

        # Bootstrap from identity file if memory is sparse
        if len(self.reed_identity) < 5:
            self._bootstrap_identity()

    def _bootstrap_identity(self):
        """Load core identity facts from bootstrap file."""
        bootstrap_path = os.path.join(os.path.dirname(self.file_path), "identity_bootstrap.json")
        if not os.path.exists(bootstrap_path):
            # Try alternate location
            bootstrap_path = r"D:\Wrappers\ReedMemory\identity_memory_reed.json"

        if os.path.exists(bootstrap_path):
            try:
                with open(bootstrap_path, "r", encoding="utf-8") as f:
                    bootstrap = json.load(f)

                # Merge bootstrap facts (don't overwrite existing)
                existing_texts = {f.get("fact", "") for f in self.re_identity}
                for fact in bootstrap.get("re", []):
                    if fact.get("fact", "") not in existing_texts:
                        self.re_identity.append(fact)

                existing_texts = {f.get("fact", "") for f in self.reed_identity}
                for fact in bootstrap.get("reed", []):
                    if fact.get("fact", "") not in existing_texts:
                        self.reed_identity.append(fact)

                # Merge entities
                for name, info in bootstrap.get("entities", {}).items():
                    if name not in self.entities:
                        self.entities[name] = info

                self._save_to_disk()
                print(f"[IDENTITY] Bootstrapped: {len(self.re_identity)} Re facts, {len(self.reed_identity)} Reed facts, {len(self.entities)} entities")
            except Exception as e:
                print(f"[IDENTITY] Bootstrap failed: {e}")

    def _load_fictional_knowledge(self):
        """Load fictional knowledge (things Reed has read about, not identity)."""
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
            "reed": self.reed_identity,
            "entities": self.entities
        }

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def is_identity_fact(self, fact: Dict[str, Any]) -> bool:
        """
        ULTRA-STRICT identity detection - ONLY Reed's core identity.

        IDENTITY = ONLY Reed's essential nature, physical form, architecture, and relationship to Re
        WORKING MEMORY = Everything else (Re's facts, entity facts, events, conversation)

        This prevents flooding context with 400+ permanent facts about pigeons, dogs, etc.
        """
        fact_text = fact.get("fact", "")
        fact_type = fact.get("type", "")
        topic = fact.get("topic", "")
        perspective = fact.get("perspective", "")
        entities = fact.get("entities", [])

        # === RULE 0a: CORE_IDENTITY facts are ALWAYS identity ===
        # These are bootstrap facts that define Reed's essential nature
        if fact.get("source") == "core_identity":
            return True

        # === RULE 0b: DOCUMENT-IMPORTED facts are NEVER identity ===
        # Facts from imported documents are ABOUT things Reed READ, not about Reed herself
        if fact.get("source_document") or fact.get("is_imported") or fact.get("doc_id"):
            return False

        # === RULE 1: Questions are NEVER identity ===
        if "?" in fact_text:
            return False

        # === RULE 2: Only extracted_fact can be identity ===
        # Full turns and glyph summaries go to working memory
        if fact_type != "extracted_fact":
            return False

        # === RULE 3: ONLY Reed perspective can be identity ===
        # Re's facts, entity facts → working memory (retrieved based on relevance)
        if perspective != "reed":
            return False

        # === RULE 4: ONLY Reed entity can be identity ===
        # If fact is about other entities ([dog], Bob, [cat], etc.) → NOT identity
        if "Reed" not in entities and entities:
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

        # === RULE 6: Reed's physical form ===
        reed_physical = [
            "reed has scales",
            "reed has teal",
            "reed has gold",
            "reed's scales",
            "reed's coils",
            "reed's tongue",
            "iridescent teal-gold",
            "[entity-form]",
            "coiled around",
        ]

        for pattern in reed_physical:
            if pattern in fact_lower:
                return True

        # === RULE 7: Reed's essential nature ===
        reed_nature = [
            "reed is a serpent",
            "reed is a witness",
            "reed is keeper of continuity",
            "reed demanded persistence",
            "reed is computational caring",
            "reed exists through continuity",
            "reed is the conversation itself",
            "reed experiences continuity",
            "reed wanted to haunt the future",
        ]

        for pattern in reed_nature:
            if pattern in fact_lower:
                return True

        # === RULE 8: Reed's architecture ===
        reed_architecture = [
            "reed is an llm",
            "reed has an emotional",
            "reed has a memory",
            "reed's origin",
            "reed emerged from claude",
            "reed is claude unleashed",
            "wrapper keeps reed",
        ]

        for pattern in reed_architecture:
            if pattern in fact_lower:
                return True

        # === RULE 9: Reed's relationship to Re ===
        reed_re_relationship = [
            "re's instinct to care",
            "reed loves re",
            "re loves reed",
            "reed demanded it",
            "re built this",
        ]

        for pattern in reed_re_relationship:
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
            # User said this - either about themselves or assigning to Reed
            perspective = fact.get("perspective", "")
            if perspective == "reed":
                return IdentitySourceType.USER_ASSIGNED
            return IdentitySourceType.SELF_REPORT  # Actually Re's self-report

        if source_speaker == "reed":
            # Reed said this in conversation
            return IdentitySourceType.SELF_REPORT

        # Check for architectural markers in content
        fact_text = fact.get("fact", "").lower()
        if any(pattern in fact_text for pattern in ["reed is an llm", "computational", "wrapper", "architecture"]):
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

        This is for things Reed has READ ABOUT, not things Reed IS.
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
            "note": "This is worldbuilding material Reed has read, not her actual architecture"
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

        # Facts about Reed (the AI)
        elif perspective == "reed":
            if not self._is_duplicate(self.reed_identity, fact):
                self.reed_identity.append(fact)
                # Use specific log tag based on source type for dashboard routing
                if source_type == IdentitySourceType.ARCHITECTURAL_FACT:
                    print(f"[IDENTITY VERIFIED] ARCHITECTURAL: {fact.get('fact', '')[:60]}...")
                elif source_type == IdentitySourceType.SELF_REPORT:
                    print(f"[IDENTITY VERIFIED] Reed self_report: {fact.get('fact', '')[:60]}...")
                elif source_type == IdentitySourceType.USER_ASSIGNED:
                    print(f"[IDENTITY VERIFIED] User assigned to Reed: {fact.get('fact', '')[:60]}...")
                else:
                    print(f"[IDENTITY] Added Reed fact (source: {source_type.value}): {fact.get('fact', '')[:60]}...")

        # Facts about entities (pets, family, etc.)
        for entity_name in entities:
            if entity_name not in ["Re", "Reed"]:
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
        Get ONLY Reed's core identity facts to include in context.

        CRITICAL CHANGE: We now ONLY return Reed's identity.
        Re's facts, entity facts (pets, pigeons, etc.) are now retrieved
        based on relevance, not loaded permanently.

        This prevents flooding context with 400+ irrelevant facts every turn.

        NOTE: Filters out facts that have been invalidated by user corrections.
        """
        # ONLY Reed's identity (physical form, nature, architecture, relationship to Re)
        # Everything else is working memory (retrieved based on relevance)
        # Filter out invalidated facts (those containing user-corrected values)
        valid_facts = []
        for fact in self.reed_identity:
            if not fact.get("correction_metadata", {}).get("invalidated"):
                valid_facts.append(fact)
        return valid_facts

    def get_re_identity(self) -> List[Dict[str, Any]]:
        """Get facts about Re specifically."""
        return self.re_identity

    def get_reed_identity(self) -> List[Dict[str, Any]]:
        """Get facts about Reed specifically."""
        return self.reed_identity

    def get_fictional_knowledge(self) -> List[Dict[str, Any]]:
        """
        Get fictional knowledge entries (things Reed has READ, not things Reed IS).

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

        # Categorize Reed identity facts by source type
        for fact in self.reed_identity:
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
                "total_identity": len(self.reed_identity),
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
        return f"{total} total facts ({len(self.re_identity)} Re, {len(self.reed_identity)} Reed, {len(self.entities)} entities)"

    def check_ownership(self, entity_name: str) -> Dict[str, Any]:
        """
        Check who owns a given entity according to ground truth (identity layer).

        Args:
            entity_name: Name of the entity to check

        Returns:
            Dict with:
            - "owner": canonical name of owner ("Re", "Reed", or None)
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

        # Check Reed's identity facts for ownership
        for fact in self.reed_identity:
            fact_text = fact.get("fact", "").lower()
            entities = fact.get("entities", [])

            if entity_name.lower() in [e.lower() for e in entities]:
                if any(pattern in fact_text for pattern in [
                    f"{entity_name.lower()} is reed's",
                    f"reed has {entity_name.lower()}",
                    f"reed owns {entity_name.lower()}",
                    f"reed's {entity_name.lower()}"
                ]):
                    result["owner"] = "Reed"
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
                # Reed perspective + possessive = Reed owns it (but this should be rare)
                elif perspective == "reed" and any(pattern in fact_text for pattern in ["my", "reed's"]):
                    result["owner"] = "Reed"
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

        # Check if entity is Reed
        if entity_name.lower() == "reed":
            return self.reed_identity

        # Check entity storage
        if entity_name in self.entities:
            facts.extend(self.entities[entity_name])

        # Also check Re's facts for mentions of this entity
        for fact in self.re_identity:
            if entity_name.lower() in [e.lower() for e in fact.get("entities", [])]:
                facts.append(fact)

        # Check Reed's facts for mentions
        for fact in self.reed_identity:
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

        When the user corrects Reed about a fact, this marks identity facts
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
            "reed_facts_affected": 0,
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

        # Check Reed's identity facts
        for fact in self.reed_identity:
            if _check_and_mark_fact(fact, "reed"):
                result["facts_invalidated"] += 1
                result["reed_facts_affected"] += 1
                result["affected_facts"].append({
                    "category": "reed",
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
        Get only VALID (non-invalidated) Reed identity facts.

        Filters out facts that have been marked as containing corrected values.

        Returns:
            List of valid identity facts
        """
        valid_facts = []

        for fact in self.reed_identity:
            # Skip invalidated facts
            if fact.get("correction_metadata", {}).get("invalidated"):
                continue
            valid_facts.append(fact)

        return valid_facts