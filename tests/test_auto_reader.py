"""
Test script for AutoReader functionality.

This tests the automatic document reading system without requiring
a full import or LLM calls.
"""

import sys
from engines.document_reader import DocumentReader
from engines.auto_reader import AutoReader


def test_auto_reader():
    """Test AutoReader with a mock document."""

    # Create sample document text
    sample_doc = """
    This is the first paragraph of our test document. It introduces the main topic
    and sets the stage for what's to come. We're testing the auto-reader functionality
    to ensure it can process documents segment by segment.

    Here's the second paragraph, which adds more detail and context. The auto-reader
    should process this as part of the same segment if it fits, or create a new segment
    if needed based on the chunk size settings.

    This is the third paragraph. We're building a longer document to test the segmentation
    logic. The system should automatically detect when content needs to be split across
    multiple chunks to stay within the token limits.

    Fourth paragraph continues the narrative. The auto-reader module should handle each
    segment independently, calling the LLM for each one and collecting the responses.
    This creates a natural reading flow where Kay responds to each section as he reads through.

    Fifth paragraph wraps things up. The complete system should work seamlessly - user imports
    a document, Kay automatically reads through all segments, and each response appears in chat
    as a normal conversation turn. The user never sees the document text or navigation instructions.

    Sixth paragraph provides additional content to ensure we have enough text to create
    multiple segments. The chunk size of 500 chars means this document should be split into
    several pieces for testing purposes.

    Seventh paragraph continues building out the test content. We want to ensure that the
    document reader properly splits at paragraph boundaries when possible, falling back to
    sentence splitting if a single paragraph exceeds the chunk size.

    Eighth paragraph adds even more content. The auto-reader should maintain state across
    segments, storing each response in memory and tracking which parts of the document
    have been processed.

    Ninth paragraph is here for good measure. The system should handle documents of any
    size, from small single-segment documents to large multi-segment ones with dozens
    or even hundreds of chunks.

    Tenth and final paragraph concludes our test document. When complete, the auto-reader
    should report statistics about how many segments were processed and whether any errors
    occurred during the reading process.
    """.strip()

    print("="*70)
    print("AUTO READER TEST")
    print("="*70)
    print(f"\nTest document: {len(sample_doc)} characters\n")

    # Create DocumentReader with small chunk size for testing
    doc_reader = DocumentReader(chunk_size=500)
    load_success = doc_reader.load_document(sample_doc, "test_document.txt", "test_doc_id")
    num_chunks = doc_reader.total_chunks

    print(f"[OK] DocumentReader loaded successfully: {num_chunks} chunks")

    # Verify chunks were created
    print("\nChunk breakdown:")
    for i in range(num_chunks):
        chunk = doc_reader.get_current_chunk()
        print(f"  Chunk {chunk['position']}/{chunk['total']}: {len(chunk['text'])} chars")
        if i < num_chunks - 1:
            doc_reader.advance()

    # Reset to beginning
    doc_reader.jump_to(0)

    print("\n" + "="*70)
    print("TESTING AUTO READER")
    print("="*70)

    # Create mock LLM response function
    response_count = [0]  # Use list for mutable counter

    def mock_llm_response(prompt, agent_state):
        """Mock LLM that returns canned responses."""
        response_count[0] += 1
        segment_num = response_count[0]
        return f"Mock response #{segment_num}: This is Kay's simulated reaction to segment {segment_num}."

    # Create mock display function
    messages = []

    def mock_display(role, message):
        """Capture messages instead of displaying."""
        messages.append({
            'role': role,
            'message': message
        })
        print(f"\n[{role.upper()}] {message[:100]}{'...' if len(message) > 100 else ''}")

    # Create AutoReader instance
    auto_reader = AutoReader(
        get_llm_response_func=mock_llm_response,
        add_message_func=mock_display,
        memory_engine=None  # No memory engine for this test
    )

    print("\n[OK] AutoReader initialized")
    print(f"[OK] Starting synchronous read of {num_chunks} segments...\n")

    # Run auto-reader synchronously
    result = auto_reader.read_document_sync(
        doc_reader=doc_reader,
        doc_name="test_document.txt",
        agent_state=None,  # No agent state for this test
        start_segment=1
    )

    # Report results
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"\n[OK] Segments read: {result['segments_read']}/{num_chunks}")
    print(f"[OK] Responses generated: {len(result['responses'])}")
    print(f"[OK] Messages captured: {len(messages)}")
    print(f"[OK] Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"  - {error}")

    # Verify all segments were processed
    print("\nResponse breakdown:")
    for i, resp_data in enumerate(result['responses'], 1):
        print(f"  Segment {resp_data['segment']}: {len(resp_data['response'])} chars")

    # Summary
    print("\n" + "="*70)
    success = (
        result['segments_read'] == num_chunks and
        len(result['errors']) == 0 and
        len(result['responses']) == num_chunks
    )

    if success:
        print("[PASS] TEST PASSED - Auto-reader successfully processed all segments")
    else:
        print("[FAIL] TEST FAILED - See errors above")

    print("="*70)

    return success


if __name__ == "__main__":
    try:
        success = test_auto_reader()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[CRASH] TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
