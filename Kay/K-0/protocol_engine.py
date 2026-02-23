# protocol_engine.py
import os
import pandas as pd

class ProtocolEngine:
    """
    Loads the ULTRAMAP CSV and exposes per-emotion rule dictionaries.
    Each row in the spreadsheet becomes a dictionary keyed by emotion.
    """
    def __init__(self, path="data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv"):
        if not os.path.exists(path):
            raise FileNotFoundError(f"ULTRAMAP file not found: {path}")
        df = pd.read_csv(path)
        # Convert each row into a dict; store all columns
        self.protocol = {
            row["Emotion"]: {k: v for k, v in row.items() if k != "Emotion"}
            for _, row in df.iterrows()
        }

    def get(self, emotion: str) -> dict:
        """Return all parameters for one emotion."""
        return self.protocol.get(emotion, {})

    def all(self) -> dict:
        """Return the full protocol dictionary."""
        return self.protocol
