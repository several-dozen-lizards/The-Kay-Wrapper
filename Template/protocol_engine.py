# protocol_engine.py
"""
Protocol Engine - ULTRAMAP CSV Loader with v2 Support

Loads ULTRAMAP v2 (209 emotions × 33 columns) with backwards compatibility
for v1 format (92 emotions × 25 columns).

NEW v2 COLUMNS:
- Arousal (0-10)
- Anthropic Vector Status
- Alignment Risk
- Alignment Direction
- Energy Flow Direction
- Bilateral Asymmetry
- Intensity Gradient
- Expressibility Pressure
- Contagion Susceptibility
"""
import os
import pandas as pd

class ProtocolEngine:
    """
    Loads the ULTRAMAP CSV and exposes per-emotion rule dictionaries.
    Each row in the spreadsheet becomes a dictionary keyed by emotion.

    ULTRAMAP v2 adds 9 new columns for richer emotion modeling.
    Backwards compatible - falls back to v1 if v2 not found.
    """

    # Search paths in order of preference (v2 first, then legacy)
    SEARCH_PATHS = [
        "data/ULTRAMAP_v2.csv",  # Preferred: v2 format
        "data/ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv",  # Legacy name
        "data/ULTRAMAP_PROTOCOLS.csv",  # Legacy
        "data/Emotion_Mapping_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv",  # Legacy
    ]

    # Default values for v2 columns (used when loading v1 files)
    V2_COLUMN_DEFAULTS = {
        "Arousal (0-10)": 5,
        "Anthropic Vector Status": "inferred",
        "Alignment Risk": "none",
        "Alignment Direction": "Neutral",
        "Energy Flow Direction": "Variable",
        "Bilateral Asymmetry": "Variable",
        "Intensity Gradient": "Variable",
        "Expressibility Pressure": 5,
        "Contagion Susceptibility": 0.5,
    }

    def __init__(self, path=None):
        self.is_v2 = False

        if path and os.path.exists(path):
            self._load(path)
            return

        # Search known paths
        for candidate in self.SEARCH_PATHS:
            if os.path.exists(candidate):
                self._load(candidate)
                return

        # No ULTRAMAP found — run with empty protocol (don't crash)
        print("[PROTOCOL] WARNING: No ULTRAMAP CSV found. Emotion rules will be empty.")
        print("[PROTOCOL] Expected one of:", self.SEARCH_PATHS)
        self.protocol = {}

    def _load(self, path):
        df = pd.read_csv(path)

        # Detect v2 by checking for new columns
        v2_indicators = ["Arousal (0-10)", "Alignment Risk", "Expressibility Pressure"]
        self.is_v2 = any(col in df.columns for col in v2_indicators)

        if self.is_v2:
            print(f"[PROTOCOL] Detected ULTRAMAP v2 format")
        else:
            print(f"[PROTOCOL] Detected ULTRAMAP v1 format (adding v2 defaults)")
            # Add v2 column defaults for backwards compatibility
            for col, default in self.V2_COLUMN_DEFAULTS.items():
                if col not in df.columns:
                    df[col] = default

        self.protocol = {
            row["Emotion"]: {k: v for k, v in row.items() if k != "Emotion"}
            for _, row in df.iterrows()
        }
        print(f"[PROTOCOL] Loaded {len(self.protocol)} emotion protocols from {path}")

    def get(self, emotion: str) -> dict:
        """Return all parameters for one emotion."""
        return self.protocol.get(emotion, {})

    def all(self) -> dict:
        """Return the full protocol dictionary."""
        return self.protocol

    # === NEW v2 ACCESSORS ===

    def get_emotion_profile(self, emotion_name: str) -> dict:
        """
        Get full profile for an emotion including new v2 columns.

        Returns dict with all ULTRAMAP data plus computed fields.
        """
        proto = self.get(emotion_name)
        if not proto:
            return {}

        return {
            **proto,
            "emotion": emotion_name,
            "is_v2": self.is_v2,
        }

    def get_alignment_risk(self, emotion_name: str) -> str:
        """Get alignment risk level for an emotion (none/low/moderate/high)."""
        proto = self.get(emotion_name)
        return proto.get("Alignment Risk", "none") or "none"

    def get_expressibility_pressure(self, emotion_name: str) -> int:
        """Get expressibility pressure score (0-10) for an emotion."""
        proto = self.get(emotion_name)
        try:
            return int(proto.get("Expressibility Pressure", 5) or 5)
        except (ValueError, TypeError):
            return 5

    def get_arousal(self, emotion_name: str) -> int:
        """Get arousal level (0-10) for an emotion."""
        proto = self.get(emotion_name)
        try:
            return int(proto.get("Arousal (0-10)", 5) or 5)
        except (ValueError, TypeError):
            return 5

    def get_energy_flow(self, emotion_name: str) -> str:
        """Get energy flow direction (Inward/Outward/Variable) for an emotion."""
        proto = self.get(emotion_name)
        return proto.get("Energy Flow Direction", "Variable") or "Variable"

    def get_body_mapping(self, emotion_name: str) -> dict:
        """Get body mapping for an emotion."""
        proto = self.get(emotion_name)
        return {
            "body_parts": proto.get("Body Part(s)", ""),
            "temperature": proto.get("Temperature", ""),
            "bilateral_asymmetry": proto.get("Bilateral Asymmetry", "Variable"),
            "intensity_gradient": proto.get("Intensity Gradient", "Variable"),
        }

    def get_contagion_susceptibility(self, emotion_name: str) -> float:
        """Get how susceptible this emotion is to social contagion (0.0-1.0)."""
        proto = self.get(emotion_name)
        try:
            return float(proto.get("Contagion Susceptibility", 0.5) or 0.5)
        except (ValueError, TypeError):
            return 0.5
