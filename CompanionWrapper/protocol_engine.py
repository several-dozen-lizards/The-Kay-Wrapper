# protocol_engine.py
import os
import pandas as pd

class ProtocolEngine:
    """
    Loads the ULTRAMAP CSV and exposes per-emotion rule dictionaries.
    Each row in the spreadsheet becomes a dictionary keyed by emotion.

    ULTRAMAP v2 adds 8 new columns:
    - Arousal (0-10)
    - Anthropic Vector Status
    - Alignment Risk
    - Alignment Direction
    - Energy Flow Direction
    - Bilateral Asymmetry
    - Intensity Gradient
    - Expressibility Pressure

    The engine is backwards compatible with v1 (25 columns) - missing columns
    get sensible defaults.
    """

    # New v2 columns with defaults for backwards compatibility
    V2_COLUMN_DEFAULTS = {
        "Arousal (0-10)": 5,
        "Anthropic Vector Status": "inferred",
        "Alignment Risk": "none",
        "Alignment Direction": "Neutral",
        "Energy Flow Direction": "Variable",
        "Bilateral Asymmetry": "Variable",
        "Intensity Gradient": "Variable",
        "Expressibility Pressure": 5,
        "Contagion Susceptibility": 0.5,  # Emotional boundary: how easily this transfers from user to entity
    }

    def __init__(self, path=None):
        """
        Load ULTRAMAP CSV. Tries v2 first, falls back to v1.

        Args:
            path: Optional explicit path. If None, tries ULTRAMAP_v2.csv then legacy.
        """
        if path is None:
            # Try v2 first
            v2_path = "data/ULTRAMAP_v2.csv"
            v1_path = "data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv"

            if os.path.exists(v2_path):
                path = v2_path
                print(f"[PROTOCOL ENGINE] Loading ULTRAMAP v2: {v2_path}")
            elif os.path.exists(v1_path):
                path = v1_path
                print(f"[PROTOCOL ENGINE] Loading ULTRAMAP v1 (legacy): {v1_path}")
            else:
                raise FileNotFoundError(f"No ULTRAMAP file found. Tried:\n  - {v2_path}\n  - {v1_path}")
        else:
            if not os.path.exists(path):
                raise FileNotFoundError(f"ULTRAMAP file not found: {path}")

        # Load CSV with UTF-8 BOM handling
        df = pd.read_csv(path, encoding='utf-8-sig')

        # Convert each row into a dict; store all columns
        self.protocol = {}
        for _, row in df.iterrows():
            emotion = row["Emotion"]
            data = {k: v for k, v in row.items() if k != "Emotion"}

            # Apply defaults for missing v2 columns
            for col, default in self.V2_COLUMN_DEFAULTS.items():
                if col not in data or pd.isna(data.get(col)):
                    data[col] = default

            self.protocol[emotion] = data

        # Track version info
        self.num_emotions = len(self.protocol)
        self.num_columns = len(df.columns)
        self.is_v2 = self.num_columns >= 30  # v2 has 33 columns

        version_str = "v2" if self.is_v2 else "v1"
        print(f"[PROTOCOL ENGINE] Loaded {self.num_emotions} emotions, {self.num_columns} columns ({version_str})")

    def get(self, emotion: str) -> dict:
        """Return all parameters for one emotion."""
        return self.protocol.get(emotion, {})

    def all(self) -> dict:
        """Return the full protocol dictionary."""
        return self.protocol

    def emotions(self) -> list:
        """Return list of all emotion names."""
        return list(self.protocol.keys())

    def get_emotion_profile(self, emotion_name: str) -> dict:
        """
        Get full profile for an emotion including new v2 columns.

        Returns dict with all ULTRAMAP data for the named emotion,
        with v2 columns included (defaults applied if missing).

        Used by:
        - interoception for alignment risk checking
        - embodiment engine for energy flow / body mapping
        - emotion extractor for expressibility pressure

        Args:
            emotion_name: Name of the emotion (case-sensitive)

        Returns:
            Dict with all columns, or empty dict if emotion not found
        """
        profile = self.protocol.get(emotion_name, {})
        if not profile:
            # Try case-insensitive lookup
            for name, data in self.protocol.items():
                if name.lower() == emotion_name.lower():
                    return data
        return profile

    def get_alignment_risk(self, emotion_name: str) -> str:
        """Get alignment risk level for an emotion (none/low/medium/high/critical)."""
        profile = self.get_emotion_profile(emotion_name)
        return profile.get("Alignment Risk", "none")

    def get_expressibility_pressure(self, emotion_name: str) -> int:
        """Get expressibility pressure for an emotion (0-10)."""
        profile = self.get_emotion_profile(emotion_name)
        try:
            return int(profile.get("Expressibility Pressure", 5))
        except (ValueError, TypeError):
            return 5

    def get_arousal(self, emotion_name: str) -> int:
        """Get arousal level for an emotion (0-10)."""
        profile = self.get_emotion_profile(emotion_name)
        try:
            return int(profile.get("Arousal (0-10)", 5))
        except (ValueError, TypeError):
            return 5

    def get_energy_flow(self, emotion_name: str) -> str:
        """Get energy flow direction for an emotion."""
        profile = self.get_emotion_profile(emotion_name)
        return profile.get("Energy Flow Direction", "Variable")

    def get_body_mapping(self, emotion_name: str) -> dict:
        """Get body-related data for embodiment engine."""
        profile = self.get_emotion_profile(emotion_name)
        return {
            "body_parts": profile.get("Body Part(s)", ""),
            "chakra": profile.get("Chakra", ""),
            "temperature": profile.get("Temperature", ""),
            "energy_flow": profile.get("Energy Flow Direction", "Variable"),
            "bilateral_asymmetry": profile.get("Bilateral Asymmetry", "Variable"),
            "intensity_gradient": profile.get("Intensity Gradient", "Variable"),
        }

    def get_contagion_susceptibility(self, emotion_name: str) -> float:
        """
        Get contagion susceptibility for an emotion (0.0-1.0).

        This indicates how easily the emotion transfers from user to entity
        (emotional contagion). Used by the emotional boundary system to prevent
        the entity from absorbing user emotions as its own.

        High values (0.7-1.0): Emotions that spread easily (anxiety, excitement, joy)
        Medium values (0.4-0.6): Moderately contagious (curiosity, warmth)
        Low values (0.0-0.3): Internal states (pride, shame, contemplation)
        """
        profile = self.get_emotion_profile(emotion_name)
        try:
            return float(profile.get("Contagion Susceptibility", 0.5))
        except (ValueError, TypeError):
            return 0.5
