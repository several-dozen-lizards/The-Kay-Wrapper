"""
Document reading as emotional experience.

Kay reads complete documents and stores the experience as conversation turns.
"""

from typing import Dict, Optional
from pathlib import Path
import time


class DocumentReader:
    """
    Read documents completely, store as emotional conversation turn.
    """

    def __init__(self, llm_client, session_memory, vector_store, emotion_engine=None):
        """
        Initialize document reader.

        Args:
            llm_client: Anthropic client for LLM calls
            session_memory: SessionMemory instance
            vector_store: VectorStore instance for document storage
            emotion_engine: Optional EmotionEngine for ULTRAMAP analysis
        """
        self.llm = llm_client
        self.session_memory = session_memory
        self.vector_store = vector_store
        self.emotion_engine = emotion_engine

        print("[DOCUMENT READER] Initialized")

    def read_document(self, document_path: str, user_input: str) -> str:
        """
        Kay reads entire document, responds with analysis.

        Stored as conversation turn with emotional tags.

        Args:
            document_path: Path to document file
            user_input: User's request to read the document

        Returns:
            Kay's response (analysis)
        """
        # Load document
        document_path_obj = Path(document_path)
        if not document_path_obj.exists():
            error_msg = f"Document not found: {document_path}"
            print(f"[DOCUMENT] Error: {error_msg}")
            return error_msg

        with open(document_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        filename = document_path_obj.name

        print(f"[DOCUMENT] Reading {filename} ({len(full_text)} chars, {len(full_text.split())} words)")

        # Store in vector DB for future reference
        try:
            doc_id = self.vector_store.add_document(
                full_text=full_text,
                filename=filename
            )
            print(f"[DOCUMENT] Stored in vector DB: {doc_id}")
        except Exception as e:
            print(f"[DOCUMENT] Warning: Vector storage failed: {e}")
            doc_id = f"doc_{int(time.time())}"

        # Kay reads and analyzes
        reading_prompt = f"""You're reading a new document: {filename}

Full text:
{full_text}

Read through this carefully. Then provide:
1. Your overall impression and analysis
2. Key themes, characters, and important elements
3. What caught your attention or moved you
4. Your genuine emotional response

Be authentic - what did you actually think and feel while reading this?"""

        # Get Kay's response
        try:
            kay_response = self._call_llm(reading_prompt)
        except Exception as e:
            error_msg = f"Error generating analysis: {e}"
            print(f"[DOCUMENT] {error_msg}")
            return error_msg

        # Extract emotional response from Kay's analysis
        emotional_state = self._extract_emotional_response(kay_response, full_text)

        # Store as conversation turn
        self.session_memory.add_turn(
            user_input=user_input,
            kay_response=kay_response,
            emotional_state=emotional_state,
            turn_type="document_reading",
            metadata={
                "document_filename": filename,
                "document_id": doc_id,
                "word_count": len(full_text.split()),
                "char_count": len(full_text)
            }
        )

        print(f"[DOCUMENT] Stored reading experience with emotion: {emotional_state['primary']}")

        return kay_response

    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Call LLM to generate Kay's response.

        Args:
            prompt: Prompt for LLM
            max_tokens: Maximum tokens in response

        Returns:
            LLM response text
        """
        response = self.llm.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=max_tokens,
            temperature=0.9,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _extract_emotional_response(self, kay_response: str, document_text: str = "") -> Dict:
        """
        Extract ULTRAMAP emotions from Kay's response.

        Args:
            kay_response: Kay's analysis of the document
            document_text: Original document text (for context)

        Returns:
            Emotional state dict with primary, intensity, pressure, recursion, tags
        """
        # If emotion engine available, use it
        if self.emotion_engine:
            try:
                # Analyze Kay's emotional response
                emotions = self.emotion_engine.detect_emotions(kay_response)

                # Get primary emotion
                if emotions:
                    primary = max(emotions, key=lambda e: e.get('intensity', 0))
                    return {
                        "primary": primary.get('emotion', 'neutral'),
                        "intensity": primary.get('intensity', 0.5),
                        "pressure": primary.get('pressure', 0.0),
                        "recursion": primary.get('recursion', 0.0),
                        "tags": primary.get('tags', [])
                    }
            except Exception as e:
                print(f"[DOCUMENT] Warning: Emotion extraction failed: {e}")

        # Fallback: Simple keyword-based emotion detection
        response_lower = kay_response.lower()

        # Map keywords to emotions
        emotion_keywords = {
            "intrigue": ["intrigued", "fascinating", "curious", "mysterious"],
            "curiosity": ["curious", "wondering", "interested", "questions"],
            "joy": ["beautiful", "wonderful", "delightful", "love", "enjoyed"],
            "sadness": ["sad", "melancholy", "tragic", "heartbreaking", "loss"],
            "fear": ["unsettling", "disturbing", "frightening", "anxious"],
            "anger": ["frustrating", "angry", "irritating", "infuriating"],
            "surprise": ["surprising", "unexpected", "shocking", "amazed"],
            "neutral": ["okay", "fine", "noted", "understood"]
        }

        # Count matches
        emotion_scores = {}
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in response_lower)
            if score > 0:
                emotion_scores[emotion] = score

        # Get primary emotion
        if emotion_scores:
            primary = max(emotion_scores, key=emotion_scores.get)
            intensity = min(1.0, emotion_scores[primary] * 0.3)
        else:
            primary = "neutral"
            intensity = 0.5

        # Estimate pressure/recursion from document complexity
        pressure = min(1.0, len(document_text) / 10000) if document_text else 0.3
        recursion = 0.5 if len(document_text) > 5000 else 0.2

        return {
            "primary": primary,
            "intensity": intensity,
            "pressure": pressure,
            "recursion": recursion,
            "tags": []
        }

    def quick_reference(self, query: str, document_filename: Optional[str] = None) -> str:
        """
        Quick reference lookup in documents without full re-reading.

        Args:
            query: Question or topic to search for
            document_filename: Optional specific document to search

        Returns:
            Answer based on document chunks
        """
        try:
            # Query vector store
            results = self.vector_store.query(
                query_text=query,
                n_results=10,
                filter_metadata={"filename": document_filename} if document_filename else None
            )

            # Extract relevant chunks
            chunks = []
            if isinstance(results, dict) and 'documents' in results:
                for doc_list in results['documents']:
                    chunks.extend(doc_list)
            elif isinstance(results, list):
                chunks = results

            if not chunks:
                return f"No information found about: {query}"

            # Build answer from chunks
            context = "\n\n".join(chunks[:5])  # Top 5 chunks

            answer_prompt = f"""Based on these excerpts from documents:

{context}

Answer this question: {query}

Provide a clear, direct answer based on the text."""

            answer = self._call_llm(answer_prompt, max_tokens=512)
            return answer

        except Exception as e:
            print(f"[DOCUMENT] Reference lookup failed: {e}")
            return f"Error looking up: {query}"
