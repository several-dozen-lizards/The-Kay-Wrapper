# engines/reflection_engine.py
import random
import time
from typing import Optional

class ReflectionEngine:
    def __init__(self, dreaming_enabled=True):
        self.dreaming_enabled = dreaming_enabled

    def reflect(self, agent_state, user_input: str, response: str):
        """
        Perform post-turn self-reflection, consolidation, and optional 'dreaming'.
        Can update agent_state.meta, drift, motifs, etc.
        """
        emotion_snapshot = agent_state.emotional_cocktail.copy()
        social_snapshot = agent_state.social['needs'].copy()
        motifs = agent_state.meta.get('motifs', [])
        note = {
            "emotion": emotion_snapshot,
            "social": social_snapshot,
            "motifs": motifs,
            "input": user_input,
            "output": response,
        }
        agent_state.meta.setdefault('reflection_log', []).append(note)

        if random.random() < 0.1:
            drift = agent_state.meta.get('identity_drift', 0.0)
            drift += random.uniform(-0.01, 0.02)
            agent_state.meta['identity_drift'] = max(0.0, min(1.0, drift))

        if self.dreaming_enabled and random.random() < 0.05:
            self._dream(agent_state)

    def _dream(self, agent_state):
        print("[Dreaming] Night phase: consolidating memories, motifs, and emotional states.")
        agent_state.meta.setdefault('dream_log', []).append({
            "t": time.time(),
            "event": "dreamed/consolidated"
        })
