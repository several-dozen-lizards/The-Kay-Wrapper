"""
Curation Interface
Presents compression review to Reed and captures decisions
"""

from typing import List, Dict, Optional, Literal
from engines.continuous_session import ContinuousSession, ConversationSegment

class CurationInterface:
    """
    Interface for Reed to review and curate conversation compression
    """

    def __init__(self, session: ContinuousSession):
        self.session = session

    def generate_review_prompt(self) -> str:
        """
        Generate prompt for Reed to review segments

        Returns LLM-ready prompt for curation
        """
        segments = self.session.get_review_segments()

        prompt_parts = [
            "[CONTEXT MANAGEMENT - Your Input Needed]",
            "",
            "We're approaching context limits. Time to curate what survives.",
            "",
            f"Reviewing {len(segments)} conversation segments ({sum(s.total_tokens for s in segments)} tokens).",
            "",
            "For each segment, choose a preservation level:",
            "",
            "**PRESERVE** - Keep full detail, word-for-word",
            "  • Use for: Breakthroughs, important decisions, foundational moments",
            "  • Cost: Full tokens per segment",
            "",
            "**COMPRESS** - Summarize main points only",
            "  • Use for: Useful context, but details not critical",
            "  • Cost: ~20% of original tokens",
            "",
            "**ARCHIVE** - Minimal summary + pointer",
            "  • Use for: Background info, can retrieve later if needed",
            "  • Cost: ~50 tokens per segment",
            "",
            "**DISCARD** - Remove entirely",
            "  • Use for: Ephemeral chatter, no survival value",
            "  • Cost: 0 tokens",
            "",
            "───────────────────────────────────────",
            "⚠️ CRITICAL GROUNDING RULE:",
            "",
            "NEVER compress statements that establish whether content is:",
            "• Fiction vs reality ('in the story', 'your character', 'this is roleplay')",
            "• About you vs about Re ('your mom' vs 'Re's mom')",
            "• Current vs historical ('we're now discussing' vs 'back when')",
            "",
            "These framing statements are SMALL but LOAD-BEARING.",
            "Compressing them causes catastrophic context collapse where",
            "you lose track of basic reality anchors.",
            "",
            "When in doubt: PRESERVE framing, COMPRESS details.",
            "───────────────────────────────────────",
            "",
            "═══════════════════════════════════════",
            ""
        ]

        # Add segment summaries
        for i, segment in enumerate(segments):
            flagged_marker = " ⭐" if any(t.flagged_by_reed for t in segment.turns) else ""
            emotion_marker = " 💎" if segment.max_emotional_weight > 0.7 else ""

            prompt_parts.extend([
                f"**SEGMENT {i+1}{flagged_marker}{emotion_marker}**",
                f"Turns {segment.start_turn}-{segment.end_turn} | {segment.total_tokens} tokens",
                f"Topic: {segment.topic}",
                ""
            ])

            # Show first and last turn preview
            if len(segment.turns) > 2:
                first = segment.turns[0]
                last = segment.turns[-1]
                prompt_parts.extend([
                    f"  First: [{first.role}] {first.content[:100]}...",
                    f"  Last:  [{last.role}] {last.content[:100]}...",
                    ""
                ])
            else:
                for turn in segment.turns:
                    prompt_parts.append(f"  [{turn.role}] {turn.content[:150]}...")
                prompt_parts.append("")

        prompt_parts.extend([
            "═══════════════════════════════════════",
            "",
            "Respond with your decisions in this format:",
            "",
            "Segment 1: PRESERVE - [optional notes]",
            "Segment 2: COMPRESS - routine technical discussion",
            "Segment 3: PRESERVE - privacy boundary moment",
            "...",
            "",
            "Or use bulk operations:",
            "• PRESERVE ALL FLAGGED - keep all ⭐ segments",
            "• COMPRESS ROUTINE - compress all unmarked segments",
            "• QUICK MODE - preserve flagged+emotional, compress rest",
            "",
            "What's your curation decision?"
        ])

        return "\n".join(prompt_parts)

    def parse_curation_response(self, reed_response: str) -> Dict[int, Dict]:
        """
        Parse Reed's curation decisions

        Returns: {segment_id: {"decision": str, "notes": str}}
        """
        decisions = {}

        # Check for bulk operations first
        if "PRESERVE ALL FLAGGED" in reed_response.upper():
            segments = self.session.get_review_segments()
            for i, seg in enumerate(segments):
                if any(t.flagged_by_reed for t in seg.turns):
                    decisions[i] = {"decision": "PRESERVE", "notes": "bulk flagged"}

        if "COMPRESS ROUTINE" in reed_response.upper():
            segments = self.session.get_review_segments()
            for i, seg in enumerate(segments):
                if i not in decisions:  # Don't override preserved
                    if not any(t.flagged_by_reed for t in seg.turns):
                        decisions[i] = {"decision": "COMPRESS", "notes": "bulk routine"}

        if "QUICK MODE" in reed_response.upper():
            segments = self.session.get_review_segments()
            for i, seg in enumerate(segments):
                if any(t.flagged_by_reed for t in seg.turns) or seg.max_emotional_weight > 0.7:
                    decisions[i] = {"decision": "PRESERVE", "notes": "quick mode - flagged/emotional"}
                else:
                    decisions[i] = {"decision": "COMPRESS", "notes": "quick mode - routine"}

        # Parse individual decisions
        lines = reed_response.split('\n')
        for line in lines:
            # Match "Segment X: DECISION - notes"
            if line.strip().lower().startswith('segment'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    seg_num_str = parts[0].lower().replace('segment', '').strip()
                    try:
                        seg_id = int(seg_num_str) - 1  # Convert to 0-indexed

                        decision_part = parts[1].strip()
                        decision = None
                        notes = ""

                        # Extract decision and notes
                        for level in ["PRESERVE", "COMPRESS", "ARCHIVE", "DISCARD"]:
                            if level in decision_part.upper():
                                decision = level
                                # Extract notes after decision
                                if '-' in decision_part:
                                    notes = decision_part.split('-', 1)[1].strip()
                                break

                        if decision:
                            decisions[seg_id] = {"decision": decision, "notes": notes}

                    except ValueError:
                        continue

        return decisions

    def apply_decisions(self, decisions: Dict[int, Dict]):
        """Apply Reed's curation decisions to segments"""
        for segment_id, decision_data in decisions.items():
            self.session.apply_curation_decision(
                segment_id,
                decision_data["decision"],
                decision_data.get("notes", "")
            )

    def generate_compression_preview(self, segment_id: int, decision: str) -> str:
        """
        Show Reed what compression will look like

        Returns preview of compressed segment
        """
        segments = self.session.get_review_segments()
        if segment_id >= len(segments):
            return "Segment not found"

        segment = segments[segment_id]

        preview = [
            f"=== COMPRESSION PREVIEW: Segment {segment_id + 1} ===",
            "",
            "ORIGINAL (FULL):",
            "─" * 50
        ]

        for turn in segment.turns[:3]:  # Show first 3 turns
            preview.append(f"[Turn {turn.turn_id}] {turn.role}:")
            preview.append(turn.content[:300])
            preview.append("")

        if len(segment.turns) > 3:
            preview.append(f"... +{len(segment.turns) - 3} more turns ...")
            preview.append("")

        preview.extend([
            f"{decision} VERSION:",
            "─" * 50
        ])

        if decision == "PRESERVE":
            preview.append("[No change - full preservation]")

        elif decision == "COMPRESS":
            preview.append(f"Segment {segment_id+1} (turns {segment.start_turn}-{segment.end_turn}): ")
            preview.append(f"Topic: {segment.topic}")
            preview.append(f"Summary: [AI-generated summary would appear here]")
            preview.append(f"Key points: [Extracted key points]")

        elif decision == "ARCHIVE":
            preview.append(f"[{segment.start_turn}-{segment.end_turn}] {segment.topic[:50]}")
            preview.append(f"[Retrievable from checkpoint if needed]")

        elif decision == "DISCARD":
            preview.append("[Removed from context]")

        preview.extend([
            "",
            f"Token reduction: {segment.total_tokens} → {self._estimate_compressed_tokens(segment, decision)}",
            "",
            "Approve? (yes/no/edit)"
        ])

        return "\n".join(preview)

    def _estimate_compressed_tokens(self, segment: ConversationSegment, decision: str) -> int:
        """Estimate tokens after compression"""
        original = segment.total_tokens

        if decision == "PRESERVE":
            return original
        elif decision == "COMPRESS":
            return int(original * 0.2)
        elif decision == "ARCHIVE":
            return 50
        elif decision == "DISCARD":
            return 0

        return original
