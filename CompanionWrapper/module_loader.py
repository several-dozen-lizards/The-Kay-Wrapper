"""
Module Loader — Feature flag system for wrapper subsystems.

Reads modules.json to determine which subsystems are enabled.
Every subsystem in main.py should check here before initializing.

USAGE:
  from module_loader import modules

  if modules.enabled("oscillator"):
      from resonant_core.resonant_integration import ResonantIntegration
      resonance = ResonantIntegration(...)

  if modules.enabled("visual_sensor"):
      from engines.visual_sensor import VisualSensor
      sensor = VisualSensor(...)
"""

import os
import json
from typing import Dict, Set


class ModuleLoader:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "modules.json"
            )
        self._config_path = config_path
        self._modules: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._config_path):
            with open(self._config_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            # Filter out _comment keys
            self._modules = {
                k: v for k, v in raw.items()
                if isinstance(v, dict) and "enabled" in v
            }
        else:
            print("[MODULES] No modules.json found — all modules enabled by default")
            self._modules = {}

    def enabled(self, module_name: str) -> bool:
        """Check if a module is enabled. Unknown modules default to True."""
        if module_name not in self._modules:
            return True  # Fail open — unknown modules are enabled
        return self._modules[module_name].get("enabled", True)

    def disabled(self, module_name: str) -> bool:
        return not self.enabled(module_name)

    def enable(self, module_name: str):
        """Enable a module and save."""
        if module_name in self._modules:
            self._modules[module_name]["enabled"] = True
            self._save()

    def disable(self, module_name: str):
        """Disable a module and save."""
        if module_name in self._modules:
            self._modules[module_name]["enabled"] = False
            self._save()

    def _save(self):
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump({"_comment": "Module toggles. Set false to disable any subsystem."} | self._modules, f, indent=2)

    def list_enabled(self) -> Set[str]:
        return {k for k, v in self._modules.items() if v.get("enabled", True)}

    def list_disabled(self) -> Set[str]:
        return {k for k, v in self._modules.items() if not v.get("enabled", True)}

    def status_report(self) -> str:
        """Print a startup status report."""
        lines = ["[MODULES] Subsystem status:"]
        for name, config in sorted(self._modules.items()):
            status = "✓ ON " if config.get("enabled", True) else "✗ OFF"
            desc = config.get("description", "")[:60]
            lines.append(f"  {status}  {name:<25} {desc}")
        return "\n".join(lines)

    def reload(self):
        """Hot-reload module config."""
        self._load()


# Module-level singleton
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules.json")
modules = ModuleLoader(_config_path)
