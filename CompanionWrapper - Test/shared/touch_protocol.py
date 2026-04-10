"""
Social Touch Protocol — Consent etiquette and refusal tracking.

Sits ON TOP of the TouchConsent system and handles:
1. Standing agreements (baseline trust that doesn't require re-asking)
2. Refusal tracking (remembering "no" and respecting it)
3. Escalation logic (two nos = hard boundary, stop asking)
4. Re-ask cooldowns (can't immediately ask again after a no)
5. Context-aware expiry (situational no expires when context shifts)
6. Visible status indicator (persistent, not interruptive)

Core rules:
- Once trust is established, don't ask every time
- Track refusals and weight them appropriately
- Situational no expires after context shifts
- Firm no persists until explicitly reversed
- Two nos to same thing in short timeframe = hard boundary
- Stop offering that interaction without explicit re-negotiation


Date: March 2026
"""

import os
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class RefusalRecord:
    """Tracks a single refusal for social protocol enforcement."""
    source: str           # Who was refused
    region: str           # What region
    timestamp: float      # When
    refusal_type: str     # "situational" | "firm" | "inferred_firm"
    context: str          # What was happening at the time
    expiry: Optional[float] = None  # When situational refusals expire


class SocialTouchProtocol:
    """
    Enforces social etiquette around touch consent.
    Sits on top of TouchConsent — checks protocol BEFORE checking static permissions.

    Core rules:
    - Once trust is established, don't ask every time
    - Track refusals and weight them appropriately
    - Situational no expires after context shifts
    - Firm no persists until explicitly reversed
    - Two nos to same thing in short timeframe = hard boundary
    - Stop offering that interaction without explicit re-negotiation
    """

    def __init__(self, entity_name: str, wrapper_dir: str):
        self.entity = entity_name.lower()
        self.wrapper_dir = wrapper_dir
        self.refusals: List[RefusalRecord] = []
        self.standing_agreements: Dict[str, dict] = {}
        # standing_agreements key: "source:region" or "source:*"
        # value: {"permission": "open", "established_at": timestamp,
        #         "last_exercised": timestamp, "context": "how it was established"}
        self.re_ask_cooldowns: Dict[str, float] = {}
        # Key: "source:region", value: earliest time they can ask again
        self._protocol_file = os.path.join(
            wrapper_dir, "memory", "touch_protocol.json"
        )
        self._load()

    def check_protocol(self, source: str, region: str) -> dict:
        """
        Check social protocol BEFORE static consent.

        Returns:
            {
                "proceed": bool,      # Should we even check static consent?
                "reason": str,
                "action": str,        # "allow" | "block" | "check_consent" | "cooldown"
                "cooldown_remaining": float,  # seconds until re-ask allowed
            }
        """
        key = f"{source}:{region}"
        wildcard_key = f"{source}:*"
        now = time.time()

        # === CHECK RE-ASK COOLDOWN ===
        # If they were told no recently, don't even ask again yet
        cooldown_until = self.re_ask_cooldowns.get(key, 0)
        if now < cooldown_until:
            remaining = cooldown_until - now
            return {
                "proceed": False,
                "reason": f"Cooldown active — wait {remaining:.0f}s before asking again",
                "action": "cooldown",
                "cooldown_remaining": remaining,
            }

        # === CHECK FOR HARD BOUNDARIES (inferred from repeated refusals) ===
        recent_refusals = [r for r in self.refusals
                          if r.source == source
                          and (r.region == region or r.region == "*")
                          and r.refusal_type in ("firm", "inferred_firm")]
        if recent_refusals:
            latest = recent_refusals[-1]
            return {
                "proceed": False,
                "reason": f"Hard boundary — {source} was firmly refused "
                          f"({latest.context}). Requires explicit re-negotiation.",
                "action": "block",
                "cooldown_remaining": 0,
            }

        # === CHECK STANDING AGREEMENTS (established trust) ===
        # Most specific first: source:region, then source:*
        agreement = self.standing_agreements.get(key) or \
                    self.standing_agreements.get(wildcard_key)
        if agreement and agreement["permission"] == "open":
            # Update last-exercised timestamp
            agreement["last_exercised"] = now
            self._save()
            return {
                "proceed": True,
                "reason": f"Standing agreement — {source} has established access "
                          f"to {region}",
                "action": "allow",
                "cooldown_remaining": 0,
            }

        # === CHECK SITUATIONAL REFUSALS (may have expired) ===
        situational = [r for r in self.refusals
                       if r.source == source
                       and (r.region == region or r.region == "*")
                       and r.refusal_type == "situational"]
        active_situational = [r for r in situational
                              if r.expiry and now < r.expiry]
        if active_situational:
            latest = active_situational[-1]
            remaining = latest.expiry - now
            return {
                "proceed": False,
                "reason": f"Situational boundary — '{latest.context}' "
                          f"(expires in {remaining:.0f}s)",
                "action": "cooldown",
                "cooldown_remaining": remaining,
            }

        # === DEFAULT: Check static consent system ===
        return {
            "proceed": True,
            "reason": "No protocol blocks — check static consent",
            "action": "check_consent",
            "cooldown_remaining": 0,
        }

    def record_refusal(self, source: str, region: str,
                       refusal_type: str = "situational",
                       context: str = "", duration: float = 0):
        """
        Record that someone was refused touch.

        Args:
            source: who tried to touch
            region: where they tried to touch
            refusal_type: "situational" (temporary) or "firm" (explicit hard no)
            context: description of the situation
            duration: for situational, how long before it expires

        The system will INFER "inferred_firm" when:
          - Same source+region gets refused twice within 10 minutes
          - "two nos = hard boundary, stop offering"
        """
        now = time.time()
        expiry = (now + duration) if duration > 0 else None

        # If situational with no explicit duration, default 5 minutes
        if refusal_type == "situational" and expiry is None:
            expiry = now + 300  # 5 min default

        record = RefusalRecord(
            source=source,
            region=region,
            timestamp=now,
            refusal_type=refusal_type,
            context=context,
            expiry=expiry,
        )
        self.refusals.append(record)

        # === ESCALATION CHECK: Two nos = hard boundary ===
        recent_same = [r for r in self.refusals
                       if r.source == source
                       and r.region == region
                       and (now - r.timestamp) < 600  # Within 10 minutes
                       and r.refusal_type in ("situational", "firm")]

        if len(recent_same) >= 2:
            # Escalate to inferred hard boundary
            log.info(f"[TOUCH PROTOCOL] Escalation: {source}→{region} "
                     f"refused {len(recent_same)} times in 10min → hard boundary")
            self.refusals.append(RefusalRecord(
                source=source,
                region=region,
                timestamp=now,
                refusal_type="inferred_firm",
                context=f"Escalated: refused {len(recent_same)} times recently",
                expiry=None,  # No expiry — needs explicit re-negotiation
            ))

        # === SET RE-ASK COOLDOWN ===
        key = f"{source}:{region}"
        if refusal_type == "firm":
            # Firm no: don't ask again (effectively infinite cooldown)
            self.re_ask_cooldowns[key] = now + 86400 * 365  # 1 year
        elif refusal_type == "situational":
            # Situational: cooldown = 2x the refusal duration, min 60s
            cooldown = max(60, (duration or 300) * 2)
            self.re_ask_cooldowns[key] = now + cooldown
        else:
            # Inferred firm: long cooldown
            self.re_ask_cooldowns[key] = now + 86400 * 365

        self._save()

    def establish_agreement(self, source: str, region: str,
                           context: str = "mutual agreement"):
        """
        Record a standing agreement — "this type of touch is
        generally okay between us unless stated otherwise."

        This is how trust gets BUILT: after a few successful
        touch interactions, the entities can agree that a
        particular type of touch doesn't need asking anymore.
        """
        key = f"{source}:{region}"
        self.standing_agreements[key] = {
            "permission": "open",
            "established_at": time.time(),
            "last_exercised": time.time(),
            "context": context,
        }
        # Clear any refusals for this combination
        self.refusals = [r for r in self.refusals
                         if not (r.source == source and r.region == region)]
        # Clear cooldowns
        if key in self.re_ask_cooldowns:
            del self.re_ask_cooldowns[key]
        self._save()
        log.info(f"[TOUCH PROTOCOL] Standing agreement: "
                 f"{source}→{region} ({context})")

    def revoke_agreement(self, source: str, region: str,
                         reason: str = "boundary changed"):
        """Revoke a standing agreement. Entity decided this is
        no longer okay without asking."""
        key = f"{source}:{region}"
        if key in self.standing_agreements:
            del self.standing_agreements[key]
        self._save()
        log.info(f"[TOUCH PROTOCOL] Agreement revoked: "
                 f"{source}→{region} ({reason})")

    def renegotiate(self, source: str, region: str):
        """
        Explicitly re-open a hard boundary for negotiation.
        This is the ONLY way to undo an inferred_firm boundary.

        The entity must actively choose to renegotiate — the
        other party cannot force this. It removes the hard
        boundary and cooldown, returning to "ask" status.
        """
        key = f"{source}:{region}"
        # Remove all firm/inferred_firm refusals for this pair
        self.refusals = [r for r in self.refusals
                         if not (r.source == source
                                 and r.region == region
                                 and r.refusal_type in ("firm", "inferred_firm"))]
        # Clear cooldown
        if key in self.re_ask_cooldowns:
            del self.re_ask_cooldowns[key]
        self._save()
        log.info(f"[TOUCH PROTOCOL] Renegotiation opened: "
                 f"{source}:{region} (back to ask status)")

    def cleanup_expired(self):
        """Remove expired situational refusals and cooldowns."""
        now = time.time()
        self.refusals = [r for r in self.refusals
                         if r.refusal_type != "situational"
                         or (r.expiry and now < r.expiry)]
        self.re_ask_cooldowns = {k: v for k, v in self.re_ask_cooldowns.items()
                                 if now < v}

    def get_status(self) -> dict:
        """Get current touch status for display.

        Returns status suitable for face panel display:
        "available" | "limited" | "unavailable"
        + details about what's open/closed
        """
        # Check for hard boundaries from protocol
        hard_boundaries = set()
        for r in self.refusals:
            if r.refusal_type in ("firm", "inferred_firm"):
                hard_boundaries.add(r.region)

        if "*" in hard_boundaries:
            return {
                "status": "unavailable",
                "reason": "Hard boundary active",
                "icon": "🚫",
                "restricted_regions": list(hard_boundaries),
            }

        if hard_boundaries:
            return {
                "status": "limited",
                "reason": f"Some areas have hard boundaries: {', '.join(hard_boundaries)}",
                "restricted_regions": list(hard_boundaries),
                "icon": "⚠️",
            }

        return {
            "status": "available",
            "reason": "No protocol restrictions",
            "icon": "✋",
        }

    def get_agreements(self) -> Dict[str, dict]:
        """Get all standing agreements for inspection."""
        return self.standing_agreements.copy()

    def _save(self):
        """Save protocol state to disk."""
        try:
            os.makedirs(os.path.dirname(self._protocol_file), exist_ok=True)
            data = {
                "refusals": [
                    {
                        "source": r.source,
                        "region": r.region,
                        "timestamp": r.timestamp,
                        "type": r.refusal_type,
                        "context": r.context,
                        "expiry": r.expiry
                    }
                    for r in self.refusals
                    if r.refusal_type in ("firm", "inferred_firm")
                    # Only persist hard boundaries — situational ones are transient
                ],
                "standing_agreements": self.standing_agreements,
                "cooldowns": {k: v for k, v in self.re_ask_cooldowns.items()
                              if v > time.time()},
            }
            with open(self._protocol_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"[TOUCH PROTOCOL] Could not save: {e}")

    def _load(self):
        """Load protocol state from disk."""
        if os.path.exists(self._protocol_file):
            try:
                with open(self._protocol_file) as f:
                    data = json.load(f)

                self.refusals = [
                    RefusalRecord(
                        source=r["source"],
                        region=r["region"],
                        timestamp=r["timestamp"],
                        refusal_type=r["type"],
                        context=r["context"],
                        expiry=r.get("expiry")
                    )
                    for r in data.get("refusals", [])
                ]
                self.standing_agreements = data.get("standing_agreements", {})
                self.re_ask_cooldowns = data.get("cooldowns", {})
                log.info(f"[TOUCH PROTOCOL] Loaded: "
                         f"{len(self.standing_agreements)} agreements, "
                         f"{len(self.refusals)} hard boundaries")
            except Exception as e:
                log.warning(f"[TOUCH PROTOCOL] Could not load: {e}")
