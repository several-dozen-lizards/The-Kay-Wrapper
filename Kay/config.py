"""
Global configuration for KayZero.

Centralized settings that can be used across all modules.
"""

import os

# Debug verbosity control
# Set environment variable VERBOSE_DEBUG=true for detailed debugging
# Default: False (concise output)
VERBOSE_DEBUG = os.environ.get("VERBOSE_DEBUG", "false").lower() == "true"

# =============================================================================
# Working Memory / Prompt Size Control
# =============================================================================
# Number of conversation turns to include in the API prompt.
# This is the "working memory window" - recent turns for immediate context.
# Older conversation context is available via memory retrieval (episodic/semantic).
#
# IMPORTANT: This does NOT affect memory extraction - ALL turns are still
# processed for episodic/semantic memory creation. This only controls how many
# turns of raw conversation are included in each API call to reduce token costs.
#
# Set via environment variable or change default here.
# Default: 5 turns (enough for conversational coherence without quadratic growth)
WORKING_MEMORY_WINDOW = int(os.environ.get("WORKING_MEMORY_WINDOW", "5"))

# =============================================================================
# Context Budget Control (NEW: Prevents context bloat and hallucinations)
# =============================================================================
# These limits are ADAPTIVE - they automatically reduce when context grows large.
# The values here are the BASE limits for the NORMAL tier (context <10K tokens).
#
# Tier thresholds (tokens):
#   NORMAL: <10K tokens - full limits
#   REDUCED: 10-15K tokens - 50% limits
#   MINIMAL: 15-20K tokens - 30% limits
#   CRITICAL: >20K tokens - aggressive stripping

# Base memory limit (number of retrieved memories)
# Default: 100 (down from previous 250)
BASE_MEMORY_LIMIT = int(os.environ.get("BASE_MEMORY_LIMIT", "100"))

# Base RAG chunk limit (number of document chunks)
# Default: 20 (down from previous 50)
BASE_RAG_LIMIT = int(os.environ.get("BASE_RAG_LIMIT", "20"))

# Base working memory turns (conversation turns in context)
# Default: 3 (adaptive, overrides WORKING_MEMORY_WINDOW when budget is tight)
BASE_WORKING_TURNS = int(os.environ.get("BASE_WORKING_TURNS", "3"))

# =============================================================================
# Token-Based Working Memory Budget (for Continuous Session Mode)
# =============================================================================
# Instead of a fixed turn count, use a token budget for working memory.
# This adapts naturally to conversation style:
# - Rapid short exchanges = more turns visible
# - Deep technical discussions = fewer turns, same token budget
#
# Default: 3000 tokens (roughly equivalent to 5-10 average turns)
WORKING_MEMORY_TOKEN_BUDGET = int(os.environ.get("WORKING_MEMORY_TOKEN_BUDGET", "3000"))

# Session Summary Token Budget (for compressed context of older turns)
# This controls how much space is allocated for the summary of turns outside
# the working memory window. Combined with verbatim recent turns + emotional
# snapshot, this should stay within the model's context window.
#
# Default: 1500 tokens (allows ~15 preserved turns + topic summaries)
SESSION_SUMMARY_TOKEN_BUDGET = int(os.environ.get("SESSION_SUMMARY_TOKEN_BUDGET", "1500"))

# Image aging: turns after which images are archived from active context
# Default: 2 (images age out after 2 turns of non-mention)
IMAGE_AGING_TURNS = int(os.environ.get("IMAGE_AGING_TURNS", "2"))

# =============================================================================
# GitHub Integration
# =============================================================================
# GitHub Personal Access Token for API access
# Without token: 60 requests/hour, public repos only
# With token: 5000 requests/hour, can access private repos
#
# Create token at: https://github.com/settings/tokens
# Scopes needed: repo (for private repos), or just public_repo (for public only)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
