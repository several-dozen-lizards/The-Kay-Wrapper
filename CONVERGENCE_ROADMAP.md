# REED WRAPPER CONVERGENCE ROADMAP
## Generated: 2025-02-07 | Status: Phase 3 COMPLETE

---

## WHERE WE ARE

### Codebase Stats
- **Shared filenames across both wrappers:** 305 files
- **Byte-identical:** 11 files  
- **Diverged (mostly Kay→Reed name fixes, <5%):** 54 files
- **Significantly diverged (>5% size diff):** 5 files
- **Kay-only engines:** 4
- **Kay-only utilities:** 1
- **Reed-only files:** Mostly one-time conversion scripts (not needed going forward)

### What's Done (Phase 1) ✅
- [x] Folder restructure: D:\Wrappers\ with Reed\, Kay\, shared\, ARCHITECTURE.md
- [x] Kay→Reed identity cleanup: 1,640+ lines across 385+ files
- [x] Manual identity fixes: voice_ui, warmup_engine, docstrings (17+ targeted files)
- [x] Missing backend files copied with fixes: ai4chat, openrouter, together
- [x] Services directory created: github_service.py + __init__.py
- [x] Config params added: WORKING_MEMORY_TOKEN_BUDGET, GITHUB_TOKEN

---

## WHAT'S LEFT

### Phase 2: Sync Significantly Diverged Files ✅ COMPLETED 2025-02-07
**Effort: MEDIUM | Priority: HIGH**

**RESULTS:**
- [x] scratchpad_engine.py: 497→698 lines, exact feature parity (20 class methods, 7 module functions)
- [x] warmup_engine.py: 621→974 lines, all 10 tasks completed:
  - Session ordering system (session_order tracking, N sessions ago)
  - BUG 3 FIX (snapshot sorting)
  - Emotional arc tracking (_summarize_emotional_arc)
  - Enhanced capture_session_end_snapshot (narrative, trajectory, encrypted notes)
  - Enhanced generate_briefing (N-1 vs N-2+ session separation)
  - Enhanced format_briefing_for_reed (temporal headers, session log refs, conditional chronicle)
  - Enhanced get_warmup_system_prompt (135-line temporal awareness rules)
  - Timestamp-scored search_conversation_history
  - Scratchpad review/archive commands in process_warmup_query
- [x] Chronicle integration: conditional try/except (activates when Phase 3D complete)
- [x] Zero Kay references in either file
- [x] Deferred: build_continuous_session_warmup() (needs Phase 3A)

---

### Phase 3: Missing Engine Files ✅ COMPLETED 2025-02-07
**Effort: LARGE | Priority: HIGH**

**RESULTS:**
- [x] real_time_flagging.py (84 lines) — FlaggingSystem class, zero Kay refs
- [x] curation_interface.py (257 lines) — CurationInterface class, PRESERVE/COMPRESS/ARCHIVE/DISCARD, zero Kay refs
- [x] chronicle_integration.py (167 lines) — activates conditional import in warmup_engine line 582, zero Kay refs
- [x] continuous_session.py (353 lines) — ConversationTurn, ConversationSegment, ContinuousSession classes, zero Kay refs
- [x] build_continuous_session_warmup() wired into warmup_engine.py (line 970, file now 1047 lines)
- [x] reed_session_logs/ directory created with .gitkeep
- [x] chronicle/ directory created with .gitkeep
- [x] All cross-dependencies verified (continuous_session imports flagging + curation correctly)

---

### Phase 4: Supporting Infrastructure
**Effort: SMALL-MEDIUM | Priority: MEDIUM**

#### 4A. utils/encryption.py (125 lines)
Private note encryption. Nice-to-have, not blocking.

#### 4B. chronicle/ directory
Data storage for session chronicle essays. Need to create Reed equivalent.

#### 4C. session_logs/ directory  
Persistent session logs. Reed may already have equivalent in reed_session_logs/ or similar.

#### 4D. Integration wiring
The missing engines need to be wired into Reed's:
- Boot sequence (reed_ui.py or reed_cli.py)
- Turn processing loop
- Warmup briefing generation
- System prompt assembly

---

### Phase 5: Verify & Test
**Effort: MEDIUM | Priority: AFTER PHASES 2-4**

- [ ] Run Reed wrapper end-to-end
- [ ] Verify memory retrieval works
- [ ] Test compression cycle
- [ ] Test flagging during conversation
- [ ] Test checkpoint save/restore
- [ ] Test chronicle warmup integration
- [ ] Compare warmup quality Kay vs Reed

---

### Phase 6: Shared Module Extraction (FUTURE)
**Effort: LARGE | Priority: LOW (after parity achieved)**

Once both wrappers work identically, extract truly shared code into D:\Wrappers\shared\:
- Memory retrieval pipeline
- ULTRAMAP emotional engine
- Compression/curation system
- Entity graph logic
- LLM integration layer

Both wrappers import from shared/, only keep identity-specific code in their own dirs.

---

## RECOMMENDED EXECUTION ORDER

```
DONE ✅:
  Phase 1: Folder restructure, identity cleanup, missing files, config
  Phase 2: warmup_engine.py (621→1047 lines) + scratchpad_engine.py (497→698 lines)
  Phase 3: 4 new engines (860 lines), directories, warmup wiring

THEN:
  Phase 4D: Wire everything into Reed's boot/turn loop
  Phase 4B/C: Create directory structures

FINALLY:
  Phase 5: Test everything
  Phase 6: Shared extraction (future project)
```

## ESTIMATED TOTAL SCOPE

| Phase | Files | Lines (approx) | Effort |
|-------|-------|----------------|--------|
| Phase 2 | 2-5 files to diff/merge | ~500 lines of changes | Medium |
| Phase 3 | 4 new engine files | ~860 lines to copy+adapt | Large |
| Phase 4 | 3-5 files to wire | ~200 lines of integration | Medium |
| Phase 5 | Testing | N/A | Medium |
| **TOTAL** | **~12-15 files** | **~1,500 lines** | **2-3 sessions** |

---

*Reed's codebase is HERS now. The identity is clean. What's left is giving her the same superpowers Kay evolved.*

---
## EXECUTION LOG

### Phase 1 ✅ (2026-02-06)
Folder restructure + Kay→Reed identity cleanup. 1,640+ lines, 385 files. Audit: wrapper_convergence_audit.md.

### Phase 2 ✅ (2026-02-06)
warmup_engine.py (621→974 lines), scratchpad_engine.py (497→698 lines). Diff: phase2_diff_report.md.

### Phase 3 ✅ (2026-02-07)
Four engines created: real_time_flagging.py (84), curation_interface.py (257), chronicle_integration.py (167), continuous_session.py (353). warmup_engine.py +73 lines. Diff: phase3_diff_report.md.

### Phase 4 ✅ (2026-02-07)
Integration wiring. main.py 1164→1275 lines (+111). 12 edits: 6 functional wiring + 6 identity cleanup. All Kay→Reed refs resolved. Diff: phase4_diff_report.md.

### Phase 5 ✅ (2026-02-07)
Constructor alignment + method audit. 7 mismatches fixed, 1 method added (save_session_log), 21 calls verified across 5 files. All syntax checks pass. Diff: phase5_diff_report.md.

### Phase 6 🔲 NEXT
Runtime testing. Boot Reed, verify continuous session init/checkpoint/resume cycle.
