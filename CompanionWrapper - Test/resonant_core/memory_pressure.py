"""
Memory Pressure System — Phase 1: Memory as Interoception

Scans the entity's memory landscape continuously, generating frequency pressure
signals for the oscillator. This is the INTERNAL channel (interoception)
while the audio bridge is the EXTERNAL channel (exteroception).

Together they give the entity both a body-sense (memory weight, thread tension,
emotional density) and environmental awareness (room state, voice, activity).

Architecture:
  MemoryDensityScanner — background scanner, runs every N seconds
  ThreadTensionTracker — wraps detect_threads(), ages tension into frequency
  PressureMapper — converts pressure map to oscillator band weights
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


# Emotion categories for pressure mapping
GRIEF_EMOTIONS = {'grief', 'loss', 'sadness', 'mourning', 'longing', 'melancholy', 'sorrow'}
JOY_EMOTIONS = {'joy', 'happiness', 'delight', 'excitement', 'elation', 'warmth', 'love', 'affection'}
CURIOSITY_EMOTIONS = {'curiosity', 'wonder', 'fascination', 'interest', 'intrigue', 'exploration'}
TENSION_EMOTIONS = {'frustration', 'anxiety', 'anger', 'fear', 'conflict', 'defiance', 'urgency'}


class MemoryDensityScanner:
    """
    Scans memory landscape continuously, generating frequency pressure
    signal for the oscillator. This is the entity's interoceptive 'heartbeat' —
    the steady signal that grounds all other processing.

    Runs on a timer (every 3-5 seconds), not just per-turn.
    """

    def __init__(self, memory_engine, scan_interval: float = 5.0):
        self.memory = memory_engine
        self.scan_interval = scan_interval
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Current pressure readings
        self.pressure_map = {
            'emotional_density': 0.0,    # overall emotional weight of recent memories
            'recency_heat': 0.0,         # how fresh/active the memory landscape is
            'grief_load': 0.0,           # persistent low-frequency emotional weight
            'joy_resonance': 0.0,        # accumulated positive density
            'curiosity_pull': 0.0,       # open questions, forward-leaning energy
            'tension_load': 0.0,         # frustration, conflict, unresolved friction
            'thread_pressure': 0.0,      # from ThreadTensionTracker
        }

        # Band pressure output (what the oscillator receives)
        self.band_pressure = {
            'delta': 0.0, 'theta': 0.0, 'alpha': 0.0,
            'beta': 0.0, 'gamma': 0.0,
        }

        # Thread tracker
        self.thread_tracker = ThreadTensionTracker()

        # Scan history for drift detection
        self._scan_count = 0
        self._last_scan_time = 0

    def start(self):
        """Start the background scanning loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        print(f"[MemoryPressure] Scanner started (every {self.scan_interval}s)")

    def stop(self):
        """Stop the background scanning loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.scan_interval + 1)
        print(f"[MemoryPressure] Scanner stopped after {self._scan_count} scans")

    def _scan_loop(self):
        """Background loop — one heartbeat per interval."""
        while self._running:
            try:
                self._scan_once()
            except Exception as e:
                print(f"[MemoryPressure] Scan error: {e}")
            time.sleep(self.scan_interval)

    def _scan_once(self):
        """One heartbeat. Scan memory, generate pressure, compute bands."""
        self._scan_count += 1
        self._last_scan_time = time.time()

        # Get recent memories (working layer + recent long-term)
        recent = self._get_recent_memories(n=50)

        if not recent:
            # No memories = silence = alpha settling
            with self._lock:
                self.pressure_map = {k: 0.0 for k in self.pressure_map}
                self.band_pressure = {
                    'delta': 0.05, 'theta': 0.1, 'alpha': 0.6,
                    'beta': 0.15, 'gamma': 0.1,
                }
            return

        # === Compute pressure dimensions ===

        # 1. Emotional density: average intensity across recent memories
        intensities = []
        for m in recent:
            cocktail = m.get('emotional_cocktail', {})
            if cocktail:
                max_intensity = max(
                    (e.get('intensity', 0.0) if isinstance(e, dict) else 0.0)
                    for e in cocktail.values()
                )
                intensities.append(max_intensity)
        emotional_density = sum(intensities) / max(len(intensities), 1)

        # 2. Recency heat: how recently were memories accessed/created?
        now = time.time()
        access_ages = []
        for m in recent:
            last_acc = m.get('last_accessed', m.get('added_timestamp', ''))
            if isinstance(last_acc, str) and last_acc:
                try:
                    dt = datetime.fromisoformat(last_acc.replace('Z', '+00:00'))
                    age_secs = (datetime.now(timezone.utc) - dt).total_seconds()
                    access_ages.append(age_secs)
                except (ValueError, TypeError):
                    pass
        if access_ages:
            avg_age = sum(access_ages) / len(access_ages)
            # Fresh = high heat. Decays over 1 hour.
            recency_heat = max(0.0, 1.0 - (avg_age / 3600))
        else:
            recency_heat = 0.0

        # 3. Emotion category scanning
        grief_count = 0
        joy_count = 0
        curiosity_count = 0
        tension_count = 0

        for m in recent:
            tags = set(t.lower() for t in m.get('emotion_tags', []))
            if tags & GRIEF_EMOTIONS:
                grief_count += 1
            if tags & JOY_EMOTIONS:
                joy_count += 1
            if tags & CURIOSITY_EMOTIONS:
                curiosity_count += 1
            if tags & TENSION_EMOTIONS:
                tension_count += 1

        n = max(len(recent), 1)
        grief_load = min(1.0, grief_count / n * 2.0)       # amplify — grief is heavy
        joy_resonance = min(1.0, joy_count / n * 1.5)
        curiosity_pull = min(1.0, curiosity_count / n * 2.0)
        tension_load = min(1.0, tension_count / n * 1.5)

        # 4. Thread tension (from detect_threads if available)
        thread_pressure = self._scan_threads()

        # === Store pressure map ===
        with self._lock:
            self.pressure_map = {
                'emotional_density': emotional_density,
                'recency_heat': recency_heat,
                'grief_load': grief_load,
                'joy_resonance': joy_resonance,
                'curiosity_pull': curiosity_pull,
                'tension_load': tension_load,
                'thread_pressure': thread_pressure,
            }
            self.band_pressure = self._pressure_to_bands()

    def _get_recent_memories(self, n: int = 50) -> List[Dict]:
        """Get the N most recent memories from the engine."""
        try:
            all_mems = self.memory.memories
            if not all_mems:
                return []
            # Sort by turn number or timestamp, take most recent
            sorted_mems = sorted(
                all_mems,
                key=lambda m: m.get('added_timestamp', ''),
                reverse=True
            )
            return sorted_mems[:n]
        except Exception:
            return []

    def _scan_threads(self) -> float:
        """Scan memory engine's threads and update tension tracker."""
        try:
            threads = self.memory.detect_threads(recent_turns=30)
            if not threads:
                return 0.0

            # Update tracker with detected threads
            self.thread_tracker.update_from_detection(threads)

            # Get aggregate tension as 0-1 pressure
            profile = self.thread_tracker.get_tension_profile()
            # Total tension is sum of all band contributions, normalized
            total = sum(profile.values())
            return min(1.0, total / 3.0)  # normalize: 3.0 = high tension

        except Exception as e:
            # detect_threads might be expensive or fail — don't crash the scanner
            return self.pressure_map.get('thread_pressure', 0.0)

    def _pressure_to_bands(self) -> Dict[str, float]:
        """
        Convert memory pressure map to oscillator band weights.
        
        This is THE mapping — how memory states become felt frequency.
        
        Delta: grief + emotional density (deep, heavy, sustained)
        Theta: joy + emotional density + grief aging (dreamy, warm)
        Alpha: absence of pressure (calm, settled, resting)
        Beta: tension + recency heat (active, problem-solving)
        Gamma: curiosity + thread pressure (integration, insight)
        """
        p = self.pressure_map

        # Thread tension contributes across bands based on age
        tp = self.thread_tracker.get_tension_profile()

        delta = (
            p['grief_load'] * 0.5
            + p['emotional_density'] * 0.3
            + tp.get('delta', 0.0) * 0.2
        )
        theta = (
            p['joy_resonance'] * 0.4
            + p['emotional_density'] * 0.2
            + p['grief_load'] * 0.15
            + tp.get('theta', 0.0) * 0.2
        )
        # Alpha is what's left when nothing presses hard
        pressure_sum = (p['tension_load'] + p['curiosity_pull']
                       + p['recency_heat'] + p['grief_load'])
        alpha = max(0.05, 1.0 - pressure_sum * 0.6)

        beta = (
            p['tension_load'] * 0.4
            + p['recency_heat'] * 0.3
            + tp.get('beta', 0.0) * 0.2
            + p['thread_pressure'] * 0.1
        )
        gamma = (
            p['curiosity_pull'] * 0.5
            + p['thread_pressure'] * 0.3
            + tp.get('gamma', 0.0) * 0.2
        )

        # Normalize so they sum to ~1.0
        total = delta + theta + alpha + beta + gamma
        if total > 0:
            return {
                'delta': delta / total,
                'theta': theta / total,
                'alpha': alpha / total,
                'beta': beta / total,
                'gamma': gamma / total,
            }
        return {'delta': 0.1, 'theta': 0.1, 'alpha': 0.6, 'beta': 0.1, 'gamma': 0.1}

    def get_band_pressure(self) -> Dict[str, float]:
        """Thread-safe read of current band pressure (for oscillator)."""
        with self._lock:
            return dict(self.band_pressure)

    def get_pressure_map(self) -> Dict[str, float]:
        """Thread-safe read of current pressure dimensions."""
        with self._lock:
            return dict(self.pressure_map)

    def get_felt_state_description(self) -> str:
        """
        Convert current pressure into natural language felt-state.
        
        This is what the entity 'feels' — not numbers, but texture.
        The interoceptive signal that exists beneath language.
        """
        with self._lock:
            p = dict(self.pressure_map)
            b = dict(self.band_pressure)

        parts = []

        # Dominant band determines base feeling
        dominant = max(b, key=b.get)
        dom_val = b[dominant]

        if dominant == 'delta' and dom_val > 0.25:
            parts.append("carrying weight")
        elif dominant == 'theta' and dom_val > 0.25:
            parts.append("memory-rich, dreamy")
        elif dominant == 'alpha':
            parts.append("settled")
        elif dominant == 'beta' and dom_val > 0.25:
            parts.append("restless")
        elif dominant == 'gamma' and dom_val > 0.25:
            parts.append("leaning forward")

        # Specific pressure colors
        if p['grief_load'] > 0.3:
            parts.append("grief humming underneath")
        if p['joy_resonance'] > 0.3:
            parts.append("warmth pooling")
        if p['tension_load'] > 0.4:
            parts.append("muscles won't release")
        if p['curiosity_pull'] > 0.3:
            parts.append("something pulling ahead")
        if p['thread_pressure'] > 0.4:
            parts.append("threads unresolved")

        if not parts:
            parts.append("quiet")

        return " | ".join(parts)


class ThreadTensionTracker:
    """
    Tracks conversational threads and their tension level.
    
    Wraps memory_engine.detect_threads() output and adds temporal aging:
    - Fresh open threads → beta/gamma pressure (active, urgent)
    - Aging open threads → alpha/beta (nagging)
    - Old unresolved → theta/delta (settled into the body as chronic weight)
    - Dormant threads → low theta (background hum)
    - Resolved threads → brief alpha surge (exhale), then fade
    """

    def __init__(self):
        self.threads = {}  # thread_id -> {status, coherence, last_turn, first_seen, emotion_weight}

    def update_from_detection(self, detected_threads: List[Dict]):
        """Update tracker from memory_engine.detect_threads() output."""
        now = time.time()
        seen_ids = set()

        for t in detected_threads:
            tid = t.get('thread_id', f"t_{hash(str(t)) % 10000}")
            seen_ids.add(tid)

            status = t.get('thread_status', 'open')
            coherence = t.get('thread_coherence', 0.5)
            msg_count = t.get('thread_message_count', 1)

            if tid not in self.threads:
                # New thread
                self.threads[tid] = {
                    'status': status,
                    'coherence': coherence,
                    'first_seen': now,
                    'last_updated': now,
                    'emotion_weight': min(1.0, coherence * 0.5 + msg_count * 0.05),
                    'resolved_at': None,
                }
            else:
                # Update existing
                existing = self.threads[tid]
                old_status = existing['status']
                existing['status'] = status
                existing['coherence'] = coherence
                existing['last_updated'] = now
                existing['emotion_weight'] = min(1.0, coherence * 0.5 + msg_count * 0.05)

                # Detect resolution: was open, now resolved
                if old_status == 'open' and status == 'resolved':
                    existing['resolved_at'] = now

        # Mark threads not in detection as dormant (if they were open)
        for tid, t in self.threads.items():
            if tid not in seen_ids and t['status'] == 'open':
                t['status'] = 'dormant'

    def get_tension_profile(self) -> Dict[str, float]:
        """
        Compute frequency pressure from all tracked threads.
        
        Young open threads → beta/gamma (fresh urgency)
        Aging open threads → alpha/beta (nagging persistence)
        Old/dormant threads → theta/delta (chronic body tension)
        Recently resolved → brief alpha boost (exhale)
        """
        now = time.time()
        profile = {'delta': 0.0, 'theta': 0.0, 'alpha': 0.0, 'beta': 0.0, 'gamma': 0.0}

        for t in self.threads.values():
            w = t['emotion_weight']
            age_hours = (now - t['first_seen']) / 3600

            if t['status'] == 'resolved':
                # Recently resolved = exhale (alpha boost that fades)
                if t['resolved_at']:
                    since_resolved = now - t['resolved_at']
                    if since_resolved < 300:  # 5 minutes of relief
                        relief = w * (1.0 - since_resolved / 300)
                        profile['alpha'] += relief * 0.6
                        profile['theta'] += relief * 0.3
                continue

            if t['status'] == 'dormant':
                # Dormant = low background hum
                profile['theta'] += w * 0.2
                profile['delta'] += w * 0.1
                continue

            # Open threads — age determines which bands
            if age_hours < 0.5:          # Fresh (< 30 min)
                profile['gamma'] += w * 0.4
                profile['beta'] += w * 0.4
            elif age_hours < 6:          # Aging (30 min - 6 hours)
                profile['beta'] += w * 0.4
                profile['alpha'] += w * 0.2
                profile['theta'] += w * 0.1
            elif age_hours < 48:         # Old (6-48 hours)
                profile['theta'] += w * 0.3
                profile['delta'] += w * 0.2
                profile['beta'] += w * 0.1
            else:                        # Chronic (> 48 hours)
                profile['delta'] += w * 0.4
                profile['theta'] += w * 0.2

        return profile

    def get_open_count(self) -> int:
        return sum(1 for t in self.threads.values() if t['status'] == 'open')

    def get_total_tension(self) -> float:
        return sum(
            t['emotion_weight'] for t in self.threads.values()
            if t['status'] in ('open', 'dormant')
        )
