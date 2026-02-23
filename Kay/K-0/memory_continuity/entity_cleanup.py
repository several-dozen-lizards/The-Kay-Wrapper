"""
Entity Graph Cleanup System
Consolidates contradictory/stale entity attributes based on recent session activity
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class AttributeConflict:
    """Represents a contradiction in entity attributes"""
    entity_id: str
    attribute_name: str
    values: List[Dict[str, Any]]  # [{"value": ..., "turn": ..., "source": ...}]
    severity: str  # "high", "moderate", "low"
    last_updated_turn: int


@dataclass
class ConsolidationResult:
    """Result of consolidating contradictory attributes"""
    entity_id: str
    attribute_name: str
    consolidated_value: Any
    confidence: float
    discarded_values: List[Any]
    reasoning: str


class EntityGraphCleaner:
    """
    Cleans up entity graph by consolidating contradictions and archiving stale data
    """

    def __init__(
        self,
        entity_graph,
        llm_client,
        stale_threshold_turns: int = 100,
        inactive_threshold_turns: int = 50
    ):
        """
        Args:
            entity_graph: Entity graph instance with attributes and relationships
            llm_client: LLM client for intelligent consolidation
            stale_threshold_turns: Turns before attribute is considered stale
            inactive_threshold_turns: Turns before entity is considered inactive
        """
        self.entity_graph = entity_graph
        self.llm = llm_client
        self.stale_threshold = stale_threshold_turns
        self.inactive_threshold = inactive_threshold_turns

    def analyze_contradictions(
        self,
        current_turn: int,
        focus_entities: Optional[List[str]] = None
    ) -> Dict[str, List[AttributeConflict]]:
        """
        Analyze entity graph for contradictions

        Args:
            current_turn: Current conversation turn
            focus_entities: Optional list of entities to focus on (if None, analyzes all)

        Returns:
            Dict mapping entity_id to list of conflicts
        """

        entities_to_check = focus_entities or self.entity_graph.get_all_entity_ids()

        conflicts_by_entity = {}

        for entity_id in entities_to_check:
            entity = self.entity_graph.get_entity(entity_id)
            if not entity:
                continue

            entity_conflicts = []

            # Check each attribute for conflicts
            for attr_name, attr_history in entity.attributes.items():
                conflict = self._detect_attribute_conflict(
                    entity_id,
                    attr_name,
                    attr_history,
                    current_turn
                )

                if conflict:
                    entity_conflicts.append(conflict)

            if entity_conflicts:
                conflicts_by_entity[entity_id] = entity_conflicts

        return conflicts_by_entity

    def _detect_attribute_conflict(
        self,
        entity_id: str,
        attr_name: str,
        attr_history: List[Dict[str, Any]],
        current_turn: int
    ) -> Optional[AttributeConflict]:
        """
        Detect if an attribute has conflicting values
        """

        if len(attr_history) <= 1:
            return None  # No conflict if only one value

        # Group by unique values
        value_groups = defaultdict(list)
        for entry in attr_history:
            value_groups[str(entry["value"])].append(entry)

        if len(value_groups) <= 1:
            return None  # All values are the same

        # Determine severity
        severity = self._determine_conflict_severity(attr_name, value_groups)

        # Find most recent update
        last_updated = max(entry["turn"] for entry in attr_history)

        conflict = AttributeConflict(
            entity_id=entity_id,
            attribute_name=attr_name,
            values=attr_history,
            severity=severity,
            last_updated_turn=last_updated
        )

        return conflict

    def _determine_conflict_severity(
        self,
        attr_name: str,
        value_groups: Dict[str, List[Dict]]
    ) -> str:
        """
        Determine severity of attribute conflict
        """

        # High severity attributes (should be consistent)
        high_severity_attrs = {
            "name", "species", "age", "gender", "eye_color",
            "home_location", "occupation", "relationship_to_user"
        }

        # Moderate severity
        moderate_severity_attrs = {
            "favorite", "preference", "goal", "interest",
            "skill", "habit", "belief"
        }

        attr_lower = attr_name.lower()

        # Check if attribute name contains high-severity keywords
        if any(keyword in attr_lower for keyword in high_severity_attrs):
            return "high"

        # Check moderate severity
        if any(keyword in attr_lower for keyword in moderate_severity_attrs):
            return "moderate"

        # Low severity (preferences can change)
        return "low"

    async def consolidate_conflict(
        self,
        conflict: AttributeConflict,
        current_turn: int,
        recent_context: str = ""
    ) -> ConsolidationResult:
        """
        Use LLM to intelligently consolidate conflicting attribute values

        Args:
            conflict: AttributeConflict to resolve
            current_turn: Current turn
            recent_context: Recent conversation context for decision-making

        Returns:
            ConsolidationResult with consolidated value
        """

        # Sort values by turn (most recent first)
        sorted_values = sorted(
            conflict.values,
            key=lambda x: x["turn"],
            reverse=True
        )

        # Format values for LLM
        values_str = "\n".join([
            f"- \"{v['value']}\" (turn {v['turn']}, {current_turn - v['turn']} turns ago, source: {v.get('source', 'unknown')})"
            for v in sorted_values[:10]  # Max 10 most recent
        ])

        prompt = f"""An entity named "{conflict.entity_id}" has conflicting values for attribute "{conflict.attribute_name}".

Conflict severity: {conflict.severity}

Conflicting values (most recent first):
{values_str}

Recent conversation context:
{recent_context[:500] if recent_context else "N/A"}

Task: Determine the most accurate value for this attribute.

Consider:
1. Recency (more recent = more likely correct)
2. Source reliability
3. Severity (high-severity attributes should be consistent)
4. Context (does recent conversation clarify this?)

If values represent evolution over time (e.g., goals changing), indicate that.
If it's a genuine error, pick the most likely correct value.

Return JSON:
{{
  "consolidated_value": "the chosen value or description of evolution",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "is_evolution": true/false,
  "discard_values": ["values to remove from history"]
}}
"""

        response = await self.llm.query(
            prompt,
            max_tokens=200,
            temperature=0.3
        )

        try:
            import json
            result = json.loads(response.strip())

            consolidation = ConsolidationResult(
                entity_id=conflict.entity_id,
                attribute_name=conflict.attribute_name,
                consolidated_value=result["consolidated_value"],
                confidence=result["confidence"],
                discarded_values=result.get("discard_values", []),
                reasoning=result["reasoning"]
            )

            return consolidation

        except json.JSONDecodeError:
            # Fallback: use most recent value
            return ConsolidationResult(
                entity_id=conflict.entity_id,
                attribute_name=conflict.attribute_name,
                consolidated_value=sorted_values[0]["value"],
                confidence=0.5,
                discarded_values=[],
                reasoning="Fallback: using most recent value"
            )

    def apply_consolidation(
        self,
        consolidation: ConsolidationResult,
        current_turn: int
    ):
        """
        Apply consolidation result to entity graph
        """

        entity = self.entity_graph.get_entity(consolidation.entity_id)
        if not entity:
            return

        # Update attribute with consolidated value
        entity.attributes[consolidation.attribute_name] = [{
            "value": consolidation.consolidated_value,
            "turn": current_turn,
            "source": "consolidated",
            "confidence": consolidation.confidence,
            "consolidation_reasoning": consolidation.reasoning
        }]

        # Archive discarded values
        if consolidation.discarded_values:
            if not hasattr(entity, "archived_attributes"):
                entity.archived_attributes = {}

            archive_key = f"{consolidation.attribute_name}_archived_{current_turn}"
            entity.archived_attributes[archive_key] = {
                "discarded_values": consolidation.discarded_values,
                "reason": consolidation.reasoning,
                "archived_turn": current_turn
            }

    async def clean_goal_contradictions(
        self,
        entity_id: str,
        current_turn: int,
        max_goals: int = 5
    ) -> Dict[str, Any]:
        """
        Special handler for goal contradictions (741 in your case!)

        Args:
            entity_id: Entity with goal contradictions
            current_turn: Current turn
            max_goals: Maximum number of goals to keep

        Returns:
            Cleanup report
        """

        entity = self.entity_graph.get_entity(entity_id)
        if not entity:
            return {"error": "Entity not found"}

        # Get all goal-related attributes
        goal_attrs = {
            k: v for k, v in entity.attributes.items()
            if "goal" in k.lower()
        }

        if not goal_attrs:
            return {"message": "No goal attributes found"}

        # Collect all goal values with metadata
        all_goals = []
        for attr_name, attr_history in goal_attrs.items():
            for entry in attr_history:
                all_goals.append({
                    "attribute_name": attr_name,
                    "value": entry["value"],
                    "turn": entry["turn"],
                    "age": current_turn - entry["turn"],
                    "source": entry.get("source", "unknown")
                })

        # Sort by recency
        all_goals.sort(key=lambda g: g["turn"], reverse=True)

        # Use LLM to consolidate to top N goals
        goals_str = "\n".join([
            f"- {g['value']} (turn {g['turn']}, {g['age']} turns ago)"
            for g in all_goals[:20]  # Show top 20 for context
        ])

        prompt = f"""Entity "{entity_id}" has {len(all_goals)} goal statements (way too many!).

Recent goals (most recent first):
{goals_str}

Consolidate these into the {max_goals} most important, current, and distinct goals.

Return JSON:
{{
  "consolidated_goals": [
    {{"goal": "goal description", "priority": 1-5}},
    ...
  ],
  "archived_count": number_of_goals_archived,
  "reasoning": "brief explanation of consolidation logic"
}}
"""

        response = await self.llm.query(
            prompt,
            max_tokens=300,
            temperature=0.3
        )

        try:
            import json
            result = json.loads(response.strip())

            # Clear old goal attributes
            for attr_name in goal_attrs.keys():
                del entity.attributes[attr_name]

            # Set consolidated goals
            for idx, goal in enumerate(result["consolidated_goals"][:max_goals]):
                entity.attributes[f"goal_{idx+1}"] = [{
                    "value": goal["goal"],
                    "turn": current_turn,
                    "source": "consolidated",
                    "priority": goal.get("priority", 3)
                }]

            # Archive old goals
            if not hasattr(entity, "archived_attributes"):
                entity.archived_attributes = {}

            entity.archived_attributes[f"goals_archived_{current_turn}"] = {
                "original_count": len(all_goals),
                "consolidated_to": len(result["consolidated_goals"]),
                "reasoning": result["reasoning"],
                "archived_turn": current_turn
            }

            return {
                "original_goal_count": len(all_goals),
                "consolidated_to": len(result["consolidated_goals"]),
                "archived": len(all_goals) - len(result["consolidated_goals"]),
                "reasoning": result["reasoning"]
            }

        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response"}

    def archive_stale_entities(
        self,
        current_turn: int
    ) -> Dict[str, List[str]]:
        """
        Archive entities that haven't been mentioned in a long time

        Returns:
            Dict with archived entity IDs by reason
        """

        archived = {
            "stale": [],      # Not mentioned in stale_threshold turns
            "inactive": [],   # Not mentioned in inactive_threshold turns
        }

        for entity_id in self.entity_graph.get_all_entity_ids():
            entity = self.entity_graph.get_entity(entity_id)

            # Find most recent attribute update
            most_recent_turn = 0
            for attr_history in entity.attributes.values():
                for entry in attr_history:
                    most_recent_turn = max(most_recent_turn, entry["turn"])

            age = current_turn - most_recent_turn

            if age > self.stale_threshold:
                archived["stale"].append(entity_id)
                self._archive_entity(entity_id, current_turn, "stale")
            elif age > self.inactive_threshold:
                archived["inactive"].append(entity_id)
                # Don't fully archive, just mark as inactive
                entity.metadata = entity.metadata or {}
                entity.metadata["status"] = "inactive"
                entity.metadata["marked_inactive_turn"] = current_turn

        return archived

    def _archive_entity(
        self,
        entity_id: str,
        current_turn: int,
        reason: str
    ):
        """
        Move entity to archived state
        """

        entity = self.entity_graph.get_entity(entity_id)
        if not entity:
            return

        # Mark as archived
        entity.metadata = entity.metadata or {}
        entity.metadata["status"] = "archived"
        entity.metadata["archived_turn"] = current_turn
        entity.metadata["archive_reason"] = reason

        # Optionally move to separate archived collection
        # (Implementation depends on your entity graph structure)

    def get_cleanup_summary(
        self,
        current_turn: int
    ) -> Dict[str, Any]:
        """
        Generate summary of entity graph health
        """

        all_entities = self.entity_graph.get_all_entity_ids()

        total_contradictions = 0
        high_severity_count = 0
        entities_with_issues = 0

        conflicts = self.analyze_contradictions(current_turn)

        for entity_id, entity_conflicts in conflicts.items():
            if entity_conflicts:
                entities_with_issues += 1
                total_contradictions += len(entity_conflicts)
                high_severity_count += sum(
                    1 for c in entity_conflicts if c.severity == "high"
                )

        # Count stale entities
        stale_count = 0
        inactive_count = 0

        for entity_id in all_entities:
            entity = self.entity_graph.get_entity(entity_id)
            most_recent_turn = 0
            for attr_history in entity.attributes.values():
                for entry in attr_history:
                    most_recent_turn = max(most_recent_turn, entry["turn"])

            age = current_turn - most_recent_turn
            if age > self.stale_threshold:
                stale_count += 1
            elif age > self.inactive_threshold:
                inactive_count += 1

        return {
            "total_entities": len(all_entities),
            "entities_with_contradictions": entities_with_issues,
            "total_contradictions": total_contradictions,
            "high_severity_contradictions": high_severity_count,
            "stale_entities": stale_count,
            "inactive_entities": inactive_count,
            "health_score": self._calculate_health_score(
                len(all_entities),
                entities_with_issues,
                high_severity_count,
                stale_count
            )
        }

    def _calculate_health_score(
        self,
        total: int,
        with_issues: int,
        high_severity: int,
        stale: int
    ) -> float:
        """
        Calculate entity graph health score (0.0-1.0, higher is better)
        """

        if total == 0:
            return 1.0

        # Penalize contradictions and staleness
        contradiction_penalty = (with_issues / total) * 0.5
        severity_penalty = (high_severity / total) * 0.3
        staleness_penalty = (stale / total) * 0.2

        health = 1.0 - (contradiction_penalty + severity_penalty + staleness_penalty)

        return max(0.0, min(1.0, health))
