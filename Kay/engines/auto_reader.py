"""
Automatic Document Reader

Handles seamless automatic reading of document segments.
Kay reads through entire documents internally, responding naturally to each segment
without exposing document text or navigation to the user.

User flow:
1. User clicks Import
2. Kay automatically reads through all segments
3. Kay's natural responses appear in chat as normal conversation
4. Document stored in RAG for later reference
"""

import asyncio
import time
from typing import Callable, Dict, Any, Optional
from pathlib import Path


class AutoReader:
    """
    Handles automatic sequential reading of document segments.
    Feeds each segment to Kay's LLM and collects natural responses.
    """

    def __init__(self, get_llm_response_func: Callable, add_message_func: Callable, memory_engine=None):
        """
        Initialize auto-reader.

        Args:
            get_llm_response_func: Function to call for LLM responses (should include full context)
            add_message_func: Function to display messages in UI/console
            memory_engine: Optional memory engine for storing reading turns
        """
        self.get_response = get_llm_response_func
        self.add_message = add_message_func
        self.memory = memory_engine
        self.is_reading = False

    async def read_document_async(self, doc_reader, doc_name: str, agent_state=None, start_segment=1):
        """
        Automatically read through all segments of a document.

        This is the async version for use with UI event loops.

        Args:
            doc_reader: DocumentReader instance with loaded segments
            doc_name: Name of document being read
            agent_state: Optional agent state for full context
            start_segment: Which segment to start from (1-indexed, default 1)

        Returns:
            Dict with reading statistics (segments_read, responses, errors)
        """
        if self.is_reading:
            print("[AUTO READER] Already processing a document")
            return {'segments_read': 0, 'responses': [], 'errors': ['Auto-reader already active']}

        self.is_reading = True
        total_segments = doc_reader.total_chunks
        responses = []
        errors = []

        print(f"[AUTO READER] Starting: {doc_name} (segments {start_segment}-{total_segments})")

        # Start from specified segment (convert to 0-indexed)
        start_pos = max(0, start_segment - 1)
        doc_reader.current_position = start_pos

        try:
            for i in range(start_pos, total_segments):
                chunk_info = doc_reader.get_current_chunk()

                if not chunk_info:
                    error_msg = f"No chunk available at position {i}"
                    errors.append(error_msg)
                    print(f"[AUTO READER ERROR] {error_msg}")
                    break

                print(f"[AUTO READER] Processing segment {chunk_info['position']}/{chunk_info['total']}")

                # Build Kay's internal reading prompt
                reading_prompt = self._build_reading_prompt(chunk_info)

                try:
                    # Get Kay's response (this uses full LLM pipeline)
                    response = await self._get_kay_response_async(reading_prompt, agent_state)

                    # Store response
                    responses.append({
                        'segment': chunk_info['position'],
                        'response': response
                    })

                    # Display ONLY Kay's response in chat (NOT the document text)
                    self.add_message("kay", response)

                    # Store in memory if available
                    if self.memory:
                        self._store_reading_turn(chunk_info, response, agent_state)

                    # Brief pause between segments (feels more natural)
                    await asyncio.sleep(0.3)

                except Exception as e:
                    error_msg = f"Error processing segment {chunk_info['position']}: {str(e)}"
                    errors.append(error_msg)
                    print(f"[AUTO READER ERROR] {error_msg}")

                # Advance to next segment
                if i < total_segments - 1:
                    if not doc_reader.advance():
                        error_msg = f"Could not advance from segment {chunk_info['position']}"
                        errors.append(error_msg)
                        print(f"[AUTO READER ERROR] {error_msg}")
                        break

            print(f"[AUTO READER] Completed: {doc_name}")
            self.add_message("system", f"Finished reading {doc_name}")

            return {
                'segments_read': len(responses),
                'responses': responses,
                'errors': errors
            }

        except Exception as e:
            error_msg = f"Error during reading: {str(e)}"
            errors.append(error_msg)
            print(f"[AUTO READER] {error_msg}")
            self.add_message("system", f"Error reading document: {e}")
            return {
                'segments_read': len(responses),
                'responses': responses,
                'errors': errors
            }

        finally:
            self.is_reading = False

    def read_document_sync(self, doc_reader, doc_name: str, agent_state=None, start_segment=1):
        """
        Synchronous version for CLI/terminal use.

        Args:
            doc_reader: DocumentReader instance with loaded segments
            doc_name: Name of document being read
            agent_state: Optional agent state for full context
            start_segment: Which segment to start from (1-indexed, default 1)

        Returns:
            Dict with reading statistics (segments_read, responses, errors)
        """
        if self.is_reading:
            print("[AUTO READER] Already processing a document")
            return {'segments_read': 0, 'responses': [], 'errors': ['Auto-reader already active']}

        self.is_reading = True
        total_segments = doc_reader.total_chunks
        responses = []
        errors = []

        print(f"[AUTO READER] Starting: {doc_name} (segments {start_segment}-{total_segments})")

        # Start from specified segment (convert to 0-indexed)
        start_pos = max(0, start_segment - 1)
        doc_reader.current_position = start_pos

        try:
            for i in range(start_pos, total_segments):
                chunk_info = doc_reader.get_current_chunk()

                if not chunk_info:
                    error_msg = f"No chunk available at position {i}"
                    errors.append(error_msg)
                    print(f"[AUTO READER ERROR] {error_msg}")
                    break

                print(f"[AUTO READER] Processing segment {chunk_info['position']}/{chunk_info['total']}")

                # Build Kay's internal reading prompt
                reading_prompt = self._build_reading_prompt(chunk_info)

                try:
                    # Get Kay's response (synchronous)
                    response = self._get_kay_response_sync(reading_prompt, agent_state)

                    # Store response
                    responses.append({
                        'segment': chunk_info['position'],
                        'response': response
                    })

                    # Display ONLY Kay's response in chat (NOT the document text)
                    self.add_message("kay", response)

                    # Store in memory if available
                    if self.memory:
                        self._store_reading_turn(chunk_info, response, agent_state)

                    # Brief pause between segments
                    time.sleep(0.3)

                except Exception as e:
                    error_msg = f"Error processing segment {chunk_info['position']}: {str(e)}"
                    errors.append(error_msg)
                    print(f"[AUTO READER ERROR] {error_msg}")

                # Advance to next segment
                if i < total_segments - 1:
                    if not doc_reader.advance():
                        error_msg = f"Could not advance from segment {chunk_info['position']}"
                        errors.append(error_msg)
                        print(f"[AUTO READER ERROR] {error_msg}")
                        break

            print(f"[AUTO READER] Completed: {doc_name}")
            self.add_message("system", f"Finished reading {doc_name}")

            return {
                'segments_read': len(responses),
                'responses': responses,
                'errors': errors
            }

        except Exception as e:
            error_msg = f"Error during reading: {str(e)}"
            errors.append(error_msg)
            print(f"[AUTO READER] {error_msg}")
            self.add_message("system", f"Error reading document: {e}")
            return {
                'segments_read': len(responses),
                'responses': responses,
                'errors': errors
            }

        finally:
            self.is_reading = False

    def _build_reading_prompt(self, chunk_info: Dict[str, Any]) -> str:
        """
        Build the internal prompt that Kay sees (never shown to user).

        This creates natural reading instructions that prompt Kay to respond
        conversationally to each segment.
        """
        segment_num = chunk_info['position']
        total_segments = chunk_info['total']
        doc_name = chunk_info['doc_name']
        text = chunk_info['text']

        # Contextual intro based on position
        if segment_num == 1:
            intro = f"You're reading a document called '{doc_name}'. This is the beginning."
        elif segment_num == total_segments:
            intro = f"This is the final section of '{doc_name}'."
        else:
            intro = f"Continuing '{doc_name}' - section {segment_num} of {total_segments}."

        prompt = f"""{intro}

Read this segment and share your natural thoughts, reactions, or observations.
Comment on whatever strikes you - characters, writing style, specific moments, questions
that arise, connections you notice. Be conversational and authentic, as if you're sharing
your reading experience with Re.

SEGMENT TEXT:
{text}

Your response (be natural and specific):"""

        return prompt

    async def _get_kay_response_async(self, prompt: str, agent_state=None) -> str:
        """
        Get Kay's response to a segment (async version).

        This should call your existing conversation processing that includes
        memory retrieval, emotional state, context building, etc.
        """
        try:
            # Call the response function (which should handle full context)
            response = await asyncio.to_thread(
                self.get_response,
                prompt,
                agent_state
            )
            return response
        except Exception as e:
            print(f"[AUTO READER] Error getting response: {e}")
            return f"[Error processing segment: {e}]"

    def _get_kay_response_sync(self, prompt: str, agent_state=None) -> str:
        """
        Get Kay's response to a segment (synchronous version).
        """
        try:
            response = self.get_response(prompt, agent_state)
            return response
        except Exception as e:
            print(f"[AUTO READER] Error getting response: {e}")
            return f"[Error processing segment: {e}]"

    def _store_reading_turn(self, chunk_info: Dict[str, Any], response: str, agent_state=None):
        """
        Store Kay's reading response in memory.

        Creates a synthetic conversation turn for the reading session.
        """
        if not self.memory:
            return

        try:
            # Create a context string for the "user input"
            user_context = f"[Reading {chunk_info['doc_name']}, section {chunk_info['position']}/{chunk_info['total']}]"

            # Get current emotions for memory encoding
            current_emotions = []
            if agent_state and hasattr(agent_state, 'emotional_cocktail'):
                current_emotions = list(agent_state.emotional_cocktail.keys())

            # Store as a conversation turn using the actual memory engine API
            # Note: parameter is 'emotion_tags' not 'emotional_tags'
            self.memory.encode(
                agent_state=agent_state,
                user_input=user_context,
                response=response,
                emotion_tags=current_emotions
            )

            print(f"[AUTO READER] Stored memory: segment {chunk_info['position']}/{chunk_info['total']}")
        except Exception as e:
            print(f"[AUTO READER] Warning: Could not store reading turn in memory: {e}")


# Helper function for easy integration
def create_auto_reader(llm_response_func, message_display_func, memory_engine=None):
    """
    Factory function to create an AutoReader instance.

    Args:
        llm_response_func: Function that gets Kay's response to a prompt
        message_display_func: Function that displays messages in UI/console
        memory_engine: Optional memory engine for storing turns

    Returns:
        AutoReader instance

    Example:
        auto_reader = create_auto_reader(
            llm_response_func=lambda prompt, state: get_llm_response(prompt),
            message_display_func=lambda role, msg: print(f"{role}: {msg}"),
            memory_engine=memory_engine
        )
    """
    return AutoReader(llm_response_func, message_display_func, memory_engine)
