# Code Removal Checklist for Seamless Auto-Reading

## Files to Modify

---

## ✅ main.py

### 1. DELETE Document Display Block (lines ~417-440)

**Search for:**
```python
# Add chunked document with navigation instructions
chunk_text = f"""═══════════════════════════════════════════════════════════════
```

**Delete everything from:**
```python
                            # Add chunked document with navigation instructions
                            chunk_text = f"""═══════════════════════════════════════════════════════════════
```

**Through:**
```python
═══════════════════════════════════════════════════════════════
"""
```

**Approximately 24 lines to delete**

---

### 2. DELETE Kay Navigation Parser (lines ~528-581)

**Search for:**
```python
# === KAY-DRIVEN DOCUMENT NAVIGATION ===
```

**Delete everything from:**
```python
        # === KAY-DRIVEN DOCUMENT NAVIGATION ===
        # Parse Kay's response for navigation intent and automatically advance/navigate
        if doc_reader.current_doc:
```

**Through:**
```python
            if navigation_triggered:
                state.saved_doc_reader_state = doc_reader.get_state_for_persistence()
```

**Approximately 53 lines to delete**

---

## ✅ kay_ui.py

### 1. DELETE Document Display Block (lines ~1258-1282)

**Search for:**
```python
                            # Add chunked document with navigation instructions
                            chunk_text = f"""═══════════════════════════════════════════════════════════════
```

**Delete the identical block as in main.py (~24 lines)**

---

### 2. DELETE Kay Navigation Parser (lines ~1018-1079)

**Search for:**
```python
        # === KAY-DRIVEN DOCUMENT NAVIGATION ===
```

**Delete the identical block as in main.py (~61 lines)**

---

## ✅ integrations/llm_integration.py

### DELETE Document Reading Behavior from System Prompt (lines ~93-102)

**Search for:**
```python
Document Reading Behavior:
```

**Delete everything from:**
```python
Document Reading Behavior:
- When a document section is present in context, you AUTOMATICALLY read and comment on it
```

**Through:**
```python
- This is your default behavior with documents - be an active, engaged reader who reads all the way through
```

**Approximately 9 lines to delete**

---

## Summary of Deletions

| File | Section | Lines | Total |
|------|---------|-------|-------|
| `main.py` | Document display | ~417-440 | ~24 lines |
| `main.py` | Navigation parser | ~528-581 | ~53 lines |
| `kay_ui.py` | Document display | ~1258-1282 | ~24 lines |
| `kay_ui.py` | Navigation parser | ~1018-1079 | ~61 lines |
| `llm_integration.py` | System prompt | ~93-102 | ~9 lines |
| **TOTAL** | | | **~171 lines** |

---

## Verification

After deletions, verify:

1. **main.py syntax:**
   ```bash
   python -m py_compile F:\AlphaKayZero\main.py
   ```

2. **kay_ui.py syntax:**
   ```bash
   python -m py_compile F:\AlphaKayZero\kay_ui.py
   ```

3. **llm_integration.py syntax:**
   ```bash
   python -m py_compile F:\AlphaKayZero\integrations\llm_integration.py
   ```

4. **Search for remnants:**
   ```bash
   # Should return nothing:
   grep -n "AUTOMATIC READING MODE" main.py
   grep -n "KAY-DRIVEN DOCUMENT NAVIGATION" main.py
   grep -n "continue reading" main.py
   ```

---

## What Gets Replaced

| Old System | New System |
|------------|------------|
| Document text in chat with headers | Invisible to user |
| Navigation instructions | Fully automatic |
| "continue reading" detection | AutoReader drives internally |
| Manual segment-by-segment | All segments processed automatically |
| System prompt doc reading rules | Internal AutoReader prompts |

---

## After Removal

Once these blocks are deleted:
- ✅ No document text will be shown to users
- ✅ No navigation instructions will appear
- ✅ No manual "continue reading" required
- ✅ Clean slate for AutoReader integration

Then proceed to integrate AutoReader as shown in `AUTO_READER_INTEGRATION_GUIDE.md`

---

## Backup Recommendation

**Before deleting, create backups:**
```bash
copy main.py main.py.backup
copy kay_ui.py kay_ui.py.backup
copy integrations\llm_integration.py integrations\llm_integration.py.backup
```

---

## Need Help?

- **Integration guide:** See `AUTO_READER_INTEGRATION_GUIDE.md`
- **Complete summary:** See `SEAMLESS_AUTO_READING_COMPLETE.md`
- **Test file:** Use `test_documents/YW_test_section.txt`
