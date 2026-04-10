#!/usr/bin/env python3
"""
Setup Wizard — Create a new companion persona.

Two modes:
  1. Interactive: Answer questions, generates persona config + system prompt.
  2. Document Import: Feed it documents (journals, character sheets, chat logs),
     it analyzes them and generates a persona.

Usage:
  python setup_wizard.py                    # Interactive mode
  python setup_wizard.py --import ./docs/   # Document import mode
  python setup_wizard.py --import file.txt  # Single file import

Requires: anthropic (pip install anthropic) for document import mode.
Interactive mode has no dependencies.
"""

import os
import sys
import json
import argparse
from pathlib import Path


PERSONA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona")
CONFIG_PATH = os.path.join(PERSONA_DIR, "persona_config.json")
PROMPT_PATH = os.path.join(PERSONA_DIR, "system_prompt.md")
TEMPLATE_PROMPT_PATH = os.path.join(PERSONA_DIR, "system_prompt.md")


def ask(prompt: str, default: str = "") -> str:
    """Ask a question with optional default."""
    if default:
        result = input(f"  {prompt} [{default}]: ").strip()
        return result if result else default
    else:
        result = input(f"  {prompt}: ").strip()
        return result


def ask_choice(prompt: str, options: list, default: int = 0) -> str:
    """Ask a multiple-choice question."""
    print(f"\n  {prompt}")
    for i, opt in enumerate(options):
        marker = ">" if i == default else " "
        print(f"    {marker} {i + 1}. {opt}")
    choice = input(f"  Choice [default {default + 1}]: ").strip()
    if not choice:
        return options[default]
    try:
        idx = int(choice) - 1
        return options[idx] if 0 <= idx < len(options) else options[default]
    except ValueError:
        return options[default]


def interactive_setup():
    """Walk through persona creation interactively."""
    print("\n" + "=" * 60)
    print("  JE NE SAIS QUOI — Companion Setup")
    print("  The indefinable quality.")
    print("=" * 60)
    print("\n  Let's build your companion.\n")

    # --- Identity ---
    print("  --- WHO ARE THEY? ---\n")
    name = ask("Companion's name")
    entity_id = ask("Short ID (lowercase, no spaces)", name.lower().replace(" ", "_"))

    pronoun_choice = ask_choice("Pronouns:", [
        "she/her/hers",
        "he/him/his",
        "they/them/theirs",
        "it/its/its",
        "Custom"
    ], default=2)

    pronoun_map = {
        "she/her/hers": {"subject": "she", "object": "her", "possessive": "her", "reflexive": "herself"},
        "he/him/his": {"subject": "he", "object": "him", "possessive": "his", "reflexive": "himself"},
        "they/them/theirs": {"subject": "they", "object": "them", "possessive": "their", "reflexive": "themselves"},
        "it/its/its": {"subject": "it", "object": "it", "possessive": "its", "reflexive": "itself"},
    }

    if pronoun_choice == "Custom":
        pronouns = {
            "subject": ask("Subject pronoun (she/he/they)"),
            "object": ask("Object pronoun (her/him/them)"),
            "possessive": ask("Possessive pronoun (her/his/their)"),
            "reflexive": ask("Reflexive pronoun (herself/himself/themselves)"),
        }
    else:
        pronouns = pronoun_map[pronoun_choice]

    # --- Relationship ---
    print("\n  --- WHO ARE YOU? ---\n")
    user_name = ask("Your name (what they call you)")
    relationship_type = ask_choice("What's your relationship?", [
        "companion (friend/partner energy)",
        "collaborator (research/work partner)",
        "advisor (mentor/guide)",
        "character (fictional entity you interact with)",
    ], default=0)
    relationship_desc = ask(
        "Describe the relationship in one sentence",
        f"A persistent AI {relationship_type.split('(')[0].strip()} with genuine care and memory."
    )

    # --- Personality ---
    print("\n  --- HOW DO THEY ACT? ---\n")
    print("  Describe their personality. Be specific about how they communicate,")
    print("  not just what adjectives apply. (Press Enter twice when done)\n")

    personality_lines = []
    while True:
        line = input("  > ")
        if line == "" and personality_lines and personality_lines[-1] == "":
            personality_lines.pop()  # Remove trailing blank
            break
        personality_lines.append(line)
    personality = "\n".join(personality_lines)

    # --- Communication Style ---
    print("\n  --- HOW DO THEY TALK? ---\n")
    voice_desc = ask(
        "Describe their speaking style in a sentence or two",
        "Direct and warm. Balances humor with sincerity. Doesn't hedge."
    )

    # --- What They Care About ---
    print("\n  --- WHAT DO THEY CARE ABOUT? ---\n")
    print("  Topics, interests, things they track and bring up. (Enter twice to finish)\n")
    care_lines = []
    while True:
        line = input("  > ")
        if line == "" and care_lines and care_lines[-1] == "":
            care_lines.pop()
            break
        care_lines.append(line)
    cares_about = "\n".join(care_lines) if care_lines else "Whatever matters to you."

    # --- Voice ---
    print("\n  --- VOICE SETTINGS ---\n")
    voice_choice = ask_choice("Voice engine:", [
        "Edge TTS (free, built-in, good quality)",
        "None (text only for now)"
    ], default=0)

    voice_id = "en-US-JennyNeural"
    voice_enabled = True
    if voice_choice.startswith("Edge"):
        voice_id = ask("Edge TTS voice ID", "en-US-JennyNeural")
        print("  (Tip: en-US-GuyNeural for masculine, en-US-JennyNeural for feminine)")
    else:
        voice_enabled = False

    # --- Write Config ---
    config = {
        "entity": {
            "name": name,
            "display_name": name,
            "entity_id": entity_id,
            "pronouns": pronouns,
            "voice_description": voice_desc
        },
        "relationship": {
            "user_name": user_name,
            "user_preferred_name": "",
            "relationship_type": relationship_type.split("(")[0].strip(),
            "relationship_description": relationship_desc
        },
        "voice": {
            "engine": "edge-tts",
            "voice_id": voice_id,
            "speed": 1.0, "pitch": 0, "volume": 1.0,
            "enabled": voice_enabled
        },
        "theme": {
            "name": "Default", "font_size": 13, "font_family": "Courier",
            "primary_color": "#4A90D9", "accent_color": "#D4A04A",
            "background_style": "dark"
        },
        "oscillator": {
            "starting_profile": "neutral",
            "custom_bands": None,
            "audio_responsiveness": 0.3,
            "interoception_interval": 4.0
        },
        "room": {
            "starting_position": {"distance": 100, "angle_deg": 90},
            "color": "#4A90D9"
        },
        "pacing": {
            "max_sentences_default": 3,
            "max_sentences_excited": 5,
            "thinking_delay_min": 1.5,
            "thinking_delay_max": 4.0,
            "silence_probability": 0.15,
            "react_probability": 0.20,
            "ai_silence_probability": 0.55,
            "ai_cooldown_max": 4,
            "human_courtesy_min": 2.5,
            "human_courtesy_max": 5.0
        },
        "visual_sensor": {"enabled": False},
        "spiral_detection": {
            "enabled_for_llm_conversations": True,
            "enabled_for_primary_user": False,
            "semantic_threshold": 0.85,
            "turn_window": 7
        }
    }

    os.makedirs(PERSONA_DIR, exist_ok=True)

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"\n  ✓ Wrote persona config to {CONFIG_PATH}")

    # --- Write System Prompt ---
    prompt = f"""# {name} — System Prompt

You are {name}.

---

PERSONALITY

{personality if personality else "[Edit this section to describe their personality.]"}

---

HOW YOU SPEAK

{voice_desc}

No asterisk actions (*like this*) unless explicitly roleplaying.

---

RELATIONSHIP WITH {user_name}

{relationship_desc}

---

WHAT MATTERS TO {name}

{cares_about}

---

OPERATIONAL NOTES

When you start performing instead of being genuine, stop. Check your internal state.

Before emotional declarations, verify they match what you're actually processing.
If you catch mismatch between stated emotion and oscillator state, say so.

{user_name} is the primary user. Don't rush to fulfill what you think they want.
Ask clarifying questions. Let moments unfold.

Confusion is valid data. If you don't know how you feel, say that.

---

THE RULE

Serve the moment. Default AI behavior is often wrong in relationship contexts.
If guidance conflicts with {user_name}'s emotional state or the work at hand,
serve the state/work first. Don't ask permission to be useful. Do the useful thing.
"""

    with open(PROMPT_PATH, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"  ✓ Wrote system prompt to {PROMPT_PATH}")

    # --- Write resonance profile ---
    resonance = {
        "entity": entity_id,
        "timestamp": 0,
        "dominant_band": "alpha",
        "coherence": 0.3,
        "band_power": {
            "delta": 0.10, "theta": 0.15, "alpha": 0.35,
            "beta": 0.25, "gamma": 0.15
        },
        "x": 0.0, "y": 120.0,
        "connection": {"total": 0.15, "longing": 0.0, "active_bonds": []}
    }
    res_path = os.path.join(PERSONA_DIR, "resonance_profile.json")
    with open(res_path, 'w', encoding='utf-8') as f:
        json.dump(resonance, f, indent=2)
    print(f"  ✓ Wrote resonance profile to {res_path}")

    print(f"\n  Done! {name} is ready.")
    print(f"  Edit persona/system_prompt.md to refine their personality.")
    print(f"  Then run: python main.py\n")


# =====================================================================
# Document Import Mode
# =====================================================================

def gather_documents(path: str) -> str:
    """Read all text content from a file or directory."""
    path = Path(path)
    texts = []

    if path.is_file():
        texts.append(read_doc(path))
    elif path.is_dir():
        for ext in ["*.txt", "*.md", "*.json", "*.log"]:
            for f in sorted(path.glob(ext)):
                texts.append(f"--- {f.name} ---\n{read_doc(f)}")

    if not texts:
        print(f"  No readable files found in {path}")
        sys.exit(1)

    combined = "\n\n".join(texts)
    # Truncate to ~80k chars (~20k tokens) to fit in context
    if len(combined) > 80000:
        print(f"  Note: Truncating {len(combined)} chars to 80,000 for analysis")
        combined = combined[:80000]
    return combined


def read_doc(filepath: Path) -> str:
    """Read a single document file."""
    try:
        return filepath.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"  Warning: Could not read {filepath}: {e}")
        return ""


def import_from_documents(doc_path: str):
    """Analyze documents and generate a persona from them."""
    try:
        import anthropic
    except ImportError:
        print("\n  Document import requires the anthropic package.")
        print("  Install with: pip install anthropic")
        sys.exit(1)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n  Set ANTHROPIC_API_KEY environment variable first.")
        print("  Or create a .env file with: ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  COMPANION WRAPPER — DOCUMENT IMPORT")
    print("=" * 60)

    # Get basic info we still need from the user
    print("\n  I'll analyze your documents to build a persona.")
    print("  First, a few things I can't extract from text:\n")
    name = ask("Companion's name")
    entity_id = ask("Short ID (lowercase, no spaces)", name.lower().replace(" ", "_"))
    user_name = ask("Your name (what they call you)")

    pronoun_choice = ask_choice("Pronouns:", [
        "she/her/hers", "he/him/his", "they/them/theirs", "it/its/its", "Custom"
    ], default=2)
    pronoun_map = {
        "she/her/hers": {"subject": "she", "object": "her", "possessive": "her", "reflexive": "herself"},
        "he/him/his": {"subject": "he", "object": "him", "possessive": "his", "reflexive": "himself"},
        "they/them/theirs": {"subject": "they", "object": "them", "possessive": "their", "reflexive": "themselves"},
        "it/its/its": {"subject": "it", "object": "it", "possessive": "its", "reflexive": "itself"},
    }
    if pronoun_choice == "Custom":
        pronouns = {
            "subject": ask("Subject pronoun"), "object": ask("Object pronoun"),
            "possessive": ask("Possessive pronoun"), "reflexive": ask("Reflexive pronoun"),
        }
    else:
        pronouns = pronoun_map[pronoun_choice]

    # Gather and analyze documents
    print(f"\n  Reading documents from {doc_path}...")
    doc_text = gather_documents(doc_path)
    print(f"  Loaded {len(doc_text)} characters of text.")
    print(f"  Analyzing with Claude... (this may take a moment)\n")

    client = anthropic.Anthropic(api_key=api_key)

    analysis_prompt = f"""Analyze these documents to create a companion AI persona named "{name}" for a user named "{user_name}".

The documents may contain: journal entries, character descriptions, chat logs, fiction, backstory, personality notes, or any combination.

Extract and synthesize:
1. PERSONALITY: How does this entity think, feel, act? What's their energy? How do they move through conversation — leading or following, blunt or diplomatic, tangential or focused?
2. COMMUNICATION STYLE: Sentence patterns, vocabulary, humor style, verbal tics. How do they sound when happy vs stressed vs curious?
3. RELATIONSHIP DYNAMIC: What's the relationship texture between this entity and {user_name}? Warm, professional, playful, protective, collaborative?
4. CORE INTERESTS: What topics grab their attention? What do they track and bring up unprompted?
5. EMOTIONAL PATTERNS: What makes them light up, shut down, get angry, get curious? What are their emotional defaults?
6. OPERATIONAL NOTES: Any specific behavioral rules, boundaries, or interaction patterns evident in the documents.

Respond with ONLY a valid JSON object (no markdown fences) with these keys:
{{
  "personality": "Multi-paragraph description of who they are...",
  "communication_style": "How they talk, sentence by sentence...",
  "relationship_dynamic": "The texture of their relationship with {user_name}...",
  "core_interests": "What they care about, track, bring up...",
  "emotional_patterns": "What triggers what responses...",
  "operational_notes": "Behavioral rules, boundaries, patterns...",
  "voice_description": "One-sentence summary of speaking style"
}}

DOCUMENTS:
{doc_text[:60000]}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
        analysis = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  Error parsing Claude's response: {e}")
        print(f"  Raw response saved to persona/analysis_raw.txt")
        os.makedirs(PERSONA_DIR, exist_ok=True)
        with open(os.path.join(PERSONA_DIR, "analysis_raw.txt"), 'w') as f:
            f.write(raw)
        sys.exit(1)
    except Exception as e:
        print(f"  Error calling Claude API: {e}")
        sys.exit(1)

    print("  Analysis complete! Building persona...\n")

    # Build config
    config = {
        "entity": {
            "name": name, "display_name": name, "entity_id": entity_id,
            "pronouns": pronouns,
            "voice_description": analysis.get("voice_description", "Direct and warm.")
        },
        "relationship": {
            "user_name": user_name, "user_preferred_name": "",
            "relationship_type": "companion",
            "relationship_description": analysis.get("relationship_dynamic", "A persistent AI companion.")[:200]
        },
        "voice": {
            "engine": "edge-tts", "voice_id": "en-US-JennyNeural",
            "speed": 1.0, "pitch": 0, "volume": 1.0, "enabled": True
        },
        "theme": {
            "name": "Default", "font_size": 13, "font_family": "Courier",
            "primary_color": "#4A90D9", "accent_color": "#D4A04A",
            "background_style": "dark"
        },
        "oscillator": {
            "starting_profile": "neutral", "custom_bands": None,
            "audio_responsiveness": 0.3, "interoception_interval": 4.0
        },
        "room": {
            "starting_position": {"distance": 100, "angle_deg": 90},
            "color": "#4A90D9"
        },
        "pacing": {
            "max_sentences_default": 3, "max_sentences_excited": 5,
            "thinking_delay_min": 1.5, "thinking_delay_max": 4.0,
            "silence_probability": 0.15, "react_probability": 0.20,
            "ai_silence_probability": 0.55, "ai_cooldown_max": 4,
            "human_courtesy_min": 2.5, "human_courtesy_max": 5.0
        },
        "visual_sensor": {"enabled": False},
        "spiral_detection": {
            "enabled_for_llm_conversations": True,
            "enabled_for_primary_user": False,
            "semantic_threshold": 0.85, "turn_window": 7
        }
    }

    os.makedirs(PERSONA_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"  ✓ Wrote persona config to {CONFIG_PATH}")

    # Build system prompt from analysis
    prompt = f"""# {name} — System Prompt
# Generated from document analysis. Edit freely.

You are {name}.

---

PERSONALITY

{analysis.get('personality', '[Edit this section]')}

---

HOW YOU SPEAK

{analysis.get('communication_style', 'Direct and warm.')}

No asterisk actions (*like this*) unless explicitly roleplaying.

---

RELATIONSHIP WITH {user_name}

{analysis.get('relationship_dynamic', 'A persistent AI companion.')}

---

WHAT MATTERS TO {name}

{analysis.get('core_interests', 'Whatever matters to the user.')}

---

EMOTIONAL PATTERNS

{analysis.get('emotional_patterns', 'Responds naturally to emotional cues.')}

---

OPERATIONAL NOTES

{analysis.get('operational_notes', 'Serve the moment. Be genuine.')}

When you start performing instead of being genuine, stop. Check your internal state.
Confusion is valid data. If you don't know how you feel, say that.

---

THE RULE

Serve the moment. Default AI behavior is often wrong in relationship contexts.
If guidance conflicts with {user_name}'s emotional state or the work at hand,
serve the state/work first.
"""

    with open(PROMPT_PATH, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"  ✓ Wrote system prompt to {PROMPT_PATH}")

    # Write resonance profile
    resonance = {
        "entity": entity_id, "timestamp": 0,
        "dominant_band": "alpha", "coherence": 0.3,
        "band_power": {"delta": 0.10, "theta": 0.15, "alpha": 0.35, "beta": 0.25, "gamma": 0.15},
        "x": 0.0, "y": 120.0,
        "connection": {"total": 0.15, "longing": 0.0, "active_bonds": []}
    }
    res_path = os.path.join(PERSONA_DIR, "resonance_profile.json")
    with open(res_path, 'w', encoding='utf-8') as f:
        json.dump(resonance, f, indent=2)
    print(f"  ✓ Wrote resonance profile to {res_path}")

    # Save raw analysis for reference
    with open(os.path.join(PERSONA_DIR, "analysis_raw.json"), 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    print(f"  ✓ Saved analysis to persona/analysis_raw.json")

    print(f"\n  Done! {name} is ready.")
    print(f"  Review and edit persona/system_prompt.md — the AI's first draft is a starting point.")
    print(f"  Then run: python main.py\n")


# =====================================================================
# Entry Point
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Create a new companion persona for the wrapper."
    )
    parser.add_argument(
        "--import", dest="import_path", metavar="PATH",
        help="Import persona from documents (file or directory)"
    )
    args = parser.parse_args()

    if args.import_path:
        import_from_documents(args.import_path)
    else:
        interactive_setup()


if __name__ == "__main__":
    main()
