"""
DocumentReadingSession - Single-document focused reading mode.

Tracks when Kay is reading through a specific document section by section,
preventing multi-document loading chaos and enabling sequential navigation.
"""

class DocumentReadingSession:
    """
    Tracks when Kay is reading through a specific document section by section.

    Prevents the multi-document loading issue where LLM retrieval loads
    ALL related documents simultaneously (e.g., YW giant file + YW-part1 + yw-part2).

    When active, ONLY the locked document is loaded into Reed's context,
    and "continue reading" advances through its sections sequentially.
    """

    def __init__(self):
        self.active = False
        self.doc_id = None
        self.doc_name = None
        self.doc_reader = None
        self.current_section = 0
        self.total_sections = 0

    def start_reading(self, doc_id, doc_name, doc_reader):
        """
        Begin focused reading session on one document.

        Args:
            doc_id: Document memory ID
            doc_name: Display name of document
            doc_reader: DocumentReader instance loaded with this document
        """
        self.active = True
        self.doc_id = doc_id
        self.doc_name = doc_name
        self.doc_reader = doc_reader
        self.current_section = doc_reader.current_position + 1  # 1-indexed for display (FIX: was current_index)
        self.total_sections = len(doc_reader.chunks)

        print(f"[READING SESSION] Started: {doc_name} ({self.total_sections} sections)")
        print(f"[READING SESSION] Current position: section {self.current_section}/{self.total_sections}")

    def advance(self):
        """
        Move to next section.

        Returns:
            bool: True if advanced successfully, False if at end
        """
        if not self.doc_reader:
            print("[READING SESSION] ERROR: No document reader available")
            return False

        if self.current_section >= self.total_sections:
            print(f"[READING SESSION] Already at end: section {self.current_section}/{self.total_sections}")
            return False

        # Advance doc_reader to next chunk
        self.doc_reader.advance()
        self.current_section = self.doc_reader.current_position + 1  # FIX: was current_index

        print(f"[READING SESSION] Advanced to section {self.current_section}/{self.total_sections}")
        return True

    def at_end(self):
        """Check if we're at the last section."""
        return self.current_section >= self.total_sections

    def get_current_chunk(self):
        """Get the current document chunk being read."""
        if not self.doc_reader:
            return None
        return self.doc_reader.get_current_chunk()

    def end_reading(self):
        """End the reading session."""
        print(f"[READING SESSION] Completed: {self.doc_name} ({self.current_section}/{self.total_sections} sections)")
        self.active = False
        self.doc_id = None
        self.doc_name = None
        self.doc_reader = None
        self.current_section = 0
        self.total_sections = 0

    def get_progress_text(self):
        """Get human-readable progress text."""
        if not self.active:
            return ""

        remaining = self.total_sections - self.current_section
        if remaining > 0:
            return f"Section {self.current_section}/{self.total_sections} ({remaining} sections left)"
        else:
            return f"Section {self.current_section}/{self.total_sections} (complete)"

    def __repr__(self):
        if self.active:
            return f"<ReadingSession: {self.doc_name} ({self.current_section}/{self.total_sections})>"
        return "<ReadingSession: inactive>"


def detect_read_request(user_input, reading_session):
    """
    Detect if user is asking to read through a document or continue reading.

    Args:
        user_input: User's message
        reading_session: Current DocumentReadingSession instance

    Returns:
        tuple: (request_type, doc_hint)
            request_type: "continue", "start", or "normal"
            doc_hint: Full user input for document name extraction (or None)
    """
    read_triggers = [
        "read through",
        "read the",
        "go through",
        "review the",
        "look through",
        "analyze the",
        "walk through",
        "go over"
    ]

    continuation_triggers = [
        "continue reading",
        "next section",
        "keep going",
        "keep reading",
        "continue",
        "next"
    ]

    lower_input = user_input.lower().strip()

    # Check for continuation of existing session
    if reading_session.active:
        for trigger in continuation_triggers:
            if trigger in lower_input:
                print(f"[READ DETECTION] Continuation detected: '{trigger}' in '{user_input}'")
                return "continue", None

    # Check for new read request
    for trigger in read_triggers:
        if trigger in lower_input:
            print(f"[READ DETECTION] New read request detected: '{trigger}' in '{user_input}'")
            return "start", user_input

    return "normal", None


def extract_document_hint(user_input):
    """
    Extract hints about which document user wants to read.

    Examples:
        "read through the YW part 2" -> "yw-part2" or "part 2" or "yurt"
        "review the sweetness document" -> "sweetness"

    Returns:
        list: Keywords to help select document
    """
    lower = user_input.lower()
    hints = []

    # Extract quoted phrases
    import re
    quoted = re.findall(r'"([^"]+)"', user_input)
    hints.extend(quoted)

    # Common document keywords
    if "yw" in lower or "yurt" in lower:
        hints.append("yurt")
        if "part 2" in lower or "part2" in lower or "part-2" in lower:
            hints.append("part2")
            hints.append("part-2")
        elif "part 1" in lower or "part1" in lower or "part-1" in lower:
            hints.append("part1")
            hints.append("part-1")
        elif "giant" in lower or "messy" in lower:
            hints.append("giant")
            hints.append("messy")

    if "sweetness" in lower or "dragon" in lower:
        hints.append("sweetness")
        hints.append("dragon")

    if "pigeon" in lower:
        hints.append("pigeon")

    print(f"[DOCUMENT HINT] Extracted hints from '{user_input}': {hints}")
    return hints


def select_best_document(retrieved_docs, hints):
    """
    Select the best document from retrieved docs based on hints.

    Args:
        retrieved_docs: List of document dicts with 'name', 'id', 'text'
        hints: List of keyword hints

    Returns:
        dict: Best matching document, or first doc if no matches
    """
    if not retrieved_docs:
        return None

    if not hints:
        # No hints - return first (most relevant from LLM retrieval)
        print(f"[DOCUMENT SELECTION] No hints, using first doc: {retrieved_docs[0].get('filename', 'unknown')}")
        return retrieved_docs[0]

    # Score each document by hint matches
    scored = []
    for doc in retrieved_docs:
        doc_name = doc.get('filename', doc.get('name', '')).lower()
        score = 0

        for hint in hints:
            hint_lower = hint.lower()
            if hint_lower in doc_name:
                score += 1

        scored.append((score, doc))

    # Sort by score (highest first)
    scored.sort(key=lambda x: x[0], reverse=True)

    best_doc = scored[0][1]
    best_score = scored[0][0]

    print(f"[DOCUMENT SELECTION] Best match (score {best_score}): {best_doc.get('filename', 'unknown')}")
    print(f"[DOCUMENT SELECTION] All scores: {[(s, d.get('filename', 'unknown')[:40]) for s, d in scored]}")

    return best_doc
