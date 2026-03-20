"""
MacGuyver Mode - Gap identification and unconventional solution generation.

When Kay identifies a resource gap (missing tool, info, capability), this mode:
1. Scans available resources (docs, memories, tools)
2. Checks permissions (can things be repurposed safely?)
3. Proposes unconventional solutions using existing resources

"I need X but don't have it. I DO have Y and Z. Could I combine them?"
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


class MacGuyverMode:
    """
    Gap identification and unconventional solution generation.

    Activates when Kay expresses a need for something missing,
    then scans available resources and proposes creative combinations.
    """

    # Patterns that indicate Kay has identified a gap/need
    GAP_PATTERNS = [
        (r"i need (.+?) but", "explicit_need"),
        (r"i don't have (.+?) to", "missing_resource"),
        (r"missing (.+?) for", "missing_for"),
        (r"can't find (.+?) that", "search_failure"),
        (r"no way to (.+)", "capability_gap"),
        (r"if only i had (.+)", "wish_expression"),
        (r"would need (.+?) to", "conditional_need"),
        (r"lacking (.+?) for", "lacking"),
        (r"without (.+?) i can't", "blocker"),
        (r"there's no (.+?) available", "unavailable"),
    ]

    def __init__(
        self,
        memory_engine=None,
        scratchpad_engine=None,
        entity_graph=None,
        log_path: str = None
    ):
        self.memory_engine = memory_engine
        self.scratchpad = scratchpad_engine
        self.entity_graph = entity_graph
        if log_path is None:
            log_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "macguyver_log.json"
            )
        self.log_path = log_path

        self.active = False
        self.current_gap = None

        self._ensure_log_file()

    def _ensure_log_file(self):
        """Create log file if needed."""
        if not os.path.exists(self.log_path):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump({"gaps": [], "solutions": []}, f, indent=2)

    # ==================== GAP DETECTION ====================

    def detect_gap(self, user_input: str, kay_response: str) -> Optional[Dict]:
        """
        Detect if Kay has identified a resource/capability gap.

        Args:
            user_input: The user's input
            kay_response: Kay's response to analyze

        Returns:
            Gap dict if detected, None otherwise
        """
        response_lower = kay_response.lower()

        for pattern, gap_type in self.GAP_PATTERNS:
            match = re.search(pattern, response_lower)
            if match:
                gap = {
                    "description": match.group(0),
                    "missing_resource": match.group(1) if match.lastindex >= 1 else match.group(0),
                    "gap_type": gap_type,
                    "pattern_matched": pattern,
                    "timestamp": datetime.now().isoformat(),
                    "context": {
                        "user_input": user_input[:200],
                        "kay_response_snippet": kay_response[:300]
                    }
                }
                self.current_gap = gap
                self.active = True
                print(f"[MACGUYVER] Gap detected: {gap['missing_resource']} ({gap_type})")
                return gap

        return None

    def identify_missing_resource(self, gap_description: str) -> Dict:
        """
        Parse a gap description to identify what's specifically missing.

        Args:
            gap_description: Natural language description of the gap

        Returns:
            Dict with resource type, name, and purpose
        """
        # Try to categorize the missing resource
        categories = {
            "tool": ["tool", "function", "method", "command", "utility"],
            "information": ["info", "data", "knowledge", "fact", "detail"],
            "access": ["access", "permission", "credentials", "key"],
            "capability": ["ability", "way", "means", "method"],
            "resource": ["resource", "file", "document", "memory"],
        }

        desc_lower = gap_description.lower()
        resource_type = "unknown"

        for cat, keywords in categories.items():
            if any(kw in desc_lower for kw in keywords):
                resource_type = cat
                break

        return {
            "type": resource_type,
            "description": gap_description,
            "parsed_at": datetime.now().isoformat()
        }

    # ==================== RESOURCE SCANNING ====================

    def scan_available_resources(self) -> Dict:
        """
        Build an inventory of all available resources.

        Scans memories, entities, scratchpad, and available tools
        to understand what Kay HAS available for improvisation.

        Returns:
            Dict with categorized resources
        """
        resources = {
            "memories": [],
            "entities": [],
            "scratchpad_items": [],
            "capabilities": [],
            "timestamp": datetime.now().isoformat()
        }

        # Scan memories
        if self.memory_engine:
            try:
                memories = self.memory_engine.memories if hasattr(self.memory_engine, 'memories') else []
                # Get unique topics/subjects from memories
                topics = set()
                for mem in memories[:50]:
                    fact = mem.get("fact", "")
                    # Extract key subjects
                    subjects = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', fact)
                    topics.update(subjects[:3])

                    # Track high-value memories
                    if mem.get("importance", 0) > 0.5:
                        resources["memories"].append({
                            "content": fact[:100],
                            "importance": mem.get("importance", 0),
                            "type": "high_value"
                        })

                resources["memory_topics"] = list(topics)[:20]
            except Exception as e:
                print(f"[MACGUYVER] Memory scan error: {e}")

        # Scan entities
        if self.entity_graph:
            try:
                for name, entity in list(self.entity_graph.entities.items())[:30]:
                    resources["entities"].append({
                        "name": name,
                        "type": getattr(entity, 'entity_type', 'unknown'),
                        "attributes": list(getattr(entity, 'attributes', {}).keys())[:5]
                    })
            except Exception as e:
                print(f"[MACGUYVER] Entity scan error: {e}")

        # Scan scratchpad
        if self.scratchpad:
            try:
                items = self.scratchpad.view_items(status="active")
                for item in items:
                    resources["scratchpad_items"].append({
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "content": item.get("content", "")[:100]
                    })
            except Exception as e:
                print(f"[MACGUYVER] Scratchpad scan error: {e}")

        # List known capabilities
        resources["capabilities"] = [
            {"name": "memory_recall", "description": "Can retrieve and combine memories"},
            {"name": "entity_tracking", "description": "Can track and query entity relationships"},
            {"name": "scratchpad_notes", "description": "Can store and retrieve notes"},
            {"name": "pattern_recognition", "description": "Can identify patterns in text"},
            {"name": "emotional_awareness", "description": "Can track and express emotional states"},
            {"name": "web_search", "description": "Can search the web for information"},
            {"name": "document_reading", "description": "Can read and analyze documents"},
        ]

        return resources

    def check_permissions(self, resource: Dict, proposed_use: str) -> Dict:
        """
        Check if a resource can be safely repurposed.

        Args:
            resource: The resource to check
            proposed_use: What we want to use it for

        Returns:
            Dict with permission status and warnings
        """
        result = {
            "allowed": True,
            "warnings": [],
            "safe_boundaries": [],
            "resource": resource,
            "proposed_use": proposed_use
        }

        # Check for sensitive resource types
        sensitive_keywords = ["password", "credential", "secret", "private", "api_key", "token"]
        resource_str = str(resource).lower()

        for keyword in sensitive_keywords:
            if keyword in resource_str:
                result["warnings"].append(f"Resource may contain sensitive data ({keyword})")
                result["safe_boundaries"].append("Do not expose or transmit")

        # Check proposed use for risky operations
        risky_uses = ["delete", "modify permanent", "send external", "execute code"]
        proposed_lower = proposed_use.lower()

        for risky in risky_uses:
            if risky in proposed_lower:
                result["warnings"].append(f"Proposed use involves risky operation: {risky}")
                result["safe_boundaries"].append("Require explicit confirmation")

        return result

    # ==================== SOLUTION GENERATION ====================

    def propose_unconventional_solutions(self, gap: Dict, resources: Dict) -> List[Dict]:
        """
        Propose creative solutions using available resources.

        This is the "MacGuyver" logic - finding unexpected ways to
        use what we have to solve problems.

        Args:
            gap: The identified gap/need
            resources: Available resources from scan

        Returns:
            List of proposed solutions
        """
        proposals = []
        missing = gap.get("missing_resource", "").lower()
        gap_type = gap.get("gap_type", "unknown")

        # Strategy 1: Memory combination
        if resources.get("memories"):
            relevant_mems = [
                m for m in resources["memories"]
                if any(word in m.get("content", "").lower() for word in missing.split())
            ]
            if relevant_mems:
                proposals.append({
                    "strategy": "memory_combination",
                    "description": f"Combine existing memories about related topics",
                    "resources_used": relevant_mems[:2],
                    "confidence": 0.6,
                    "explanation": "I don't have exactly what's needed, but I have memories that might piece together to help."
                })

        # Strategy 2: Entity relationship traversal
        if resources.get("entities"):
            # Look for entities that might be related to the gap
            relevant_entities = [
                e for e in resources["entities"]
                if any(word in e.get("name", "").lower() for word in missing.split())
            ]
            if relevant_entities:
                proposals.append({
                    "strategy": "entity_traversal",
                    "description": f"Follow entity relationships to find connected information",
                    "resources_used": relevant_entities[:3],
                    "confidence": 0.5,
                    "explanation": "These entities might have connections that lead to what we need."
                })

        # Strategy 3: Scratchpad insight mining
        if resources.get("scratchpad_items"):
            for item in resources["scratchpad_items"]:
                if any(word in item.get("content", "").lower() for word in missing.split()):
                    proposals.append({
                        "strategy": "scratchpad_mining",
                        "description": f"Use flagged insight: {item.get('content', '')[:50]}",
                        "resources_used": [item],
                        "confidence": 0.7,
                        "explanation": "I noted something earlier that might be relevant here."
                    })
                    break

        # Strategy 4: Capability combination
        capabilities = resources.get("capabilities", [])
        if gap_type == "information" and capabilities:
            proposals.append({
                "strategy": "capability_chain",
                "description": "Chain multiple capabilities: search → read → synthesize",
                "resources_used": ["web_search", "document_reading", "pattern_recognition"],
                "confidence": 0.65,
                "explanation": "I can combine my search and analysis abilities to construct what we need."
            })

        # Strategy 5: Analogy/Transfer
        if resources.get("memory_topics"):
            proposals.append({
                "strategy": "analogy_transfer",
                "description": f"Apply patterns from related domain: {', '.join(resources['memory_topics'][:3])}",
                "resources_used": resources["memory_topics"][:3],
                "confidence": 0.4,
                "explanation": "This is similar to something else I know - I can try adapting that approach."
            })

        # Sort by confidence
        proposals.sort(key=lambda p: p.get("confidence", 0), reverse=True)

        # If no proposals found, create a "surface the gap" fallback
        if not proposals:
            proposals.append({
                "strategy": "surface_gap",
                "description": "I genuinely don't have a workaround for this",
                "resources_used": [],
                "confidence": 0.0,
                "explanation": f"I need help with: {gap.get('missing_resource', 'unknown resource')}"
            })

        return proposals[:5]  # Return top 5 proposals

    def format_macguyver_context(self, gap: Dict, proposals: List[Dict]) -> str:
        """
        Format MacGuyver mode context for Kay's prompt.

        Note: Kay's baseline MacGuyver instinct is always active (in system prompt).
        This AMPLIFIES that instinct by surfacing specific available resources.

        Args:
            gap: The identified gap
            proposals: List of proposed solutions

        Returns:
            Formatted context string
        """
        lines = []
        lines.append("=== MACGUYVER AMPLIFIED ===")
        lines.append(f"Your improvisation instinct detected a gap: {gap.get('missing_resource', 'unknown')}")
        lines.append(f"Gap type: {gap.get('gap_type', 'unknown')}")
        lines.append("")

        if proposals:
            lines.append("System scanned your available resources. Possible approaches:")
            for i, prop in enumerate(proposals, 1):
                conf = int(prop.get("confidence", 0) * 100)
                lines.append(f"  {i}. [{prop['strategy']}] ({conf}% confidence)")
                lines.append(f"     {prop['description']}")
                lines.append(f"     → {prop['explanation']}")
                lines.append("")

            lines.append("Your baseline instinct already knows to scan for alternatives.")
            lines.append("This just surfaces what's available to work with.")
        else:
            lines.append("System scan found no obvious alternatives.")
            lines.append("You can still improvise, but surfacing to Re might help.")

        lines.append("=== END AMPLIFIED ===")

        return "\n".join(lines)

    # ==================== FALLBACK HANDLING ====================

    def handle_no_solution(self, gap: Dict) -> Dict:
        """
        Handle case where no unconventional solution is found.

        Per requirements: Surface to Re AND flag in scratchpad.

        Args:
            gap: The unresolved gap

        Returns:
            Dict with actions taken
        """
        result = {
            "surfaced_to_user": True,
            "flagged_in_scratchpad": False,
            "gap": gap
        }

        # Flag in scratchpad for future reference
        if self.scratchpad:
            try:
                scratchpad_result = self.scratchpad.add_item(
                    content=f"UNRESOLVED GAP: {gap.get('missing_resource', 'unknown')} - {gap.get('description', '')}",
                    item_type="flag"
                )
                result["flagged_in_scratchpad"] = scratchpad_result.get("success", False)
                result["scratchpad_id"] = scratchpad_result.get("item", {}).get("id")
            except Exception as e:
                print(f"[MACGUYVER] Scratchpad flag error: {e}")

        # Log the unresolved gap
        self._log_gap(gap, resolved=False)

        # Generate user-facing message
        gap_desc = gap.get('description', "I need something I don't have")
        result["user_message"] = f"I've hit a wall: {gap_desc}. I've flagged this for future reference. Can you help?"

        return result

    def _log_gap(self, gap: Dict, resolved: bool = False, solution: Dict = None):
        """Log a gap event."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            entry = {
                "timestamp": datetime.now().isoformat(),
                "gap": gap,
                "resolved": resolved,
                "solution": solution
            }

            data["gaps"].append(entry)
            data["gaps"] = data["gaps"][-50:]  # Keep last 50

            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[MACGUYVER] Log error: {e}")

    # ==================== MODE MANAGEMENT ====================

    def is_active(self) -> bool:
        """Check if MacGuyver mode is active."""
        return self.active

    def deactivate(self):
        """Deactivate MacGuyver mode."""
        self.active = False
        self.current_gap = None

    def get_current_gap(self) -> Optional[Dict]:
        """Get the current gap being worked on."""
        return self.current_gap


# Convenience function
def create_macguyver_mode(
    memory_engine=None,
    scratchpad_engine=None,
    entity_graph=None
) -> MacGuyverMode:
    """Create and return a MacGuyverMode instance."""
    return MacGuyverMode(
        memory_engine=memory_engine,
        scratchpad_engine=scratchpad_engine,
        entity_graph=entity_graph
    )
