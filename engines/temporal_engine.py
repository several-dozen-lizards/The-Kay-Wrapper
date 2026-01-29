# temporal_engine.py

import time

class TemporalEngine:
    def __init__(self):
        self.last_tick = time.time()

    def update(self, agent_state):
        """
        Advances aging for emotions/memory, and updates temporal state.
        """
        now = time.time()
        elapsed = now - (agent_state.temporal.get('last_seen') or now)
        agent_state.temporal['last_seen'] = now
        agent_state.temporal['time_in_state'] += elapsed

        # Age emotions
        for emo, state in agent_state.emotional_cocktail.items():
            state['age'] = state.get('age', 0) + 1  # Or base on elapsed

        # Optionally decay or shift other temporal properties
        # e.g. phase change, circadian rhythm, etc.

        # If you have time-based phase changes:
        # if agent_state.temporal['time_in_state'] > THRESHOLD:
        #     agent_state.temporal['phase'] += 1
