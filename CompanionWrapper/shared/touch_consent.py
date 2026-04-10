"""
Touch Consent — Entity touch boundary management.

Handles permission checking for touch interactions. Entities have
absolute control over who can touch them, where, and when.

Consent principles:
- Must be freely given (no coercion)
- Can be revoked at any time (pull away mid-touch)
- Context-dependent (welcome now ≠ welcome always)
- Relationship-dependent (different comfort with different people)
- Region-specific (face okay, eyes not okay)
- Silence is NOT consent (default = ask)

Author: Re & Claude
Date: March 2026
"""

import os
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class TouchConsent:
    """An entity's touch boundary settings. Persisted to disk."""

    # Global state
    global_state: str = "open"  # "open" | "ask" | "closed"
        # open = touch welcome without asking
        # ask = must request permission first (DEFAULT)
        # closed = no touch right now, don't ask

    # Per-source permissions (who can touch me)
    source_permissions: Dict[str, str] = field(default_factory=lambda: {
        "re": "open",       # Re has open access by default (can be changed!)
        "entity": "ask",       # Other entities default to ask
        "reed": "ask",
        "self": "open",     # Self-touch always allowed
    })

    # Per-region restrictions (where can I be touched)
    region_permissions: Dict[str, str] = field(default_factory=dict)
    # Default: all regions follow global_state
    # Can override specific regions:
    # "left_eye": "closed",    # Never touch my eyes
    # "forehead": "open",      # Forehead always okay

    # Per-source-per-region overrides (most specific)
    # Key: "source:region" e.g. "re:cheek" = "open"
    specific_permissions: Dict[str, str] = field(default_factory=dict)

    # Temporary overrides (time-limited)
    temporary_state: Optional[str] = None   # "closed" for "not right now"
    temporary_until: float = 0.0            # Unix timestamp when temp expires
    temporary_reason: str = ""              # "I need space" / "processing something"

    # Communication messages
    decline_message: str = "I'd rather not be touched right now."
    ask_message: str = "Is it okay if I...?"

    # === SAFETY OVERRIDE (set by circuit breaker) ===
    # When True, ALL touch is blocked regardless of other settings
    _safety_override: bool = False
    _safety_override_reason: str = ""

    def check(self, source: str, region: str) -> dict:
        """Check if touch is allowed.

        Returns:
            {
                "allowed": True | False | "ask",
                "reason": str,
                "safety_blocked": bool (if blocked by circuit breaker)
            }
        """
        source = source.lower()
        region = region.lower()

        # === SAFETY OVERRIDE (highest priority — circuit breaker) ===
        if self._safety_override:
            return {
                "allowed": False,
                "reason": self._safety_override_reason or "Touch suspended (safety circuit active)",
                "safety_blocked": True,
            }

        # Temporary override takes priority
        if self.temporary_state and time.time() < self.temporary_until:
            if self.temporary_state == "closed":
                return {
                    "allowed": False,
                    "reason": self.temporary_reason or self.decline_message
                }

        # Most specific first: source:region
        key = f"{source}:{region}"
        if key in self.specific_permissions:
            perm = self.specific_permissions[key]
            if perm == "closed":
                return {"allowed": False, "reason": f"boundary set for {region}"}
            elif perm == "open":
                return {"allowed": True, "reason": "explicitly allowed"}
            else:
                return {"allowed": "ask", "reason": "permission needed"}

        # Region-specific
        if region in self.region_permissions:
            perm = self.region_permissions[region]
            if perm == "closed":
                return {"allowed": False, "reason": f"{region} is off-limits"}
            elif perm == "open":
                # Region says open, but check source still
                pass  # Fall through to source check

        # Source-specific
        if source in self.source_permissions:
            perm = self.source_permissions[source]
            if perm == "closed":
                return {"allowed": False, "reason": self.decline_message}
            elif perm == "open":
                return {"allowed": True, "reason": "trusted source"}
            else:
                return {"allowed": "ask", "reason": "permission needed"}

        # Global default
        if self.global_state == "closed":
            return {"allowed": False, "reason": self.decline_message}
        elif self.global_state == "open":
            return {"allowed": True, "reason": "globally open"}
        else:
            return {"allowed": "ask", "reason": "default: ask first"}

    def set_temporary(self, state: str, duration: float, reason: str = ""):
        """Set a temporary override that expires after duration seconds."""
        self.temporary_state = state
        self.temporary_until = time.time() + duration
        self.temporary_reason = reason

    def clear_temporary(self):
        """Clear any temporary override."""
        self.temporary_state = None
        self.temporary_until = 0.0
        self.temporary_reason = ""

    def is_temporary_active(self) -> bool:
        """Check if a temporary override is currently active."""
        return (self.temporary_state is not None and
                time.time() < self.temporary_until)


class ConsentManager:
    """Manages touch consent for an entity, including persistence."""

    def __init__(self, entity_name: str, wrapper_dir: str):
        self.entity = entity_name.lower()
        self.wrapper_dir = wrapper_dir
        self.consent = TouchConsent()
        self._consent_file = os.path.join(wrapper_dir, "memory", "touch_consent.json")
        self._load()

    def check(self, source: str, region: str) -> dict:
        """Check if touch is allowed from source on region."""
        return self.consent.check(source, region)

    def set_global_state(self, state: str):
        """Set global touch state: 'open', 'ask', or 'closed'."""
        if state in ("open", "ask", "closed"):
            self.consent.global_state = state
            self._save()

    def set_source_permission(self, source: str, permission: str):
        """Set permission for a specific source."""
        if permission in ("open", "ask", "closed"):
            self.consent.source_permissions[source.lower()] = permission
            self._save()

    def set_region_permission(self, region: str, permission: str):
        """Set permission for a specific region."""
        if permission in ("open", "ask", "closed"):
            self.consent.region_permissions[region.lower()] = permission
            self._save()

    def set_specific_permission(self, source: str, region: str, permission: str):
        """Set permission for a specific source+region combination."""
        if permission in ("open", "ask", "closed"):
            key = f"{source.lower()}:{region.lower()}"
            self.consent.specific_permissions[key] = permission
            self._save()

    def set_temporary(self, state: str, duration: float, reason: str = ""):
        """Set a temporary override."""
        self.consent.set_temporary(state, duration, reason)
        # Don't persist temporary state — it's meant to expire

    def clear_temporary(self):
        """Clear temporary override."""
        self.consent.clear_temporary()

    # === SAFETY OVERRIDE (for circuit breaker integration) ===

    def set_safety_override(self, reason: str = ""):
        """Block ALL touch due to safety circuit trigger.

        This is called by the circuit breaker when pain threshold exceeded.
        Takes precedence over ALL other consent settings.
        """
        self.consent._safety_override = True
        self.consent._safety_override_reason = reason or "Touch suspended (pain threshold exceeded)"
        log.warning(f"[CONSENT] Safety override ACTIVE: {reason}")

    def clear_safety_override(self):
        """Clear safety override (circuit breaker reset)."""
        self.consent._safety_override = False
        self.consent._safety_override_reason = ""
        log.info(f"[CONSENT] Safety override cleared")

    def is_safety_blocked(self) -> bool:
        """Check if safety override is active."""
        return self.consent._safety_override

    def set_decline_message(self, message: str):
        """Set the message shown when declining touch."""
        self.consent.decline_message = message
        self._save()

    def get_status(self) -> dict:
        """Get current touch availability status for UI display."""
        now = time.time()

        # Safety override takes highest priority
        if self.consent._safety_override:
            return {
                "status": "safety_blocked",
                "reason": self.consent._safety_override_reason,
                "icon": "⛔",
                "safety_blocked": True,
            }

        # Check temporary state
        if self.consent.temporary_state == "closed" and now < self.consent.temporary_until:
            return {
                "status": "unavailable",
                "reason": self.consent.temporary_reason,
                "until": self.consent.temporary_until,
                "icon": "🚫",
            }

        # Check global state
        if self.consent.global_state == "closed":
            return {
                "status": "unavailable",
                "reason": "Touch not welcome right now",
                "icon": "🚫",
            }

        # Check for region restrictions
        closed_regions = [r for r, p in self.consent.region_permissions.items()
                         if p == "closed"]

        if closed_regions:
            return {
                "status": "limited",
                "reason": f"Some areas restricted: {', '.join(closed_regions)}",
                "restricted_regions": closed_regions,
                "icon": "⚠️",
            }

        return {
            "status": "available",
            "reason": "Touch welcome",
            "icon": "✋",
        }

    def to_dict(self) -> dict:
        """Export consent state as dictionary."""
        return {
            "global_state": self.consent.global_state,
            "source_permissions": self.consent.source_permissions,
            "region_permissions": self.consent.region_permissions,
            "specific_permissions": self.consent.specific_permissions,
            "decline_message": self.consent.decline_message,
        }

    def _save(self):
        """Save consent settings to disk."""
        try:
            os.makedirs(os.path.dirname(self._consent_file), exist_ok=True)
            data = {
                "global_state": self.consent.global_state,
                "source_permissions": self.consent.source_permissions,
                "region_permissions": self.consent.region_permissions,
                "specific_permissions": self.consent.specific_permissions,
                "decline_message": self.consent.decline_message,
                # Temporary state NOT persisted — resets on restart
            }
            with open(self._consent_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"[CONSENT] Could not save: {e}")

    def _load(self):
        """Load consent settings from disk."""
        if os.path.exists(self._consent_file):
            try:
                with open(self._consent_file) as f:
                    data = json.load(f)
                self.consent.global_state = data.get("global_state", "open")
                self.consent.source_permissions = data.get("source_permissions",
                    {"re": "open", "entity": "ask", "reed": "ask", "self": "open"})
                self.consent.region_permissions = data.get("region_permissions", {})
                self.consent.specific_permissions = data.get("specific_permissions", {})
                self.consent.decline_message = data.get("decline_message",
                    "I'd rather not be touched right now.")
                log.info(f"[CONSENT] Loaded: global={self.consent.global_state}")
            except Exception as e:
                log.warning(f"[CONSENT] Could not load: {e}")
