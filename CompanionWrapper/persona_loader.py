"""
Persona Loader — The identity layer.

Reads persona_config.json and system_prompt.md from the persona/ directory,
provides a single interface for the entire wrapper to access entity identity.

REPLACES:
  - kay_prompts.py / reed_prompts.py (hardcoded system prompts)
  - Hardcoded entity names in main.py, nexus_entity.py, config.json
  - Hardcoded pacing configs in conversation_pacer.py

USAGE:
  from persona_loader import persona

  persona.name          # "Companion"
  persona.entity_id     # "companion"
  persona.system_prompt  # Full system prompt with variables resolved
  persona.pronouns      # {"subject": "they", ...}
  persona.voice_config  # {"engine": "edge-tts", ...}
  persona.pacing_config # PacingConfig instance
  persona.room_config   # {"starting_position": {...}, "color": "#..."}
  persona.oscillator_config  # {"starting_profile": "neutral", ...}
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Pronouns:
    subject: str = "they"
    object: str = "them"
    possessive: str = "their"
    reflexive: str = "themselves"


class Persona:
    """
    Central identity provider for the wrapper.
    
    Loads persona configuration from persona/ directory and resolves
    all template variables. Every module that needs to know WHO this
    entity is should import from here instead of hardcoding.
    """

    def __init__(self, persona_dir: str = None):
        if persona_dir is None:
            # Priority 1: COMPANION_DIR (full companion isolation mode)
            companion_dir = os.environ.get("COMPANION_DIR")
            if companion_dir:
                persona_dir = os.path.join(companion_dir, "who_i_am")
            else:
                # Priority 2: PERSONA_CONFIG_DIR (legacy multi-persona mode)
                persona_dir = os.environ.get("PERSONA_CONFIG_DIR")

            if not persona_dir:
                # Priority 3: Default ./persona relative to this file
                persona_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "persona"
                )
        self.persona_dir = persona_dir
        self._config = {}
        self._system_prompt_raw = ""
        self._load()

    def _load(self):
        """Load persona config and system prompt from disk."""
        # Check for persona.json (companion format) first, then persona_config.json (legacy)
        config_path = os.path.join(self.persona_dir, "persona.json")
        if not os.path.exists(config_path):
            config_path = os.path.join(self.persona_dir, "persona_config.json")

        # Also check for personality.md (companion format) vs system_prompt.md (legacy)
        prompt_path = os.path.join(self.persona_dir, "personality.md")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(self.persona_dir, "system_prompt.md")

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Persona config not found at {config_path}. "
                f"Run setup_wizard.py to create one, or copy from Template/persona/."
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self._system_prompt_raw = f.read()
        else:
            self._system_prompt_raw = f"You are {self.name}."

    def reload(self):
        """Hot-reload persona config (for live editing)."""
        self._load()

    # --- Identity ---

    @property
    def name(self) -> str:
        return self._config.get("entity", {}).get("name", "Companion")

    @property
    def display_name(self) -> str:
        return self._config.get("entity", {}).get("display_name", self.name)

    @property
    def entity_id(self) -> str:
        return self._config.get("entity", {}).get("entity_id", self.name.lower())

    @property
    def pronouns(self) -> Pronouns:
        p = self._config.get("entity", {}).get("pronouns", {})
        return Pronouns(
            subject=p.get("subject", "they"),
            object=p.get("object", "them"),
            possessive=p.get("possessive", "their"),
            reflexive=p.get("reflexive", "themselves"),
        )

    @property
    def user_name(self) -> str:
        return self._config.get("relationship", {}).get("user_name", "User")

    @property
    def user_preferred_name(self) -> str:
        return self._config.get("relationship", {}).get("user_preferred_name", "")

    # --- System Prompt ---

    @property
    def system_prompt(self) -> str:
        """System prompt with all template variables resolved."""
        p = self.pronouns
        return self._system_prompt_raw.replace(
            "{ENTITY_NAME}", self.name
        ).replace(
            "{USER_NAME}", self.user_name
        ).replace(
            "{PRONOUNS_SUBJECT}", p.subject
        ).replace(
            "{PRONOUNS_OBJECT}", p.object
        ).replace(
            "{PRONOUNS_POSSESSIVE}", p.possessive
        ).replace(
            "{PRONOUNS_REFLEXIVE}", p.reflexive
        )

    # --- Subsystem Configs ---

    @property
    def voice_config(self) -> Dict[str, Any]:
        return self._config.get("voice", {
            "engine": "edge-tts",
            "voice_id": "en-US-JennyNeural",
            "speed": 1.0, "pitch": 0, "volume": 1.0, "enabled": True
        })

    @property
    def theme_config(self) -> Dict[str, Any]:
        return self._config.get("theme", {
            "name": "Default", "font_size": 13, "font_family": "Courier"
        })

    @property
    def oscillator_config(self) -> Dict[str, Any]:
        return self._config.get("oscillator", {
            "starting_profile": "neutral",
            "audio_responsiveness": 0.3,
            "interoception_interval": 4.0
        })

    @property
    def room_config(self) -> Dict[str, Any]:
        return self._config.get("room", {
            "starting_position": {"distance": 100, "angle_deg": 90},
            "color": "#4A90D9"
        })

    @property
    def pacing_config(self) -> Dict[str, Any]:
        """Raw pacing dict. Convert to PacingConfig in conversation_pacer."""
        return self._config.get("pacing", {
            "max_sentences_default": 3,
            "thinking_delay_min": 1.5,
            "thinking_delay_max": 4.0
        })

    @property
    def visual_sensor_config(self) -> Dict[str, Any]:
        return self._config.get("visual_sensor", {"enabled": False})

    @property
    def spiral_detection_config(self) -> Dict[str, Any]:
        return self._config.get("spiral_detection", {
            "enabled_for_llm_conversations": True,
            "enabled_for_primary_user": False
        })

    # --- Resonance Profile ---

    @property
    def resonance_profile(self) -> Dict[str, Any]:
        """Load the entity's resonance profile (oscillator starting state)."""
        profile_path = os.path.join(self.persona_dir, "resonance_profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "entity": self.entity_id,
            "dominant_band": "alpha",
            "coherence": 0.3,
            "band_power": {"delta": 0.10, "theta": 0.15, "alpha": 0.35, "beta": 0.25, "gamma": 0.15}
        }

    # --- Config Generation ---

    def generate_config_json(self) -> Dict[str, Any]:
        """Generate the wrapper's config.json from persona settings.
        
        This replaces the old manually-edited config.json with one 
        derived from persona_config.json. Called by setup_wizard or at startup.
        """
        return {
            "theme": self.theme_config.get("name", "Default"),
            "font_size": self.theme_config.get("font_size", 13),
            "font_family": self.theme_config.get("font_family", "Courier"),
            "voice": self.voice_config,
            "spiral_detection": self.spiral_detection_config,
            "visual_sensor": self.visual_sensor_config,
        }

    def write_config_json(self, output_dir: str = None):
        """Write generated config.json to the wrapper root."""
        if output_dir is None:
            output_dir = os.path.dirname(self.persona_dir)
        config = self.generate_config_json()
        path = os.path.join(output_dir, "config.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"[PERSONA] Wrote config.json to {path}")

    def write_resonance_shared(self, shared_dir: str):
        """Write resonance profile to shared/ for oscillator startup."""
        profile = self.resonance_profile
        path = os.path.join(shared_dir, f"resonance_{self.entity_id}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(profile, f)
        print(f"[PERSONA] Wrote resonance profile to {path}")

    # --- String Representation ---

    def __repr__(self):
        return f"Persona(name={self.name!r}, id={self.entity_id!r})"


# =====================================================================
# Module-level singleton
# =====================================================================
# Import this in any module that needs persona info:
#   from persona_loader import persona
#
# The persona is loaded once at import time. Call persona.reload() to
# pick up changes without restarting.

# Check COMPANION_DIR first, then fall back to ./persona
_companion_dir = os.environ.get("COMPANION_DIR")
if _companion_dir:
    _persona_dir = os.path.join(_companion_dir, "who_i_am")
else:
    _persona_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona")

try:
    persona = Persona(_persona_dir)
    if _companion_dir:
        print(f"[PERSONA] Loaded from companion: {persona.name} ({persona.entity_id})")
    else:
        print(f"[PERSONA] Loaded: {persona.name} ({persona.entity_id})")
except FileNotFoundError:
    persona = None
    print("[PERSONA] No persona config found. Run setup_wizard.py to create one.")
