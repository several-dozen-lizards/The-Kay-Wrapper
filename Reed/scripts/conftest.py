"""
Configuration for AlphaKayZero scripts.
Adds the project root to Python path so scripts can import project modules.

For scripts that need to run standalone, add this at the top:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
