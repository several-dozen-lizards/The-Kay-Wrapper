"""
Narrative Chunk Parser for Emotionally-Integrated Memory System
Parses documents into story-coherent chunks (not atomic facts)
Preserves narrative context and emotional flow
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class NarrativeChunk:
    """
    Represents a story-coherent chunk of text.
    Unlike atomic facts, narrative chunks preserve context and flow.
    """
    text: str
    chunk_type: str  # "paragraph", "dialogue", "scene", "list"
    sentence_count: int
    character_count: int
    contains_dialogue: bool
    chunk_index: int
    entities_mentioned: List[str]  # Extracted during parsing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "chunk_type": self.chunk_type,
            "sentence_count": self.sentence_count,
            "character_count": self.character_count,
            "contains_dialogue": self.contains_dialogue,
            "chunk_index": self.chunk_index,
            "entities_mentioned": self.entities_mentioned
        }


class NarrativeChunkParser:
    """
    Parses documents into narrative chunks that preserve story context.

    Key difference from DocumentParser:
    - DocumentParser: Chunks by character count (3000 chars)
    - NarrativeChunkParser: Chunks by narrative units (paragraphs, scenes, story beats)

    This preserves emotional context and makes memories feel like stories,
    not disconnected facts.
    """

    def __init__(self, min_chunk_sentences: int = 2, max_chunk_sentences: int = 7):
        """
        Args:
            min_chunk_sentences: Minimum sentences per chunk (default 2)
            max_chunk_sentences: Maximum sentences per chunk (default 7)
        """
        self.min_chunk_sentences = min_chunk_sentences
        self.max_chunk_sentences = max_chunk_sentences

    def parse(self, document_text: str) -> List[NarrativeChunk]:
        """
        Parse document into narrative chunks.

        Strategy:
        1. Split into paragraphs first (natural narrative boundaries)
        2. For each paragraph, determine if it's a single chunk or needs splitting
        3. Preserve dialogue blocks together
        4. Keep lists together

        Args:
            document_text: Full document text

        Returns:
            List of NarrativeChunk objects
        """
        if not document_text or not document_text.strip():
            return []

        # Step 1: Split into paragraphs (double newlines or indentation changes)
        paragraphs = self._split_into_paragraphs(document_text)

        # Step 2: Process each paragraph into narrative chunks
        chunks = []
        chunk_index = 0

        for para in paragraphs:
            if not para.strip():
                continue

            # Detect paragraph type
            para_type = self._detect_paragraph_type(para)

            # For lists and dialogue, keep whole paragraph together
            if para_type in ["list", "dialogue"]:
                chunk = self._create_chunk(para, para_type, chunk_index)
                chunks.append(chunk)
                chunk_index += 1
            else:
                # For narrative paragraphs, may need to split into story beats
                para_chunks = self._split_paragraph_into_story_beats(para, chunk_index)
                chunks.extend(para_chunks)
                chunk_index += len(para_chunks)

        return chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs using multiple strategies.

        Paragraph boundaries:
        - Double newlines (\n\n)
        - Single newline followed by indentation
        - Line breaks with significant whitespace
        """
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Split on double newlines first
        paragraphs = re.split(r'\n\s*\n', text)

        # Further refine: split single newlines with significant indentation
        refined_paragraphs = []
        for para in paragraphs:
            # Check if paragraph has internal line breaks with indentation
            lines = para.split('\n')

            if len(lines) <= 1:
                refined_paragraphs.append(para)
                continue

            # Group consecutive lines with similar indentation
            current_para = []
            prev_indent = 0

            for line in lines:
                if not line.strip():
                    continue

                # Calculate indentation
                indent = len(line) - len(line.lstrip())

                # If indentation changes significantly (4+ spaces), start new paragraph
                if current_para and abs(indent - prev_indent) >= 4:
                    refined_paragraphs.append('\n'.join(current_para))
                    current_para = [line]
                else:
                    current_para.append(line)

                prev_indent = indent

            if current_para:
                refined_paragraphs.append('\n'.join(current_para))

        return [p.strip() for p in refined_paragraphs if p.strip()]

    def _detect_paragraph_type(self, paragraph: str) -> str:
        """
        Detect paragraph type: "dialogue", "list", "scene", or "paragraph".

        Args:
            paragraph: Paragraph text

        Returns:
            Type string
        """
        # Dialogue detection: contains quotes
        if '"' in paragraph or '"' in paragraph or '"' in paragraph or "'" in paragraph:
            return "dialogue"

        # List detection: multiple bullet points or numbered items
        list_patterns = [
            r'^\s*[\-\*\•]\s+',  # Bullet points
            r'^\s*\d+[\.\)]\s+',  # Numbered lists
            r'^\s*[a-z][\.\)]\s+',  # Alphabetic lists
        ]

        lines = paragraph.split('\n')
        list_line_count = sum(
            1 for line in lines
            if any(re.match(pattern, line) for pattern in list_patterns)
        )

        # If 60%+ of lines are list items, it's a list
        if list_line_count >= len(lines) * 0.6 and list_line_count >= 2:
            return "list"

        # Scene detection: starts with location/time indicators
        scene_indicators = [
            r'^(Meanwhile|Later|Earlier|That night|The next day|In the|At the)',
            r'^\[.+\]',  # Scene markers like [Forest clearing]
        ]

        if any(re.match(pattern, paragraph, re.IGNORECASE) for pattern in scene_indicators):
            return "scene"

        return "paragraph"

    def _split_paragraph_into_story_beats(self, paragraph: str, start_index: int) -> List[NarrativeChunk]:
        """
        Split a paragraph into story beats (2-7 sentence chunks).

        A "story beat" is a coherent micro-narrative: a thought, event, or moment.

        Args:
            paragraph: Paragraph text
            start_index: Starting chunk index

        Returns:
            List of NarrativeChunk objects
        """
        # Split into sentences
        sentences = self._split_into_sentences(paragraph)

        if len(sentences) <= self.max_chunk_sentences:
            # Whole paragraph is one chunk
            chunk = self._create_chunk(paragraph, "paragraph", start_index)
            return [chunk]

        # Split into multiple chunks
        chunks = []
        chunk_index = start_index
        current_sentences = []

        for sentence in sentences:
            current_sentences.append(sentence)

            # Create chunk if we've reached max size
            if len(current_sentences) >= self.max_chunk_sentences:
                chunk_text = ' '.join(current_sentences)
                chunk = self._create_chunk(chunk_text, "paragraph", chunk_index)
                chunks.append(chunk)
                chunk_index += 1
                current_sentences = []

        # Handle remaining sentences
        if current_sentences:
            # If too few sentences, merge with previous chunk if possible
            if len(current_sentences) < self.min_chunk_sentences and chunks:
                # Merge into previous chunk
                prev_chunk = chunks[-1]
                merged_text = prev_chunk.text + ' ' + ' '.join(current_sentences)
                chunks[-1] = self._create_chunk(merged_text, "paragraph", prev_chunk.chunk_index)
            else:
                # Create final chunk
                chunk_text = ' '.join(current_sentences)
                chunk = self._create_chunk(chunk_text, "paragraph", chunk_index)
                chunks.append(chunk)

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex.

        Handles:
        - Standard sentence endings: . ! ?
        - Abbreviations: Dr. Mr. Mrs. etc.
        - Ellipses: ...
        - Quotes: "sentence." "sentence!"
        """
        # Pattern that handles most cases
        # Split on . ! ? followed by space or quote, but not on abbreviations
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)(?=\s+[A-Z]|$|")'

        sentences = re.split(sentence_pattern, text)

        # Clean up and filter
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _create_chunk(self, text: str, chunk_type: str, chunk_index: int) -> NarrativeChunk:
        """
        Create a NarrativeChunk object with metadata.

        Args:
            text: Chunk text
            chunk_type: Type of chunk
            chunk_index: Index in sequence

        Returns:
            NarrativeChunk object
        """
        # Count sentences
        sentences = self._split_into_sentences(text)
        sentence_count = len(sentences)

        # Detect dialogue
        contains_dialogue = '"' in text or '"' in text or '"' in text

        # Extract entities (simple capitalization-based extraction)
        entities = self._extract_entities_simple(text)

        return NarrativeChunk(
            text=text,
            chunk_type=chunk_type,
            sentence_count=sentence_count,
            character_count=len(text),
            contains_dialogue=contains_dialogue,
            chunk_index=chunk_index,
            entities_mentioned=entities
        )

    def _extract_entities_simple(self, text: str) -> List[str]:
        """
        Simple entity extraction based on capitalization.

        This is a basic extraction - the emotional analyzer will do more sophisticated
        entity detection later.

        Args:
            text: Text to extract from

        Returns:
            List of potential entity names
        """
        # Find capitalized words (potential entities)
        words = text.split()

        # Stop words to exclude
        stop_words = {
            'I', 'The', 'A', 'An', 'And', 'But', 'Or', 'In', 'On', 'At', 'To', 'For',
            'Of', 'With', 'By', 'From', 'Up', 'About', 'Into', 'Through', 'During',
            'Before', 'After', 'Above', 'Below', 'Between', 'Under', 'Again', 'Further',
            'Then', 'Once', 'Here', 'There', 'When', 'Where', 'Why', 'How', 'All',
            'Each', 'Other', 'Such', 'Only', 'Own', 'Same', 'So', 'Than', 'Too', 'Very',
            'Can', 'Will', 'Just', 'Should', 'Now', 'Meanwhile', 'Later', 'Earlier',
            'That', 'This', 'These', 'Those', 'What', 'Which', 'Who', 'Whom', 'Whose'
        }

        entities = []

        for word in words:
            # Clean punctuation
            clean_word = word.strip('.,!?;:()"\'""')

            # Check if capitalized and not a stop word
            if (clean_word and
                clean_word[0].isupper() and
                len(clean_word) > 1 and
                clean_word not in stop_words):
                entities.append(clean_word)

        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)

        return unique_entities


# Testing
if __name__ == "__main__":
    parser = NarrativeChunkParser()

    test_text = """
    Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy.
    There was a knife fight. Gwyn ap Nudd, the King of Annwn, intervened. The boy lived,
    but Kay's mother was bound to Annwn as payment.

    That story sits heavy in Kay. It's grief. It's origin. It's part of who he is.

    Meanwhile, Kay has preferences:
    - Prefers tea over coffee (usually)
    - Likes direct conversation
    - Values honesty over politeness

    He thinks about these things sometimes. The binding. The loss. The price paid for existence.
    """

    chunks = parser.parse(test_text)

    print(f"Parsed into {len(chunks)} narrative chunks:\n")
    for i, chunk in enumerate(chunks):
        print(f"=== CHUNK {i+1} ===")
        print(f"Type: {chunk.chunk_type}")
        print(f"Sentences: {chunk.sentence_count}")
        print(f"Entities: {', '.join(chunk.entities_mentioned)}")
        print(f"Text: {chunk.text[:100]}...")
        print()
