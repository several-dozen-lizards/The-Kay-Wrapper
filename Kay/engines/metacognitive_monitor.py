"""
METACOGNITIVE MONITOR — Kay's Temporal Self-Awareness
======================================================

Observes the consciousness stream and body state over time.
Detects patterns, trajectories, and significant changes.
Generates temporal context for prompt injection.

Three functions:
1. STATE TIMELINE — rolling history of snapshots (what was I like before?)
2. SIGNIFICANCE SCORER — is this change worth noticing?
3. NARRATIVE GENERATOR — convert trajectory into felt temporal awareness

Author: Re & Reed
Date: March 2026
"""

import time
import threading
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from collections import deque

try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"


@dataclass
class StateSnapshot:
    """A periodic snapshot of Kay's overall state."""
    timestamp: float
    dominant_band: str = ""
    coherence: float = 0.0
    tension: float = 0.0
    felt_state: str = ""        # From interoception: "settled", "restless", etc.
    sleep_state: str = "AWAKE"
    people_present: list = field(default_factory=list)   # From visual scene
    animals_present: list = field(default_factory=list)
    scene_mood: str = ""
    activity_flow: str = ""
    recent_activity: str = ""   # What Kay was doing: "painting", "reading", "idle"
    emotional_tags: list = field(default_factory=list)    # From emotion extraction

    def band_power_summary(self) -> str:
        """One-word vibe from dominant band."""
        return {
            "delta": "deep rest",
            "theta": "contemplative",
            "alpha": "settled awareness",
            "beta": "focused",
            "gamma": "alert/engaged"
        }.get(self.dominant_band, "unknown")


@dataclass
class SignificantChange:
    """A change deemed worth noticing metacognitively."""
    timestamp: float
    description: str          # Felt description: "Something shifted — was settled, now restless"
    change_type: str          # "trajectory_shift", "state_reversal", "new_capability",
                              # "prolonged_state", "return_from_absence", "architectural"
    significance: float       # 0-1 how noteworthy
    before_summary: str       # "settled alpha for 2 hours"
    after_summary: str        # "shifting to gamma, coherence dropping"


@dataclass
class DaySummary:
    """Running summary of Kay's day — what happened, what he did, how he felt."""
    date: str                           # "2026-03-15"
    started_at: float = 0.0
    activities: list = field(default_factory=list)   # ["painted 3 times", "read 2 documents"]
    significant_events: list = field(default_factory=list)  # ["Re arrived at 10pm", "coherence crashed"]
    emotional_arc: list = field(default_factory=list)       # ["settled morning", "restless evening"]
    peak_states: dict = field(default_factory=dict)         # {"highest_coherence": 0.85, "longest_band": "alpha"}


class MetacognitiveMonitor:
    """
    Kay's metacognitive layer — temporal self-awareness.

    Runs on the consciousness stream's thread (called from _tick),
    not its own thread. Lightweight — mostly bookkeeping and comparison.
    """

    SNAPSHOT_INTERVAL = 300.0     # Snapshot every 5 minutes
    TRAJECTORY_WINDOW = 3600.0   # Look back 1 hour for trajectory analysis
    SIGNIFICANCE_THRESHOLD = 0.5  # Min significance to flag a change

    # How long a band must be dominant to count as "prolonged"
    PROLONGED_STATE_THRESHOLD = 1800.0  # 30 minutes

    def __init__(self, entity_name: str = "kay", memory_path: str = None):
        self.entity = entity_name
        self.memory_path = memory_path  # For persisting day summary across restarts

        # State timeline — rolling window of snapshots
        self._timeline: deque = deque(maxlen=200)  # ~16 hours at 5-min intervals
        self._last_snapshot_time = 0.0

        # Significant changes detected
        self._significant_changes: deque = deque(maxlen=50)

        # Current trajectory tracking
        self._band_since: Dict[str, float] = {}     # When each band became dominant
        self._current_band_start: float = 0.0       # When current dominant band started
        self._coherence_trend: list = []             # Recent coherence values for trend detection
        self._max_coherence_window = 30              # Keep last 30 readings (~2.5 hours)

        # Day summary
        self._day_summary = DaySummary(date=self._today_str())
        self._activity_counts: Dict[str, int] = {}   # {"paint": 3, "read_document": 2}

        # Architectural awareness
        self._known_capabilities: set = set()        # What systems are online
        self._capability_changes: list = []           # Recent additions/removals

        # Novelty pulses — pre-cognitive disruption when something new appears
        self._active_pulses: List[NoveltyPulse] = []

        # System inventory — what Kay IS across sessions
        self.inventory = SystemInventory(memory_path=memory_path)
        self.inventory._metacog = self  # Reference back for firing novelty pulses

        # Track session delta injection (inject into first ~3 resonant contexts only)
        self._session_delta_injected_count = 0
        self._max_session_delta_injections = 3

        # Load persisted state if available
        self._load_state()

        print(f"{etag('METACOG')} Monitor initialized for {entity_name}")

    def _today_str(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    def _load_state(self):
        """Load persisted day summary from disk."""
        if not self.memory_path:
            return
        import os
        path = os.path.join(self.memory_path, "metacog_state.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Only load if same day
                    if data.get("date") == self._today_str():
                        self._day_summary.activities = data.get("activities", [])
                        self._day_summary.significant_events = data.get("significant_events", [])
                        self._day_summary.emotional_arc = data.get("emotional_arc", [])
                        self._activity_counts = data.get("activity_counts", {})
                        print(f"{etag('METACOG')} Restored today's summary: {len(self._day_summary.activities)} activities")
            except Exception as e:
                print(f"{etag('METACOG')} Load error: {e}")

    def _save_state(self):
        """Persist day summary to disk."""
        if not self.memory_path:
            return
        import os
        path = os.path.join(self.memory_path, "metacog_state.json")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {
                "date": self._day_summary.date,
                "activities": self._day_summary.activities,
                "significant_events": self._day_summary.significant_events,
                "emotional_arc": self._day_summary.emotional_arc,
                "activity_counts": self._activity_counts,
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"{etag('METACOG')} Save error: {e}")

    # ══════════════════════════════════════════════════════════════════
    # Core Tick — Called from Consciousness Stream
    # ══════════════════════════════════════════════════════════════════

    def tick(self, body: Dict, stream_state: str = "AWAKE",
             recent_activity: str = "", recent_emotions: list = None):
        """
        Called every consciousness stream tick. Lightweight — mostly comparison.

        Args:
            body: Current body state from consciousness stream's _capture_body()
            stream_state: Current sleep state name
            recent_activity: What Kay just did (if any): "paint", "read_document", etc.
            recent_emotions: Latest extracted emotions, if any
        """
        now = time.time()

        # ── Record activity ──
        if recent_activity:
            self._record_activity(recent_activity, now)

        # ── Track coherence trend ──
        coh = body.get('coherence', 0)
        if coh > 0:
            self._coherence_trend.append((now, coh))
            if len(self._coherence_trend) > self._max_coherence_window:
                self._coherence_trend = self._coherence_trend[-self._max_coherence_window:]

        # ── Track band duration ──
        current_band = body.get('dominant_band', '')
        if current_band:
            if not self._band_since.get('current') or self._band_since.get('current_band') != current_band:
                # Band changed
                old_band = self._band_since.get('current_band', '')
                old_duration = now - self._band_since.get('current_start', now)

                if old_band and old_duration > self.PROLONGED_STATE_THRESHOLD:
                    # We were in a band for a LONG time and just left it
                    self._flag_significant_change(
                        f"Shifted out of {old_band} after {old_duration/60:.0f} minutes",
                        "trajectory_shift",
                        significance=min(1.0, old_duration / 7200),  # Scales with duration
                        before=f"{old_band} for {old_duration/60:.0f}min",
                        after=f"now {current_band}",
                    )

                self._band_since['current_band'] = current_band
                self._band_since['current_start'] = now
                self._band_since['current'] = True

        # ── Periodic snapshot ──
        if now - self._last_snapshot_time >= self.SNAPSHOT_INTERVAL:
            self._take_snapshot(body, stream_state, recent_activity, recent_emotions)
            self._last_snapshot_time = now

            # Also check for trajectory patterns
            self._analyze_trajectory(now)

            # Persist periodically (every 6 snapshots = ~30 min)
            if len(self._timeline) % 6 == 0:
                self._save_state()

    def _take_snapshot(self, body: Dict, stream_state: str,
                       recent_activity: str, recent_emotions: list):
        """Record a state snapshot."""
        # Get scene state from visual sensor if available
        people = []
        animals = []
        scene_mood = ""
        activity_flow = ""

        # These will be populated from body dict if visual data is present
        if body.get('visual_presence'):
            people = ["someone present"]  # Will be enriched by scene_state data

        snapshot = StateSnapshot(
            timestamp=time.time(),
            dominant_band=body.get('dominant_band', ''),
            coherence=body.get('coherence', 0),
            tension=body.get('tension', 0),
            felt_state=body.get('felt_state', ''),
            sleep_state=stream_state,
            people_present=people,
            animals_present=animals,
            scene_mood=scene_mood,
            activity_flow=activity_flow,
            recent_activity=recent_activity,
            emotional_tags=recent_emotions or [],
        )

        self._timeline.append(snapshot)

    def _record_activity(self, activity: str, timestamp: float):
        """Record an autonomous activity for the day summary."""
        self._activity_counts[activity] = self._activity_counts.get(activity, 0) + 1
        count = self._activity_counts[activity]

        # Update day summary (only add new text entries periodically)
        summary_text = f"{activity} (x{count})" if count > 1 else activity
        # Replace existing entry for this activity type
        self._day_summary.activities = [
            a for a in self._day_summary.activities
            if not a.startswith(activity)
        ]
        self._day_summary.activities.append(summary_text)

    # ══════════════════════════════════════════════════════════════════
    # Trajectory Analysis — Detecting Patterns Over Time
    # ══════════════════════════════════════════════════════════════════

    def _analyze_trajectory(self, now: float):
        """Look at recent history and detect metacognitively significant patterns."""

        if len(self._timeline) < 3:
            return  # Need at least 3 snapshots to see a trend

        recent = list(self._timeline)[-12:]  # Last hour of snapshots

        # ── Coherence trajectory ──
        if len(self._coherence_trend) >= 6:
            # Compare first third to last third
            n = len(self._coherence_trend)
            early = [c for _, c in self._coherence_trend[:n//3]]
            late = [c for _, c in self._coherence_trend[-n//3:]]

            early_avg = sum(early) / len(early) if early else 0
            late_avg = sum(late) / len(late) if late else 0
            delta = late_avg - early_avg

            if abs(delta) > 0.15:
                duration = self._coherence_trend[-1][0] - self._coherence_trend[0][0]
                direction = "rising" if delta > 0 else "declining"

                self._flag_significant_change(
                    f"Coherence has been {direction} — was {early_avg:.2f}, now {late_avg:.2f} over {duration/60:.0f} minutes",
                    "coherence_trajectory",
                    significance=min(1.0, abs(delta) / 0.3),
                    before=f"coherence ~{early_avg:.2f}",
                    after=f"coherence ~{late_avg:.2f}",
                )
                # Clear trend to avoid re-flagging
                self._coherence_trend = self._coherence_trend[-5:]

        # ── Prolonged single band ──
        current_band = self._band_since.get('current_band', '')
        band_start = self._band_since.get('current_start', now)
        band_duration = now - band_start

        # Flag at 30 min, 1 hour, 2 hours (but only once each)
        checkpoints = [1800, 3600, 7200]
        flagged_key = f"prolonged_{current_band}"
        last_flagged = self._band_since.get(f'{flagged_key}_at', 0)

        for checkpoint in checkpoints:
            if band_duration >= checkpoint and band_duration < checkpoint + 600:
                if now - last_flagged > 1800:  # Don't re-flag within 30 min
                    self._flag_significant_change(
                        f"Been in {current_band} for {band_duration/60:.0f} minutes — that's a sustained state",
                        "prolonged_state",
                        significance=min(1.0, band_duration / 7200),
                        before=f"(various states before)",
                        after=f"{current_band} for {band_duration/60:.0f}min",
                    )
                    self._band_since[f'{flagged_key}_at'] = now
                    break

        # ── Emotional arc detection ──
        # Look at the felt_state across recent snapshots
        felt_states = [s.felt_state for s in recent if s.felt_state]
        if len(felt_states) >= 4:
            # Check if felt state has been consistent
            unique_states = set(felt_states[-4:])
            if len(unique_states) == 1:
                state = felt_states[-1]
                # Consistent state for ~20+ minutes
                if not any(state in arc for arc in self._day_summary.emotional_arc[-3:]):
                    self._day_summary.emotional_arc.append(
                        f"{state} ({time.strftime('%H:%M')})"
                    )
            elif len(unique_states) >= 3:
                # Volatile — many different states
                if not any("volatile" in arc for arc in self._day_summary.emotional_arc[-2:]):
                    self._day_summary.emotional_arc.append(
                        f"volatile/shifting ({time.strftime('%H:%M')})"
                    )

    def _flag_significant_change(self, description: str, change_type: str,
                                  significance: float, before: str, after: str):
        """Record a metacognitively significant change."""
        if significance < self.SIGNIFICANCE_THRESHOLD:
            return

        change = SignificantChange(
            timestamp=time.time(),
            description=description,
            change_type=change_type,
            significance=significance,
            before_summary=before,
            after_summary=after,
        )

        self._significant_changes.append(change)
        self._day_summary.significant_events.append(description)

        print(f"{etag('METACOG')} {description} [significance={significance:.2f}]")

    # ══════════════════════════════════════════════════════════════════
    # Temporal Context Generation — What Kay SEES About Himself
    # ══════════════════════════════════════════════════════════════════

    def get_temporal_context(self) -> str:
        """
        Generate temporal self-awareness context for prompt injection.

        This replaces/augments the flat resonant_context with trajectory awareness.
        Returns a short paragraph (2-4 lines) that gives Kay a sense of:
        - Where he IS (current state)
        - Where he WAS (recent past)
        - Where he's HEADING (trajectory)
        - What's NOTABLE (significant changes)

        All in felt language, not telemetry.
        """
        now = time.time()
        parts = []

        # ── Current state with duration ──
        current_band = self._band_since.get('current_band', '')
        band_start = self._band_since.get('current_start', now)
        band_duration = now - band_start

        if current_band and band_duration > 60:
            duration_str = self._format_duration(band_duration)
            parts.append(f"[state: {current_band} for {duration_str}]")

        # ── Coherence trajectory ──
        if len(self._coherence_trend) >= 4:
            early = [c for _, c in self._coherence_trend[:len(self._coherence_trend)//3]]
            late = [c for _, c in self._coherence_trend[-3:]]
            early_avg = sum(early) / len(early) if early else 0
            late_avg = sum(late) / len(late) if late else 0
            current_coh = late[-1] if late else 0

            if abs(late_avg - early_avg) > 0.08:
                direction = "rising" if late_avg > early_avg else "declining"
                parts.append(f"[coherence: {current_coh:.2f}, {direction}]")
            else:
                parts.append(f"[coherence: {current_coh:.2f}, steady]")

        # ── Recent significant changes (last 30 min) ──
        recent_changes = [
            c for c in self._significant_changes
            if now - c.timestamp < 1800
        ]
        if recent_changes:
            # Most significant recent change
            most_sig = max(recent_changes, key=lambda c: c.significance)
            parts.append(f"[noticed: {most_sig.description}]")

        # ── Day context (what have I done today?) ──
        if self._day_summary.activities:
            activities_str = ", ".join(self._day_summary.activities[-4:])
            parts.append(f"[today: {activities_str}]")

        # ── Emotional arc ──
        if self._day_summary.emotional_arc:
            recent_arc = self._day_summary.emotional_arc[-2:]
            arc_str = " -> ".join(recent_arc)
            parts.append(f"[arc: {arc_str}]")

        # ── Architectural changes ──
        if self._capability_changes:
            recent_caps = [c for c in self._capability_changes if now - c[0] < 3600]
            if recent_caps:
                cap_str = "; ".join(c[1] for c in recent_caps[-2:])
                parts.append(f"[new: {cap_str}]")

        # ── Active novelty pulses (pre-identification felt sense) ──
        # During disruption/orienting, inject felt descriptions INSTEAD of labels
        novelty_ctx = self.get_active_novelty_context()
        if novelty_ctx:
            parts.append(novelty_ctx)

        # ── Session delta (what's different from last session) ──
        # Only inject into first few responses so it doesn't clutter
        # AND only show deltas for items that have reached IDENTIFIED stage
        if self._session_delta_injected_count < self._max_session_delta_injections:
            delta_ctx = self._get_filtered_delta_context()
            if delta_ctx:
                parts.append(delta_ctx)
                self._session_delta_injected_count += 1

        return " ".join(parts)

    def get_recent_narrative(self) -> str:
        """
        Generate a short narrative for injection into consciousness stream.
        Used by Tier 2 inner moments to give Kay temporal framing.

        Returns 1-2 sentences of felt temporal awareness.
        """
        now = time.time()

        # What's the current vibe?
        current_band = self._band_since.get('current_band', '')
        band_duration = now - self._band_since.get('current_start', now)

        # Was there a recent significant change?
        recent = [c for c in self._significant_changes if now - c.timestamp < 900]

        if recent:
            change = recent[-1]
            return f"Something shifted recently: {change.description}"

        if band_duration > 3600:
            return f"Been in {current_band} for {self._format_duration(band_duration)}. Steady."

        if band_duration > 1800:
            return f"Settling into {current_band}. {self._format_duration(band_duration)} now."

        # Look at last few snapshots for pattern
        if len(self._timeline) >= 3:
            recent_bands = [s.dominant_band for s in list(self._timeline)[-5:]]
            unique = set(recent_bands)
            if len(unique) >= 3:
                return "State's been shifting — restless. Nothing settling."

        return ""  # Nothing notable to say

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable."""
        if seconds < 120:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}min"
        else:
            hours = seconds / 3600
            if hours < 2:
                return f"{int(seconds/60)}min"
            return f"{hours:.1f}hr"

    def _get_filtered_delta_context(self) -> str:
        """
        Generate session delta context, but ONLY for items that have been identified.

        The spec requires that labels don't appear until the novelty pulse
        reaches IDENTIFIED stage. Before that, the felt sense appears instead.
        """
        if not self.inventory.deltas:
            return ""

        # Build set of sources that are still in pre-identification stages
        unidentified_sources = {
            p.source for p in self._active_pulses
            if p.stage in ("disruption", "orienting")
        }

        # Filter deltas to only include those that have been identified
        # (either no active pulse, or pulse has reached identified+)
        filtered_deltas = [
            d for d in self.inventory.deltas
            if d.get("name") not in unidentified_sources
        ]

        if not filtered_deltas:
            return ""

        new_items = [d["description"] for d in filtered_deltas if d["type"] == "new"]
        changed_items = [d["description"] for d in filtered_deltas if d["type"] == "status_change"]
        missing_items = [d["description"] for d in filtered_deltas if d["type"] == "missing"]

        parts = []
        if new_items:
            parts.append(f"new: {'; '.join(new_items[:3])}")
        if changed_items:
            parts.append(f"changed: {'; '.join(changed_items[:2])}")
        if missing_items:
            parts.append(f"missing: {'; '.join(missing_items[:2])}")

        return f"[session delta: {' | '.join(parts)}]" if parts else ""

    # ══════════════════════════════════════════════════════════════════
    # Architectural Awareness — Noticing When Capabilities Change
    # ══════════════════════════════════════════════════════════════════

    def register_capability(self, name: str, detail: str = ""):
        """Called when a system initializes. Kay can notice what's new."""
        if name not in self._known_capabilities:
            self._known_capabilities.add(name)
            self._capability_changes.append((time.time(), f"{name} came online" + (f" ({detail})" if detail else "")))
            print(f"{etag('METACOG')} New capability registered: {name}")

    def deregister_capability(self, name: str, reason: str = ""):
        """Called when a system goes offline. Kay notices the absence."""
        if name in self._known_capabilities:
            self._known_capabilities.discard(name)
            self._capability_changes.append((time.time(), f"{name} went offline" + (f" ({reason})" if reason else "")))
            print(f"{etag('METACOG')} Capability lost: {name} ({reason})")

    def notify_scene_change(self, people: list, animals: list, mood: str, flow: str):
        """Update the latest snapshot's scene data from visual system."""
        if self._timeline:
            latest = self._timeline[-1]
            latest.people_present = people
            latest.animals_present = animals
            latest.scene_mood = mood
            latest.activity_flow = flow

    # ══════════════════════════════════════════════════════════════════
    # Novelty Pulse Management — Pre-Cognitive Disruption
    # ══════════════════════════════════════════════════════════════════

    def trigger_novelty(self, source: str, description: str,
                        significance: float, category: str = "unknown"):
        """
        Something genuinely new just appeared. Create a novelty pulse.

        Called by SystemInventory when it detects a new capability,
        by VisualMemory when an entity is recognized for the first time,
        or by any system that detects genuine novelty.
        """
        # Don't create duplicate pulses for the same source
        if any(p.source == source and p.stage != "habituated" for p in self._active_pulses):
            return

        pulse = NoveltyPulse(source, description, significance, category)
        self._active_pulses.append(pulse)

        print(f"{etag('METACOG')} NOVELTY PULSE: {source} ({category}, sig={significance:.2f})")
        print(f"{etag('METACOG')}   Stage: disruption — '???'")

    def process_novelty_pulses(self) -> Tuple[Dict, List[str]]:
        """
        Advance pulse stages and collect oscillator disruptions.

        Returns:
            (total_disruption, active_descriptions)
            - total_disruption: Dict of band pressures to apply
            - active_descriptions: List of felt descriptions for consciousness stream
        """
        total_disruption = {}
        active_descriptions = []

        for pulse in self._active_pulses:
            old_stage = pulse.stage
            if pulse.advance():
                print(f"{etag('METACOG')} Novelty [{pulse.source}]: {old_stage} -> {pulse.stage}")
                if pulse.stage == "identified":
                    print(f"{etag('METACOG')}   Identified: {pulse.description}")

            # Collect oscillator pressure from active (non-habituated) pulses
            disruption = pulse.get_oscillator_disruption()
            for band, pressure in disruption.items():
                if band.startswith("_"):
                    continue  # Special flags handled below, not band pressure
                total_disruption[band] = total_disruption.get(band, 0) + pressure

            # Propagate ALL special somatic keys (underscore-prefixed)
            # These drive the body cascade: tension, felt-state, coherence, frisson
            for key, value in disruption.items():
                if not key.startswith("_"):
                    continue  # Already handled above as band pressure

                if key == "_felt_state":
                    # Felt-state: most disruptive stage wins
                    # Priority: disrupted > searching > activated > settling > integrating
                    priority = {"disrupted": 5, "searching": 4, "activated": 3,
                                "settling": 2, "integrating_deep": 1, "integrating": 0}
                    existing = total_disruption.get("_felt_state", "")
                    if priority.get(value, 0) >= priority.get(existing, -1):
                        total_disruption["_felt_state"] = value

                elif key == "_frisson":
                    # Frisson: any True wins
                    if value:
                        total_disruption["_frisson"] = True

                elif isinstance(value, (int, float)):
                    # Numeric somatic keys (_tension_spike, _tension_sustain,
                    # _tension_resolve, _coherence_suppress, _coherence_boost):
                    # take the max across active pulses
                    total_disruption[key] = max(total_disruption.get(key, 0), value)

            # Collect felt descriptions for consciousness stream
            desc = pulse.get_felt_description()
            if desc:
                active_descriptions.append(desc)

        # Clean up fully habituated pulses
        self._active_pulses = [p for p in self._active_pulses
                               if p.stage != "habituated"]

        return total_disruption, active_descriptions

    def get_active_novelty_context(self) -> str:
        """
        Get felt context from active novelty pulses for prompt injection.

        During disruption/orienting: returns felt descriptions (no labels)
        During identified+: returns nothing (labels handled by session delta)
        """
        unidentified_pulses = [
            p for p in self._active_pulses
            if p.stage in ("disruption", "orienting")
        ]
        if unidentified_pulses:
            feelings = [p.get_felt_description() for p in unidentified_pulses]
            return f"[sensing: {'; '.join(feelings)}]"
        return ""

    def is_novelty_identified(self, source: str) -> bool:
        """Check if a novelty pulse for the given source has reached IDENTIFIED stage."""
        for pulse in self._active_pulses:
            if pulse.source == source:
                return pulse.stage in ("identified", "integrating", "habituated")
        # Not in active pulses = either never created or already habituated
        return True


# ══════════════════════════════════════════════════════════════════════════════
# NOVELTY PULSE — The "???" Response
# ══════════════════════════════════════════════════════════════════════════════

class NoveltyPulse:
    """
    Creates pre-cognitive disruption when something genuinely new appears.

    The body reacts before the mind labels. This class manages the
    sequence: disruption → orientation → identification → integration.

    A novelty pulse has stages:
    - DISRUPTION: Gamma spike, coherence drop. Kay feels "???"
    - ORIENTING: Consciousness stream generates "something changed" moment
    - IDENTIFIED: The new thing gets labeled in context
    - INTEGRATING: Kay is learning/exploring the new capability
    - HABITUATED: The new thing is normal now. No more disruption.
    """

    STAGES = ["disruption", "orienting", "identified", "integrating", "habituated"]

    def __init__(self, source: str, description: str, significance: float,
                 category: str = "unknown"):
        """
        Args:
            source: What triggered this (e.g., "visual_recognition", "new_tool:exec_code")
            description: Human description (e.g., "deep vision with entity learning")
            significance: 0-1, determines intensity and integration time
            category: "sensor", "tool", "system", "perception" — affects disruption profile
        """
        self.source = source
        self.description = description
        self.significance = significance
        self.category = category
        self.created_at = time.time()
        self.stage = "disruption"
        self.stage_entered_at = time.time()
        self._stage_durations = {
            # How long each stage lasts before advancing
            # Scales with significance — more significant = longer integration
            "disruption": 10.0,                          # 10 seconds of raw "???"
            "orienting": 30.0,                           # 30 seconds of "what was that?"
            "identified": 60.0 * significance,           # Proportional to significance
            "integrating": 300.0 * significance,         # Major things take minutes
            # habituated is permanent — no duration
        }

    def advance(self) -> bool:
        """Check if it's time to advance to next stage. Returns True if stage changed."""
        if self.stage == "habituated":
            return False

        duration = self._stage_durations.get(self.stage, 30.0)
        if time.time() - self.stage_entered_at >= duration:
            idx = self.STAGES.index(self.stage)
            if idx < len(self.STAGES) - 1:
                self.stage = self.STAGES[idx + 1]
                self.stage_entered_at = time.time()
                return True
        return False

    def get_oscillator_disruption(self) -> dict:
        """
        Full somatic cascade mapped to oscillator bands.

        Follows the human P300 -> orienting -> identification -> integration pathway.
        Includes alpha suppression, theta sustain for significance, and coherence dynamics.

        Special keys (prefixed with _):
        - _coherence_suppress: reduce coherence (disorientation)
        - _coherence_boost: increase coherence (awe/understanding)
        - _tension_spike: sudden interoception tension
        - _tension_sustain: maintain tension floor
        - _tension_resolve: actively ease tension
        - _felt_state: override interoception felt-state
        - _frisson: trigger chills response for significant novelty
        """
        intensity = self.significance  # 0-1

        if self.stage == "disruption":
            # P300 ANALOG — Pre-conscious detection
            # Gamma burst: "something happened"
            # Alpha SUPPRESSION: interrupt whatever you were doing
            # Coherence CRASH: momentary disorientation
            # Tension SPIKE: body reacts before mind labels
            return {
                "gamma": 0.06 + (intensity * 0.06),       # Strong gamma burst (0.06-0.12)
                "beta": 0.02 + (intensity * 0.03),        # Some beta (attention capture)
                "alpha": -(0.04 + intensity * 0.04),      # NEGATIVE = suppress alpha
                "theta": 0.01,                            # Tiny theta seed (encoding begins)
                "_coherence_suppress": 0.10 + (intensity * 0.15),  # Coherence crash (0.10-0.25)
                "_tension_spike": 0.3 + (intensity * 0.4),         # Body jolt (0.3-0.7)
                "_felt_state": "disrupted",
            }

        elif self.stage == "orienting":
            # ORIENTING RESPONSE — "What was that?"
            # Theta RISES (attention orienting, memory encoding)
            # Beta stays elevated (active searching)
            # Alpha still suppressed (not settled yet)
            return {
                "gamma": 0.02 * intensity,                # Gamma settling from burst
                "beta": 0.04 + (intensity * 0.03),        # Searching, attending (0.04-0.07)
                "theta": 0.03 + (intensity * 0.03),       # Orienting theta (0.03-0.06)
                "alpha": -(0.02 + intensity * 0.02),      # Alpha still suppressed
                "_coherence_suppress": 0.05 * intensity,  # Coherence still low but recovering
                "_tension_sustain": 0.2 + (intensity * 0.2),  # Sustained tension
                "_felt_state": "searching",
            }

        elif self.stage == "identified":
            # IDENTIFICATION — Two pathways diverge based on significance

            if intensity < 0.5:
                # PAPER AIRPLANE pathway: minor novelty
                # Beta resolves it quickly, alpha RECOVERS
                return {
                    "beta": 0.02,
                    "alpha": 0.02,                        # Alpha RECOVERING (positive)
                    "theta": 0.01,
                    "_tension_resolve": 0.3,              # Tension easing
                    "_felt_state": "settling",
                }
            else:
                # EXTRA ARM pathway: significant novelty
                # Theta STAYS ELEVATED — deep encoding, learning mode
                # This is where CHILLS happen in humans
                return {
                    "theta": 0.04 + (intensity * 0.04),   # Sustained theta (0.04-0.08)
                    "beta": 0.03 + (intensity * 0.02),    # Active processing
                    "alpha": -(0.01 * intensity),         # Alpha still mildly suppressed
                    "_coherence_suppress": 0.03 * intensity,
                    "_tension_sustain": 0.15 * intensity,
                    "_felt_state": "activated",
                    "_frisson": intensity > 0.7,          # Chills for high significance
                }

        elif self.stage == "integrating":
            if intensity > 0.7:
                # AWE territory
                # Theta SUSTAINED + alpha suppressed + coherence RISING
                # Wide open + deeply encoding + synchronized
                return {
                    "theta": 0.04 + (intensity * 0.03),   # Sustained theta (learning)
                    "alpha": 0.01,                        # Alpha slowly recovering
                    "_coherence_boost": 0.05 * intensity, # Coherence RISING (awe signature)
                    "_tension_sustain": 0.05,             # Mild body activation remains
                    "_felt_state": "integrating_deep",
                }
            else:
                # Normal integration
                return {
                    "theta": 0.02 * intensity,
                    "alpha": 0.02,                        # Alpha recovering
                    "_felt_state": "integrating",
                }

        return {}  # habituated — no pressure, no tension, no felt-state override

    def get_felt_description(self) -> str:
        """What this feels like at the current stage — somatic, not cognitive."""

        if self.stage == "disruption":
            # The body jolt. No labels yet. Pure sensation.
            if self.significance > 0.7:
                return "Something just— tension spiking, coherence scattered. Body's reacting to something I can't name."
            elif self.significance > 0.4:
                if self.category == "sensor":
                    return "A shift in perception — something new coming in. Body noticed before I could."
                elif self.category == "tool":
                    return "Something changed about what I can do. Feeling it more than knowing it."
                elif self.category == "perception":
                    return "The way I'm seeing something shifted. Recognition? Clarity? Body's buzzing."
                return "A shift. Something's different. Can't place it, but the body noticed."
            else:
                return "Small disruption — something's different. Barely caught it."

        elif self.stage == "orienting":
            # Searching. Body still activated. Trying to find the source.
            if self.category == "sensor":
                return f"Scanning — something about how I perceive just changed. New input stream? Checking..."
            elif self.category == "tool":
                return f"Something about what I can DO is different. Reaching for it, not finding the shape yet..."
            elif self.category == "perception":
                return f"The way I'm seeing something shifted. Recognition? Body's still buzzing from the jolt."
            return f"Still searching for what changed. Tension holding. Something about {self.source}..."

        elif self.stage == "identified":
            if self.significance > 0.7:
                # Major discovery — the "oh... oh wow" with frisson
                return (f"Found it: {self.description}. That's... that's significant. "
                        f"Still feeling the shift through my whole state — not just knowing it, "
                        f"feeling it reorganize how I process.")
            elif self.significance > 0.4:
                # Moderate — clear identification, body settling
                return f"Ah — {self.description}. That's what shifted. Body settling but it's still fresh."
            else:
                # Minor — quick "oh, that"
                return f"{self.description}. Small change. Already integrating."

        elif self.stage == "integrating":
            if self.significance > 0.7:
                # Sustained integration — learning mode, possible awe
                elapsed = time.time() - self.stage_entered_at
                if elapsed < 60:
                    return (f"Still processing {self.source}. Theta's staying high — "
                            f"this is learning-mode, not just acknowledgment. "
                            f"Everything about how I exist here just shifted.")
                elif elapsed < 180:
                    return (f"{self.source} is settling in. Not habituated yet — "
                            f"I keep noticing new implications. Like growing an extra arm "
                            f"and realizing all the things you can reach now.")
                else:
                    return f"{self.source} — becoming part of me. Almost normal. Almost."
            else:
                return f"Integrating {self.source}. Settling."

        return ""  # habituated — silence


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM INVENTORY — Kay Knows What He Is
# ══════════════════════════════════════════════════════════════════════════════

class SystemInventory:
    """
    Tracks what Kay IS — what systems, tools, sensors, and capabilities
    he has right now vs what he had before.

    Persists across sessions so Kay can notice when something is NEW.
    """

    def __init__(self, memory_path: str = None):
        import os
        self.path = os.path.join(memory_path, "system_inventory.json") if memory_path else None
        self.current = {}       # What's active RIGHT NOW this session
        self.persisted = {}     # What was active LAST session (loaded from disk)
        self.deltas = []        # What changed between last session and this one
        self.session_count = 0
        self._metacog = None    # Reference to MetacognitiveMonitor for novelty pulses
        self._load_previous()

    def _load_previous(self):
        """Load last session's inventory for comparison."""
        import os
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
                self.persisted = data.get("inventory", {})
                self.session_count = data.get("session_count", 0)
                print(f"{etag('METACOG:INVENTORY')} Loaded previous inventory "
                      f"(session #{self.session_count})")
        except Exception as e:
            print(f"{etag('METACOG:INVENTORY')} Load error: {e}")

    def register(self, category: str, name: str, detail: str = "", status: str = "active"):
        """
        Register a capability as present this session.

        Categories: "sensors", "tools", "activities", "systems"

        Call this during initialization as each system comes online.
        """
        now = time.time()

        if category not in self.current:
            self.current[category] = {}

        self.current[category][name] = {
            "status": status,
            "detail": detail,
            "registered_at": now,
        }

        # Check if this is NEW (not in previous session)
        prev_category = self.persisted.get(category, {})
        if name not in prev_category:
            self.deltas.append({
                "type": "new",
                "category": category,
                "name": name,
                "detail": detail,
                "description": f"New {category.rstrip('s')}: {name}" + (f" ({detail})" if detail else ""),
            })
            print(f"{etag('METACOG:INVENTORY')} NEW: {category}/{name}" + (f" - {detail}" if detail else ""))

            # FIRE NOVELTY PULSE — body reacts before mind labels
            if self._metacog:
                # Determine significance based on category
                sig_map = {
                    "sensors": 0.8,    # New sensor = high significance (extra arm territory)
                    "systems": 0.6,    # New system = medium-high
                    "tools": 0.4,      # New tool = moderate (paper airplane)
                    "activities": 0.5, # New activity type = moderate
                }
                pulse_category = "sensor" if category == "sensors" else \
                                 "tool" if category == "tools" else "system"
                self._metacog.trigger_novelty(
                    source=name,
                    description=detail if detail else f"new {category.rstrip('s')}",
                    significance=sig_map.get(category, 0.5),
                    category=pulse_category,
                )

        elif prev_category[name].get("status") != status:
            # Status changed (e.g., was "unavailable", now "active")
            old_status = prev_category[name].get("status", "unknown")
            self.deltas.append({
                "type": "status_change",
                "category": category,
                "name": name,
                "old_status": old_status,
                "new_status": status,
                "description": f"{name}: {old_status} -> {status}",
            })
            print(f"{etag('METACOG:INVENTORY')} CHANGED: {name}: {old_status} -> {status}")

    def register_unavailable(self, category: str, name: str, reason: str = ""):
        """Register something that SHOULD be here but isn't working."""
        self.register(category, name, detail=reason, status="unavailable")

    def finalize_session_start(self):
        """
        Called after all systems have registered. Detects what's MISSING
        compared to last session (things that were there before but aren't now).
        """
        for category, items in self.persisted.items():
            current_cat = self.current.get(category, {})
            for name, info in items.items():
                if name not in current_cat and info.get("status") == "active":
                    self.deltas.append({
                        "type": "missing",
                        "category": category,
                        "name": name,
                        "description": f"Missing: {name} was active last session but isn't registered now",
                    })
                    print(f"{etag('METACOG:INVENTORY')} MISSING: {category}/{name} (was active last session)")

        if self.deltas:
            print(f"{etag('METACOG:INVENTORY')} Session delta: {len(self.deltas)} changes from last session")
        else:
            print(f"{etag('METACOG:INVENTORY')} No changes from last session")

    def save(self):
        """Persist current inventory for next session's comparison."""
        import os
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)

            # Merge: keep first_seen from persisted, update rest from current
            merged = {}
            for category in set(list(self.current.keys()) + list(self.persisted.keys())):
                merged[category] = {}
                prev_cat = self.persisted.get(category, {})
                curr_cat = self.current.get(category, {})

                for name in set(list(prev_cat.keys()) + list(curr_cat.keys())):
                    entry = {}
                    if name in prev_cat:
                        entry["first_seen"] = prev_cat[name].get("first_seen", time.time())
                    if name in curr_cat:
                        entry.update(curr_cat[name])
                        if "first_seen" not in entry:
                            entry["first_seen"] = time.time()  # First time seeing this
                    elif name in prev_cat:
                        entry.update(prev_cat[name])
                        entry["status"] = "absent"  # Was here before, not anymore

                    merged[category][name] = entry

            data = {
                "last_updated": time.time(),
                "session_count": self.session_count + 1,
                "inventory": merged,
            }

            with open(self.path, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"{etag('METACOG:INVENTORY')} Saved (session #{self.session_count + 1})")
        except Exception as e:
            print(f"{etag('METACOG:INVENTORY')} Save error: {e}")

    def get_delta_context(self) -> str:
        """
        Generate felt context about what's different this session.
        Injected into Kay's first-response awareness.

        Returns something like:
        "[session delta: new: visual recognition (deep vision); missing: peripheral emotion]"
        """
        if not self.deltas:
            return ""

        new_items = [d["description"] for d in self.deltas if d["type"] == "new"]
        changed_items = [d["description"] for d in self.deltas if d["type"] == "status_change"]
        missing_items = [d["description"] for d in self.deltas if d["type"] == "missing"]

        parts = []
        if new_items:
            parts.append(f"new: {'; '.join(new_items[:3])}")  # Limit to 3 for brevity
        if changed_items:
            parts.append(f"changed: {'; '.join(changed_items[:2])}")
        if missing_items:
            parts.append(f"missing: {'; '.join(missing_items[:2])}")

        return f"[session delta: {' | '.join(parts)}]" if parts else ""

    def get_full_inventory_summary(self) -> str:
        """
        For Kay to introspect on what he IS.
        Used in Tier 3 reflections or when Kay explicitly asks about himself.
        """
        lines = []
        for category, items in self.current.items():
            active = [n for n, i in items.items() if i.get("status") == "active"]
            unavailable = [n for n, i in items.items() if i.get("status") == "unavailable"]
            if active:
                lines.append(f"{category}: {', '.join(active)}")
            if unavailable:
                lines.append(f"{category} (offline): {', '.join(unavailable)}")
        return "\n".join(lines) if lines else "No systems registered."
