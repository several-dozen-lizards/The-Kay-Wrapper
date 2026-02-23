"""
LLM-Based Document Retrieval

Contextually-aware approach: Let the LLM decide which documents are relevant
using rich contextual information about recent imports, implicit references,
and request types.

The LLM sees:
- List of available documents (filename + preview)
- Recently imported documents (time-based, last 10 minutes)
- Implicit reference indicators ("this", "that", etc.)
- Request type (reading, analysis, navigation)
- User query
- Current emotional state (optional context)

The LLM selects which documents to load, with context-aware rules that
default to inclusion when uncertain.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import anthropic

# Import text sanitizer to prevent unicode encoding errors
try:
    from utils.text_sanitizer import sanitize_unicode
except ImportError:
    # Fallback if utils not available
    import re
    def sanitize_unicode(text):
        if not text or not isinstance(text, str):
            return text
        return re.sub(r'[\ud800-\udfff]', '', text)


def get_all_documents() -> List[Dict]:
    """
    Get list of all uploaded documents with metadata.

    Returns:
        List of dicts with: doc_id, filename, preview, upload_date
    """
    # Use absolute path based on this file's location to avoid working directory issues
    project_root = Path(__file__).parent.parent
    documents_path = project_root / "memory" / "documents.json"

    print(f"[LLM RETRIEVAL] Looking for documents at: {documents_path}")
    print(f"[LLM RETRIEVAL] File exists: {documents_path.exists()}")

    if not documents_path.exists():
        print(f"[LLM RETRIEVAL] WARNING: documents.json not found at {documents_path}")
        return []

    # Load JSON with error handling
    try:
        with open(documents_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

            # Handle empty file
            if not content:
                print("[LLM RETRIEVAL] Warning: documents.json is empty")
                return []

            docs_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[LLM RETRIEVAL] Error: documents.json is corrupted: {e}")
        return []
    except Exception as e:
        print(f"[LLM RETRIEVAL] Error reading documents.json: {e}")
        return []

    # Handle both list and dict formats
    if isinstance(docs_data, list):
        # List format: [{filename: "...", full_text: "..."}, ...]
        print(f"[LLM RETRIEVAL] Documents in list format, converting to dict")
        docs_dict = {}
        for i, doc in enumerate(docs_data):
            if not isinstance(doc, dict):
                continue

            # Use existing doc_id or memory_id, or generate from filename
            doc_id = (doc.get('doc_id') or
                     doc.get('memory_id') or
                     doc.get('filename', f'doc_{i}'))
            docs_dict[doc_id] = doc

        docs_data = docs_dict

    elif not isinstance(docs_data, dict):
        print(f"[LLM RETRIEVAL] Error: documents.json has unexpected format (type: {type(docs_data)})")
        return []

    # Build document list
    document_list = []
    for doc_id, doc in docs_data.items():
        if not isinstance(doc, dict):
            print(f"[LLM RETRIEVAL] Warning: Skipping malformed document entry: {doc_id}")
            continue

        # Get preview (first 200 chars of full text)
        full_text = doc.get('full_text', '')
        preview = full_text[:200] + "..." if len(full_text) > 200 else full_text

        document_list.append({
            'doc_id': doc_id,
            'filename': doc.get('filename', 'unknown'),
            'preview': preview,
            'upload_date': doc.get('import_date', 'unknown')  # Fixed: was 'upload_timestamp'
        })

    return document_list


def _build_document_context(documents: List[Dict], user_query: str) -> Dict[str, Any]:
    """
    Build contextual information about documents to help selection LLM.

    Args:
        documents: List of all available documents
        user_query: User's query/message

    Returns:
        Dict with contextual signals:
        - recently_imported: List of doc_ids imported in last 10 minutes
        - current_session: List of doc_ids from last 24 hours
        - historical: List of doc_ids older than 24 hours
        - has_implicit_reference: Boolean, query has "this", "that", etc.
        - has_explicit_mention: Boolean, query mentions specific filename
        - request_type: "reading" | "analysis" | "navigation" | "general"
    """
    context = {
        'recently_imported': [],
        'current_session': [],
        'historical': [],
        'has_implicit_reference': False,
        'has_explicit_mention': False,
        'request_type': 'general'
    }

    # 1. Categorize documents by age
    now = datetime.now()
    recent_threshold = now - timedelta(minutes=10)
    session_threshold = now - timedelta(hours=24)

    for doc in documents:
        upload_date_str = doc.get('upload_date', '')
        doc_id = doc['doc_id']

        if upload_date_str and upload_date_str != 'unknown':
            try:
                # Parse timestamp (assumes ISO format)
                upload_time = datetime.fromisoformat(upload_date_str)

                if upload_time > recent_threshold:
                    context['recently_imported'].append(doc_id)
                    context['current_session'].append(doc_id)
                elif upload_time > session_threshold:
                    context['current_session'].append(doc_id)
                else:
                    # Older than 24 hours = historical
                    context['historical'].append(doc_id)
            except (ValueError, TypeError):
                # If timestamp parsing fails, treat as historical
                context['historical'].append(doc_id)
        else:
            # No timestamp = treat as historical
            context['historical'].append(doc_id)

    # 2. Check for explicit filename mentions
    query_lower = user_query.lower()
    for doc in documents:
        filename_lower = doc['filename'].lower()
        # Check if filename (without extension) is mentioned
        filename_base = filename_lower.rsplit('.', 1)[0]
        if filename_base in query_lower or filename_lower in query_lower:
            context['has_explicit_mention'] = True
            break

    # 3. Detect implicit references
    implicit_indicators = [
        'this', 'that', 'these', 'those',
        'the document', 'the file', 'the text',
        'it says', 'it mentions', 'beginning scene',
        'continue reading', 'keep reading', 'next part'
    ]

    for indicator in implicit_indicators:
        if indicator in query_lower:
            context['has_implicit_reference'] = True
            break

    # 4. Categorize request type (check more specific patterns first)
    if any(word in query_lower for word in ['analyze', 'what do you think', 'opinion', 'look past']):
        context['request_type'] = 'analysis'
    elif any(word in query_lower for word in ['where', 'find', 'locate', 'section about', 'part about', 'what happens']):
        context['request_type'] = 'navigation'
    elif any(word in query_lower for word in ['read', 'continue', 'next', 'beginning', 'section', 'chapter']):
        context['request_type'] = 'reading'
    elif 'tell me about' in query_lower:
        # "Tell me about" can be analysis if document context exists
        context['request_type'] = 'analysis'

    return context


def classify_document_intent(user_input: str, available_documents: List[Dict], reading_session_active: bool = False) -> Dict[str, Any]:
    """
    Use LLM to determine user's actual intent regarding documents.

    This replaces trigger-based detection with intelligent classification to prevent
    aggressive auto-loading when user mentions documents casually.

    Args:
        user_input: User's message
        available_documents: List of available documents with metadata
        reading_session_active: Whether user is currently in a reading session

    Returns:
        Dict with:
            - intent: 'read_document' | 'reference_available' | 'discuss_generally' | 'none'
            - specific_document: filename or None
            - confidence: 0.0-1.0
            - reasoning: brief explanation
    """
    # Fast path: continuation of active reading session
    if reading_session_active and any(phrase in user_input.lower() for phrase in ['continue', 'next', 'more', 'keep reading']):
        return {
            'intent': 'read_document',
            'specific_document': None,  # Use current session document
            'confidence': 1.0,
            'reasoning': 'Continuation of active reading session'
        }

    # Build document list for context
    doc_list = "\n".join([f"- {doc.get('filename', 'unknown')}" for doc in available_documents[:10]])  # Limit to 10 for prompt brevity

    prompt = f"""User input: "{user_input}"

Available documents in memory:
{doc_list if doc_list else "None"}

Classify the user's intent regarding documents. Return ONLY a JSON object (no markdown):

{{
    "intent": "read_document" | "reference_available" | "discuss_generally" | "none",
    "specific_document": "filename.txt or null",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Intent definitions:
- read_document: User wants to actively read/review a specific document section by section
- reference_available: User wants documents available for reference but not full review (e.g., asking about specific content)
- discuss_generally: User is discussing documents/imports as a topic, not requesting specific docs
- none: No document-related intent

Examples:
"read the Medium old conversation" → {{"intent": "read_document", "specific_document": "Medium old - talking to zero.txt", "confidence": 0.95}}
"we're working on document processing" → {{"intent": "discuss_generally", "specific_document": null, "confidence": 0.9}}
"continue reading" → {{"intent": "read_document", "specific_document": null, "confidence": 1.0}}
"what did that conversation with Zero say about X?" → {{"intent": "reference_available", "specific_document": "Medium old - talking to zero.txt", "confidence": 0.85}}
"Hey how are you?" → {{"intent": "none", "specific_document": null, "confidence": 1.0}}
"tell me about those documents" → {{"intent": "discuss_generally", "specific_document": null, "confidence": 0.9}}
"""

    try:
        # Import here to avoid circular dependency
        from integrations.llm_integration import get_client_for_model
        
        # Get model from environment or use default
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        
        # Get correct client for this model
        try:
            active_client, provider_type = get_client_for_model(model)
        except ValueError as e:
            print(f"[INTENT CLASSIFIER ERROR] Client routing failed: {e}")
            return {
                'intent': 'none',
                'specific_document': None,
                'confidence': 0.0,
                'reasoning': str(e)
            }

        # Sanitize prompt to prevent unicode encoding errors
        prompt = sanitize_unicode(prompt)

        # Quick LLM call with cheaper model and low temperature
        if provider_type == 'openai':
            # OpenAI format
            response = active_client.chat.completions.create(
                model=model,
                max_tokens=200,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.choices[0].message.content.strip()
        else:
            # Anthropic format
            response = active_client.messages.create(
                model=model,
                max_tokens=200,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text.strip()

        # Strip markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('\n', 1)[1]
            response_text = response_text.rsplit('\n```', 1)[0]

        intent_data = json.loads(response_text)

        # Validate response structure
        required_keys = ['intent', 'specific_document', 'confidence']
        if not all(k in intent_data for k in required_keys):
            raise ValueError("Missing required keys in response")

        print(f"[INTENT CLASSIFIER] {intent_data['intent']} (confidence: {intent_data['confidence']:.2f}) - {intent_data.get('reasoning', 'No reasoning')}")

        return intent_data

    except json.JSONDecodeError as e:
        print(f"[INTENT CLASSIFIER ERROR] JSON parsing failed: {e}")
        print(f"[INTENT CLASSIFIER ERROR] Raw response: {response_text if 'response_text' in locals() else 'N/A'}")
        return {
            'intent': 'none',
            'specific_document': None,
            'confidence': 0.0,
            'reasoning': f'JSON parsing failed: {e}'
        }
    except Exception as e:
        print(f"[INTENT CLASSIFIER ERROR] {e}")
        import traceback
        traceback.print_exc()
        return {
            'intent': 'none',
            'specific_document': None,
            'confidence': 0.0,
            'reasoning': f'Classification failed: {e}'
        }


def select_relevant_documents(
    query: str,
    emotional_state: Optional[str] = None,
    max_docs: int = 3
) -> List[str]:
    """
    Use LLM to select which documents are relevant to the query.

    Contextually-aware approach that considers:
    - Recently imported documents (time-based)
    - Implicit references in the query
    - Request type (reading, analysis, navigation)

    Defaults to INCLUSION when uncertain.

    Args:
        query: User's query/message
        emotional_state: Optional emotional context (e.g., "curious (0.7)")
        max_docs: Maximum number of documents to select

    Returns:
        List of doc_ids that are relevant
    """
    # Get all available documents
    all_docs = get_all_documents()

    if not all_docs:
        print("[LLM RETRIEVAL] No documents available")
        return []

    print(f"[LLM RETRIEVAL] Checking {len(all_docs)} documents for relevance")

    # Build contextual information
    context = _build_document_context(all_docs, query)

    # Debug logging
    print(f"[LLM RETRIEVAL] Context: recently_imported={len(context['recently_imported'])}, "
          f"current_session={len(context['current_session'])}, "
          f"historical={len(context['historical'])}, "
          f"implicit_ref={context['has_implicit_reference']}, "
          f"explicit_mention={context['has_explicit_mention']}, "
          f"request_type={context['request_type']}")

    # CRITICAL FIX: Filter out historical documents unless explicitly mentioned
    # This prevents old session dumps from poisoning current conversations
    # EXCEPTION: Include all when user asks about documents in general

    # Detect "meta" queries about documents (user asking what documents exist)
    query_lower = query.lower()
    meta_document_queries = [
        'what documents', 'which documents', 'list documents', 'show documents',
        'documents do you have', 'documents can you see', 'documents have you read',
        'what have you read', 'what did i share', 'what did i give you',
        'what files', 'which files', 'show me the files',
        'all documents', 'all the documents', 'every document',
        'how many documents', 'count documents', 'document list',
        'what have i imported', 'what did we import', 'imported documents',
        # Questions about accessing/viewing document contents
        'access the contents', 'see the contents', 'view the contents',
        'access any of them', 'read any of them', 'see any of them',
        'can you access', 'can you see', 'can you read',
        'able to access', 'able to see', 'able to read',
        'what can you access', 'what can you see', 'what can you read'
    ]
    is_meta_document_query = any(phrase in query_lower for phrase in meta_document_queries)

    if is_meta_document_query:
        print(f"[DOC FILTER] Meta document query detected - returning ALL {len(all_docs)} documents")
        # For meta queries, return ALL doc IDs immediately without LLM selection
        all_doc_ids = [doc['doc_id'] for doc in all_docs]
        for doc in all_docs:
            print(f"[LLM RETRIEVAL] Including: {doc['filename']} (doc_id: {doc['doc_id']})")
        return all_doc_ids  # Return ALL, ignore max_docs limit for meta queries
    else:
        filtered_docs = []
        for doc in all_docs:
            doc_id = doc['doc_id']

            # Always include recently imported (< 10 minutes old)
            if doc_id in context['recently_imported']:
                filtered_docs.append(doc)
                print(f"[DOC FILTER] Including recently imported: {doc['filename']}")

            # Always include current session documents (< 24 hours old)
            elif doc_id in context['current_session']:
                filtered_docs.append(doc)

            # Only include historical documents if explicitly mentioned by filename
            elif doc_id in context['historical']:
                if context['has_explicit_mention']:
                    # Check if THIS specific document is mentioned
                    filename_lower = doc['filename'].lower()
                    filename_base = filename_lower.rsplit('.', 1)[0]
                    if filename_base in query_lower or filename_lower in query_lower:
                        filtered_docs.append(doc)
                        print(f"[DOC FILTER] Including historical doc (explicitly mentioned): {doc['filename']}")
                    else:
                        print(f"[DOC FILTER] Skipping historical doc (not explicitly mentioned): {doc['filename']}")
                else:
                    print(f"[DOC FILTER] Skipping historical doc (no explicit mention): {doc['filename']}")

    if not filtered_docs:
        print("[LLM RETRIEVAL] No current/relevant documents after filtering")
        return []

    print(f"[LLM RETRIEVAL] After filtering: {len(filtered_docs)}/{len(all_docs)} documents eligible")

    # Use filtered docs for selection
    all_docs = filtered_docs

    # Build prompt listing all documents with context indicators
    doc_list_text = ""
    for i, doc in enumerate(all_docs, start=1):
        doc_list_text += f"{i}. {doc['filename']}"

        # Mark recently imported
        if doc['doc_id'] in context['recently_imported']:
            doc_list_text += " [RECENTLY IMPORTED]"

        doc_list_text += f"\n   Preview: {doc['preview'][:100]}...\n\n"

    # Build context-aware LLM prompt
    if is_meta_document_query:
        prompt = f"""You are helping Kay list ALL available documents.

The user is asking about what documents Kay has access to. This is a meta-query about documents themselves.

All available documents:
{doc_list_text}

User query: "{query}"

For meta-queries like "what documents do you have?", you should return ALL document numbers
so Kay can tell the user about all available documents.
"""
    else:
        prompt = f"""You are helping Kay find relevant documents to answer a query.

NOTE: Historical documents (>24 hours old) have been filtered out to prevent conversation poisoning.
Only current session documents are shown below.

Available documents (current session only):
{doc_list_text}

User query: "{query}"
"""

    if emotional_state:
        prompt += f"\nKay's current emotional state: {emotional_state}\n"

    # Add contextual selection rules
    prompt += f"""
Context-Aware Selection Rules:

"""

    if context['recently_imported']:
        prompt += f"- {len(context['recently_imported'])} document(s) were recently imported (last 10 minutes)\n"
        prompt += f"- For recently imported documents, DEFAULT TO INCLUSION unless clearly irrelevant\n"

    if context['has_implicit_reference']:
        prompt += f"- Query contains implicit reference (\"this\", \"that\", \"the document\", etc.)\n"
        prompt += f"- User is likely referring to recently imported documents\n"

    if context['request_type'] == 'reading':
        prompt += f"- Request type: READING (user wants to read/continue through content)\n"
        prompt += f"- Include documents if they contain narrative content\n"
    elif context['request_type'] == 'analysis':
        prompt += f"- Request type: ANALYSIS (user wants Kay's thoughts/opinions)\n"
        prompt += f"- Include documents that Kay should analyze\n"
    elif context['request_type'] == 'navigation':
        prompt += f"- Request type: NAVIGATION (user is looking for specific content)\n"
        prompt += f"- Include documents that might contain the target content\n"

    prompt += f"""
Which documents should Kay load to respond to this query?

Selection Guidelines:
- These are CURRENT SESSION documents only - historical documents already filtered out
- For casual conversation ("Hey Kay, how are you?"), return NONE unless documents are clearly relevant
- For recently imported docs, DEFAULT TO INCLUSION if there's any connection to the query
- For implicit references + recent imports, ALWAYS include the recent document
- Only return NONE if query is clearly unrelated to all documents (e.g., "What's the weather?")
- Return up to {max_docs} document numbers

Response Format:
- Return ONLY the numbers of relevant documents (e.g., "1,3,5")
- If NO documents are relevant, return "NONE"
- Do not include any other text

Relevant document numbers:"""

    # Call LLM
    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        # Sanitize prompt to prevent unicode encoding errors
        prompt = sanitize_unicode(prompt)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Fast model for selection
            max_tokens=100,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        print(f"[LLM RETRIEVAL] LLM response: '{response_text}'")

        # Parse response
        if response_text.upper() == "NONE":
            print("[LLM RETRIEVAL] Selection result: No relevant documents")
            return []

        # Extract numbers
        import re
        numbers = re.findall(r'\d+', response_text)
        selected_indices = [int(n) for n in numbers]

        # Convert indices to doc_ids
        selected_doc_ids = []
        for idx in selected_indices:
            if 1 <= idx <= len(all_docs):
                doc = all_docs[idx - 1]
                selected_doc_ids.append(doc['doc_id'])
                print(f"[LLM RETRIEVAL] ✓ Selected: {doc['filename']} (doc_id: {doc['doc_id']})")

        return selected_doc_ids[:max_docs]

    except Exception as e:
        print(f"[LLM RETRIEVAL] Error calling LLM: {e}")
        # Fallback: If context suggests inclusion, return recently imported docs
        if context['recently_imported'] and (context['has_implicit_reference'] or context['request_type'] in ['reading', 'analysis']):
            print(f"[LLM RETRIEVAL] Fallback: Returning {len(context['recently_imported'])} recently imported document(s)")
            return context['recently_imported'][:max_docs]
        return []


def load_full_documents(doc_ids: List[str]) -> List[Dict]:
    """
    Load full text of selected documents.

    No chunking, no truncation, no scoring.
    Just load the full document text.

    Args:
        doc_ids: List of document IDs to load

    Returns:
        List of dicts with: doc_id, filename, full_text
    """
    documents_path = Path("memory/documents.json")

    if not documents_path.exists():
        return []

    # Load JSON with error handling
    try:
        with open(documents_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

            # Handle empty file
            if not content:
                print("[LLM RETRIEVAL] Warning: documents.json is empty")
                return []

            docs_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[LLM RETRIEVAL] Error: documents.json is corrupted: {e}")
        return []
    except Exception as e:
        print(f"[LLM RETRIEVAL] Error reading documents.json: {e}")
        return []

    # Handle both list and dict formats
    if isinstance(docs_data, list):
        # List format: [{filename: "...", full_text: "..."}, ...]
        print(f"[LLM RETRIEVAL] Documents in list format, converting to dict")
        docs_dict = {}
        for i, doc in enumerate(docs_data):
            if not isinstance(doc, dict):
                continue

            # Use existing doc_id or memory_id, or generate from filename
            doc_id = (doc.get('doc_id') or
                     doc.get('memory_id') or
                     doc.get('filename', f'doc_{i}'))
            docs_dict[doc_id] = doc

        docs_data = docs_dict

    elif not isinstance(docs_data, dict):
        print(f"[LLM RETRIEVAL] Error: documents.json has unexpected format (type: {type(docs_data)})")
        return []

    # Load requested documents
    loaded_docs = []
    for doc_id in doc_ids:
        if doc_id in docs_data:
            doc = docs_data[doc_id]

            if not isinstance(doc, dict):
                print(f"[LLM RETRIEVAL] Warning: Skipping malformed document: {doc_id}")
                continue

            loaded_docs.append({
                'doc_id': doc_id,
                'filename': doc.get('filename', 'unknown'),
                'full_text': doc.get('full_text', '')
            })
            print(f"[LLM RETRIEVAL] Loaded: {doc.get('filename')} ({len(doc.get('full_text', ''))} chars)")
        else:
            print(f"[LLM RETRIEVAL] Warning: Document not found: {doc_id}")

    return loaded_docs


def build_simple_context(
    query: str,
    selected_doc_ids: List[str],
    recent_conversation: List[Dict],
    emotional_state: str,
    core_identity: List[str]
) -> Dict:
    """
    Build simplified context for Reed's response.

    No complex retrieval, no scoring, no chunking.
    Just:
    - Full documents (if any)
    - Recent conversation turns
    - Emotional state
    - Core identity

    Args:
        query: Current user query
        selected_doc_ids: Document IDs selected by LLM
        recent_conversation: Recent conversation turns
        emotional_state: Current emotional state description
        core_identity: List of core identity facts

    Returns:
        Dict with all context ready for LLM prompt
    """
    # Load full documents
    documents = load_full_documents(selected_doc_ids)

    context = {
        'query': query,
        'documents': documents,
        'recent_conversation': recent_conversation,
        'emotional_state': emotional_state,
        'core_identity': core_identity,
        'document_count': len(documents),
        'conversation_turns': len(recent_conversation)
    }

    print(f"[LLM RETRIEVAL] Context built: {len(documents)} docs, {len(recent_conversation)} turns")

    return context


def format_context_for_prompt(context: Dict) -> str:
    """
    Format context into a simple prompt for Reed.

    No complex templates, just clear sections.

    Args:
        context: Context dict from build_simple_context()

    Returns:
        Formatted prompt string
    """
    sections = []

    # Emotional state
    if context['emotional_state']:
        sections.append(f"EMOTIONAL STATE: {context['emotional_state']}")

    # Core identity
    if context['core_identity']:
        identity_text = "\n".join(f"- {fact}" for fact in context['core_identity'])
        sections.append(f"CORE IDENTITY:\n{identity_text}")

    # Documents
    if context['documents']:
        docs_text = ""
        for doc in context['documents']:
            docs_text += f"\n--- {doc['filename']} ---\n"
            docs_text += doc['full_text']
            docs_text += "\n"
        sections.append(f"UPLOADED DOCUMENTS:{docs_text}")

    # Recent conversation
    if context['recent_conversation']:
        conv_text = ""
        for turn in context['recent_conversation'][-10:]:  # Last 10 turns
            speaker = turn.get('speaker', 'unknown')
            message = turn.get('message', '')
            conv_text += f"{speaker}: {message}\n"
        sections.append(f"RECENT CONVERSATION:\n{conv_text}")

    return "\n\n".join(sections)
