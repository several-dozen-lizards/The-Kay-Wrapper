# branding.py
"""
Je Ne Sais Quoi — Project Identity Constants

Import these in modules that display project branding (startup banners,
help text, about dialogs) instead of hardcoding strings.

Usage:
    from branding import PROJECT_NAME, PROJECT_SHORT, PROJECT_VERSION
"""

# Project identity
PROJECT_NAME = "Je Ne Sais Quoi"
PROJECT_SHORT = "JNSQ"
PROJECT_VERSION = "1.0.0"
PROJECT_TAGLINE = "The indefinable quality."
PROJECT_DESCRIPTION = "A persistence and emotional architecture framework for AI companions."

# Banner strings
STARTUP_BANNER = f"""
{'=' * 50}
  {PROJECT_NAME.upper()}
  {PROJECT_TAGLINE}
{'=' * 50}
"""

MANAGER_BANNER = f"""
{'=' * 45}
  {PROJECT_NAME.upper()} — Companion Manager
{'=' * 45}
"""

# CLI name
CLI_NAME = "jnsq"

# Log tag
LOG_TAG = "[JNSQ]"
