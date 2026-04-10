"""
Path utilities for the entity Zero
Ensures all file paths work regardless of current working directory
"""

import os
from pathlib import Path

# Get the project root directory (where this file's grandparent is)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def get_project_path(*path_parts) -> str:
    """
    Get absolute path relative to project root.

    Args:
        *path_parts: Path components (e.g., "memory", "memories.json")

    Returns:
        Absolute path string

    Examples:
        >>> get_project_path("memory", "memories.json")
        "F:/AlphaKayZero/memory/memories.json"

        >>> get_project_path("data", "ULTRAMAP.csv")
        "F:/AlphaKayZero/data/ULTRAMAP.csv"
    """
    return str(PROJECT_ROOT.joinpath(*path_parts))


def get_memory_path(filename: str) -> str:
    """
    Get absolute path to file in memory/ directory.

    Args:
        filename: Filename in memory directory

    Returns:
        Absolute path string
    """
    return get_project_path("memory", filename)


def get_data_path(filename: str) -> str:
    """
    Get absolute path to file in data/ directory.

    Args:
        filename: Filename in data directory

    Returns:
        Absolute path string
    """
    return get_project_path("data", filename)


def ensure_directory_exists(file_path: str):
    """
    Ensure parent directory exists for a file path.

    Args:
        file_path: Full file path (absolute or relative)
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


# Commonly used paths
MEMORY_DIR = get_project_path("memory")
DATA_DIR = get_project_path("data")
SESSIONS_DIR = get_project_path("sessions")

MEMORIES_JSON = get_memory_path("memories.json")
ENTITY_GRAPH_JSON = get_memory_path("entity_graph.json")
MEMORY_LAYERS_JSON = get_memory_path("memory_layers.json")
FOREST_JSON = get_memory_path("forest.json")
MOTIFS_JSON = get_memory_path("motifs.json")
PREFERENCES_JSON = get_memory_path("preferences.json")
DOCUMENTS_JSON = get_memory_path("documents.json")
IDENTITY_MEMORY_JSON = get_memory_path("identity_memory.json")
STATE_SNAPSHOT_JSON = get_memory_path("state_snapshot.json")

ULTRAMAP_CSV = get_data_path("Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv")

# Verify critical paths exist at import time
def verify_critical_paths():
    """Verify critical directories and files exist."""
    issues = []

    # Check directories
    for dir_path, name in [(MEMORY_DIR, "memory"), (DATA_DIR, "data")]:
        if not os.path.exists(dir_path):
            issues.append(f"Missing directory: {name}/ at {dir_path}")

    # Check ULTRAMAP
    if not os.path.exists(ULTRAMAP_CSV):
        issues.append(f"Missing ULTRAMAP file at {ULTRAMAP_CSV}")

    if issues:
        print("[PATH WARNING] Issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        return False

    return True


if __name__ == "__main__":
    # Test path utilities
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("MEMORY_DIR:", MEMORY_DIR)
    print("DATA_DIR:", DATA_DIR)
    print()
    print("Sample paths:")
    print("  memories.json:", MEMORIES_JSON)
    print("  ULTRAMAP:", ULTRAMAP_CSV)
    print()
    print("Verification:")
    if verify_critical_paths():
        print("  ✓ All critical paths exist")
    else:
        print("  ✗ Some paths missing")
