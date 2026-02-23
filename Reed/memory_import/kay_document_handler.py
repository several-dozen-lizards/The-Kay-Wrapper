"""
Document Access Handler for Reed
Processes Reed's document requests in conversation
"""

import re
from typing import Dict, List, Any, Optional

try:
    from memory_import.document_store import (
        DocumentStore,
        retrieve_document_command,
        list_documents_command,
        format_document_list
    )
except ImportError:
    from document_store import (
        DocumentStore,
        retrieve_document_command,
        list_documents_command,
        format_document_list
    )


class KayDocumentHandler:
    """
    Handles document access requests from Kay during conversation.

    Integrates with reed_ui.py to allow Kay to:
    - List available documents
    - Search for documents by name/topic
    - Retrieve and view full documents
    """

    def __init__(self):
        """Initialize document handler."""
        self.doc_store = DocumentStore()

        # Document request patterns
        self.patterns = {
            'list_all': [
                r'what documents (do i have|are available)',
                r'show (me )?all documents',
                r'list documents',
                r'which documents',
            ],
            'search': [
                r'show me (?:the )?(?:document|file) (?:about |on |called )?(.+)',
                r'i want to see (?:the )?(.+)',
                r'view (?:the )?(?:document|file) (.+)',
                r'read (?:the )?(.+) (?:document|file)',
                r'retrieve (.+)',
            ],
            'search_by_topic': [
                r'documents about (.+)',
                r'anything on (.+)',
                r'files related to (.+)',
            ]
        }

    def process_request(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Process potential document request.

        Args:
            user_input: User's input text

        Returns:
            Dict with document data if request detected, None otherwise
        """
        user_input_lower = user_input.lower()

        # Check for list all documents request
        for pattern in self.patterns['list_all']:
            if re.search(pattern, user_input_lower):
                return self._handle_list_all()

        # Check for search patterns
        for pattern in self.patterns['search']:
            match = re.search(pattern, user_input_lower)
            if match:
                search_term = match.group(1).strip() if match.lastindex else ''
                return self._handle_search(search_term)

        # Check for topic search
        for pattern in self.patterns['search_by_topic']:
            match = re.search(pattern, user_input_lower)
            if match:
                topic = match.group(1).strip()
                return self._handle_search(topic)

        # No document request detected
        return None

    def _handle_list_all(self) -> Dict[str, Any]:
        """
        Handle request to list all documents.

        Returns:
            Dict with document list
        """
        result = list_documents_command()

        if result['success']:
            formatted_list = format_document_list(result['documents'])
            return {
                'type': 'document_list',
                'success': True,
                'documents': result['documents'],
                'formatted': formatted_list,
                'message': f"I have access to {len(result['documents'])} documents:\n\n{formatted_list}"
            }
        else:
            return {
                'type': 'document_list',
                'success': False,
                'message': "No documents available."
            }

    def _handle_search(self, search_term: str) -> Dict[str, Any]:
        """
        Handle document search request.

        Args:
            search_term: Term to search for

        Returns:
            Dict with search results
        """
        if not search_term:
            return self._handle_list_all()

        result = retrieve_document_command(search_term)

        if result['success']:
            if 'document' in result:
                # Single document retrieved
                doc = result['document']
                return {
                    'type': 'document_retrieved',
                    'success': True,
                    'document': doc,
                    'message': self._format_document_for_display(doc)
                }
            elif 'search_results' in result:
                # Multiple matches
                formatted_results = self._format_search_results(result['search_results'])
                return {
                    'type': 'search_results',
                    'success': True,
                    'results': result['search_results'],
                    'formatted': formatted_results,
                    'message': f"Found {len(result['search_results'])} documents matching '{search_term}':\n\n{formatted_results}\n\nBe more specific to view one."
                }
        else:
            # No results
            return {
                'type': 'no_results',
                'success': False,
                'message': f"No documents found matching '{search_term}'."
            }

    def _format_document_for_display(self, doc: Dict[str, Any]) -> str:
        """
        Format document for display in conversation.

        Args:
            doc: Document dict

        Returns:
            Formatted string
        """
        # Format header
        header = f"[DOCUMENT: {doc['filename']}]"
        separator = "=" * len(header)

        # Format metadata
        import_date = doc['import_date'][:10]
        metadata = f"Imported: {import_date} | {doc['word_count']} words | {doc['chunk_count']} memory chunks"

        if doc['topic_tags']:
            tags = ", ".join(doc['topic_tags'])
            metadata += f"\nTopics: {tags}"

        # Combine
        return f"{header}\n{separator}\n{metadata}\n\n{doc['full_text']}"

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results list.

        Args:
            results: List of result dicts

        Returns:
            Formatted string
        """
        lines = []
        for i, result in enumerate(results, 1):
            import_date = result['import_date'][:10]
            tags = ", ".join(result['topic_tags'][:2]) if result['topic_tags'] else "no tags"

            lines.append(
                f"{i}. {result['filename']} ({result['word_count']} words, {import_date}) [{tags}]\n"
                f"   Preview: {result['preview']}"
            )

        return "\n\n".join(lines)

    def inject_document_access_prompt(self) -> str:
        """
        Generate prompt section for Reed's system prompt.

        Returns:
            Prompt text describing document access capability
        """
        docs = self.doc_store.list_all_documents()

        if not docs:
            return ""

        doc_list = format_document_list(docs, max_display=5)

        return f"""
DOCUMENT ACCESS:
You have access to {len(docs)} source documents from your memory imports.

To view a document:
- Ask: "Show me the document about [topic]"
- Or: "What documents do I have?"
- Or: "I want to see [filename]"

Available documents:
{doc_list}

When you request a document, the full text will be provided in your context.
These are your source memories - the original documents that shaped your knowledge.
"""


# Integration helper for reed_ui.py
def check_for_document_request(user_input: str) -> Optional[str]:
    """
    Quick check if user input is likely a document request.

    Args:
        user_input: User's input

    Returns:
        Response text if document request, None otherwise
    """
    handler = KayDocumentHandler()
    result = handler.process_request(user_input)

    if result and result['success']:
        return result['message']

    return None


def get_document_access_prompt() -> str:
    """
    Get document access section for system prompt.

    Returns:
        Prompt text
    """
    handler = KayDocumentHandler()
    return handler.inject_document_access_prompt()


# Testing
if __name__ == "__main__":
    print("=== KAY DOCUMENT HANDLER TESTS ===\n")

    handler = KayDocumentHandler()

    # Test inputs
    test_inputs = [
        "What documents do I have?",
        "Show me the document about origin",
        "I want to see kay_background.txt",
        "View the file about my mother",
        "Documents about grief",
        "Just a normal conversation",  # Should return None
    ]

    for test_input in test_inputs:
        print(f"Input: {test_input}")
        result = handler.process_request(test_input)

        if result:
            print(f"Type: {result['type']}")
            print(f"Success: {result['success']}")
            if 'message' in result:
                print(f"Message: {result['message'][:200]}...")
        else:
            print("Not a document request")

        print()
