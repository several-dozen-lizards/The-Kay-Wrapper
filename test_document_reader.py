"""
Test script for DocumentReader functionality.
Tests chunking, navigation, and state persistence.
"""

from engines.document_reader import DocumentReader


def test_document_reader():
    """Test basic DocumentReader functionality."""
    print("=" * 60)
    print("Testing DocumentReader")
    print("=" * 60)

    # Create sample large document
    sample_text = """This is a test document for the DocumentReader system.

Paragraph 1: This is the first paragraph. It contains some text that will be part of the first chunk.

Paragraph 2: This is the second paragraph. It contains more text.

Paragraph 3: This is the third paragraph with additional content.

Paragraph 4: Here's even more content to make the document longer.

Paragraph 5: And we continue with more paragraphs.

Paragraph 6: This paragraph adds more length to the document.

Paragraph 7: Another paragraph with some interesting content.

Paragraph 8: More text to simulate a real document.

Paragraph 9: We're getting close to the end now.

Paragraph 10: This is the final paragraph of our test document. It wraps up everything nicely."""

    # Repeat to make it larger
    large_text = sample_text * 100  # ~40k chars

    print(f"\nTest document size: {len(large_text):,} characters\n")

    # Initialize DocumentReader with small chunk size for testing
    reader = DocumentReader(chunk_size=5000)

    # Test 1: Load document
    print("Test 1: Loading document...")
    success = reader.load_document(large_text, "test_document.txt", "test_doc_001")
    print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
    print(f"  Total chunks: {reader.total_chunks}")
    print()

    # Test 2: Get current chunk (should be chunk 1)
    print("Test 2: Getting current chunk...")
    chunk = reader.get_current_chunk()
    if chunk:
        print(f"  Position: {chunk['position']}/{chunk['total']}")
        print(f"  Progress: {chunk['progress_percent']}%")
        print(f"  Chunk size: {len(chunk['text'])} chars")
        print(f"  Preview: {chunk['text'][:100]}...")
    print()

    # Test 3: Advance to next chunk
    print("Test 3: Advancing to next chunk...")
    success = reader.advance()
    chunk = reader.get_current_chunk()
    if chunk:
        print(f"  New position: {chunk['position']}/{chunk['total']}")
    print()

    # Test 4: Jump to specific chunk
    print("Test 4: Jumping to section 5...")
    success = reader.jump_to(4)  # 0-indexed, so 4 = section 5
    chunk = reader.get_current_chunk()
    if chunk:
        print(f"  New position: {chunk['position']}/{chunk['total']}")
    print()

    # Test 5: Go back
    print("Test 5: Going to previous section...")
    success = reader.previous()
    chunk = reader.get_current_chunk()
    if chunk:
        print(f"  New position: {chunk['position']}/{chunk['total']}")
    print()

    # Test 6: Restart document
    print("Test 6: Restarting document...")
    reader.jump_to(0)
    chunk = reader.get_current_chunk()
    if chunk:
        print(f"  Position after restart: {chunk['position']}/{chunk['total']}")
    print()

    # Test 7: State persistence
    print("Test 7: Testing state persistence...")
    reader.jump_to(7)  # Jump to section 8
    state = reader.get_state_for_persistence()
    print(f"  Saved state: {state}")

    # Create new reader and restore state
    reader2 = DocumentReader(chunk_size=5000)
    success = reader2.restore_state(state, large_text)
    if success:
        chunk = reader2.get_current_chunk()
        print(f"  Restored position: {chunk['position']}/{chunk['total']}")
    print()

    # Test 8: Navigation at boundaries
    print("Test 8: Testing boundary conditions...")

    # Try to go before beginning
    reader.jump_to(0)
    can_go_back = reader.previous()
    print(f"  Can go back from start: {can_go_back}")

    # Try to go past end
    reader.jump_to(reader.total_chunks - 1)
    can_advance = reader.advance()
    print(f"  Can advance from end: {can_advance}")
    print()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_document_reader()
