# Disconnected Code Analysis - AlphaKayZero (D: Drive)

This document identifies files, code fragments, and functions that are **NOT connected** to the main application flow (main.py or kay_ui.py).

**Location**: D:\ChristinaStuff\alphakayzero

---

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| **Core/Connected** | ~70 files | Imported by main.py/kay_ui.py chain |
| **Test Files** | ~163 files | Test suite (standalone, expected) |
| **Utility/Maintenance Scripts** | ~25 files | Admin tools, migrations, diagnostics |
| **Already Deprecated** | ~55 files | Moved to deprecated/ folder |
| **K-0 Backup** | ~570 files | Complete backup in K-0/ |

---

## 1. CONNECTED FILES (Core System)

These files ARE imported and used by main.py, kay_ui.py, or their dependencies.

### Entry Points (3)
- `main.py` - Terminal interface
- `kay_ui.py` - GUI interface (CustomTKinter)
- `kay_cli.py` - CLI interface (alternative)

### Core Infrastructure (12)
| File | Purpose |
|------|---------|
| `agent_state.py` | Central state container |
| `protocol_engine.py` | ULTRAMAP CSV loader |
| `config.py` | Configuration (VERBOSE_DEBUG) |
| `context_filter.py` | Glyph filter system |
| `glyph_decoder.py` | Glyph decoder |
| `glyph_vocabulary.py` | Glyph vocabulary |
| `log_router.py` | Logging/dashboard router |
| `tab_system.py` | UI tab management |
| `tab_methods.py` | Tab method helpers |
| `terminal_dashboard.py` | Dashboard display |
| `document_manager.py` | Document management logic |
| `document_manager_ui.py` | Document management UI |

### Engines (35 modules in engines/)
| File | Purpose |
|------|---------|
| `emotion_engine.py` | ULTRAMAP rule provider |
| `emotion_extractor.py` | Self-report extraction |
| `emotional_patterns.py` | Behavioral emotion tracking |
| `emotional_self_report.py` | Self-report tracking |
| `memory_engine.py` | Core memory system |
| `memory_layers.py` | Working/Episodic/Semantic tiers |
| `memory_forest.py` | Hierarchical document trees |
| `memory_deletion.py` | Memory pruning & deletion |
| `memory_layer_rebalancing.py` | Memory tier management |
| `entity_graph.py` | Entity resolution & attributes |
| `vector_store.py` | RAG/ChromaDB database |
| `llm_retrieval.py` | LLM-based document selection |
| `social_engine.py` | Social event detection |
| `temporal_engine.py` | Time & aging management |
| `embodiment_engine.py` | Physical text manifestations |
| `reflection_engine.py` | Post-turn reflection |
| `context_manager.py` | Context building & history |
| `summarizer.py` | Conversation summarization |
| `motif_engine.py` | Entity frequency tracking |
| `momentum_engine.py` | Cognitive momentum calculation |
| `meta_awareness_engine.py` | Self-monitoring (repetition/confab) |
| `relationship_memory.py` | Relationship pattern tracking |
| `document_reader.py` | Chunked document navigation |
| `auto_reader.py` | Automatic document reading |
| `web_reader.py` | URL fetching & parsing |
| `conversation_monitor.py` | Spiral detection |
| `session_summary.py` | Session summary storage |
| `session_summary_generator.py` | Summary generation |
| `reading_session.py` | Document reading sessions |
| `time_awareness.py` | Time-aware processing |
| `warmup_engine.py` | Session warmup & moments |
| `gallery_manager.py` | Image gallery management |
| `user_profiles.py` | User profile management |
| `preference_tracker.py` | Preference consolidation |
| `identity_memory.py` | Identity memory system |

### Integrations (2)
| File | Purpose |
|------|---------|
| `integrations/llm_integration.py` | Anthropic Claude API |
| `integrations/sd_integration.py` | Stable Diffusion |

### Media System (4)
| File | Purpose |
|------|---------|
| `media_orchestrator.py` | Media experience management |
| `media_context_builder.py` | Media context injection |
| `media_watcher.py` | File system monitoring |
| `resonance_memory.py` | Media resonance tracking |

### Memory Import (17 modules in memory_import/)
All connected via `kay_reader.py`:
- `__init__.py`, `active_reader.py`, `auto_import.py`
- `document_parser.py`, `document_store.py`
- `emotional_importer.py`, `emotional_signature.py`
- `hybrid_import_manager.py`, `identity_classifier.py`
- `import_manager.py`, `kay_document_handler.py`, `kay_reader.py`
- `memory_extractor.py`, `memory_forest.py`, `memory_weights.py`
- `narrative_chunks.py`, `semantic_extractor.py`

### Memory Continuity (8 modules)
All in `memory_continuity/`:
- `__init__.py`, `entity_cleanup.py`, `example_usage.py`
- `guaranteed_context.py`, `layered_retrieval.py`
- `session_boundary.py`, `smart_import.py`, `thread_momentum.py`

### Session Browser (10 modules)
All in `session_browser/`:
- `__init__.py` (SessionBrowserIntegration)
- `session_browser_ui.py`, `session_loader.py`
- `session_manager.py`, `session_metadata.py`, `session_viewer.py`
- `kay_integration.py`, `convert_sessions.py`
- `demo_browser.py`, `diagnose_sessions.py`, `INTEGRATION_EXAMPLE.py`

### UI Integration (4)
| File | Purpose |
|------|---------|
| `voice_ui_integration.py` | Voice chat UI |
| `voice_handler.py` | Voice handling (used by voice_ui) |
| `voice_interface.py` | Voice interface (used by voice_ui) |
| `autonomous_ui_integration.py` | Autonomous processing (optional) |
| `curation_ui_integration.py` | Memory curation (optional) |
| `autonomous_ui.py` | Standalone autonomous UI |
| `curation_ui.py` | Standalone curation UI |

### Utilities (4 in utils/)
- `utils/__init__.py`
- `utils/performance.py` - Performance metrics
- `utils/text_sanitizer.py` - Text utilities
- `utils/paths.py` - Path utilities
- `utils/image_processing.py` - Image utilities

---

## 2. TEST FILES (163 files - Standalone by Design)

These are test/verification scripts that run independently.

### Memory System Tests (~25)
- `test_memory_*.py` - Memory functionality testing
- `test_layer_*.py` - Memory layer testing
- `test_entity_*.py` - Entity system testing
- `test_tiered_*.py`, `test_two_tier_*.py`, `test_three_tier.py`

### Document & Import Tests (~20)
- `test_document_*.py` - Document handling & import tests
- `test_import_*.py` - Memory import testing
- `test_rag_*.py` - RAG system testing
- `test_chunking_*.py` - Document chunking tests

### Emotion & Behavioral Tests (~15)
- `test_emotion*.py` - Emotion system testing
- `test_emotional_*.py` - Emotional patterns testing
- `test_self_report_*.py` - Self-report testing

### Integration Tests (~15)
- `test_*_integration.py` - System integration tests
- `test_relationship_*.py` - Relationship tracking
- `test_session_*.py` - Session management

### Feature-Specific Tests (~30)
- `test_contradiction_*.py` - Contradiction detection
- `test_forest_*.py` - Memory forest testing
- `test_semantic_*.py` - Semantic features
- `test_clustering_*.py` - Clustering algorithms

### Verification Scripts (~10)
- `verify_*.py` - Verification scripts

### Diagnostic Scripts (~10)
- `diagnose_*.py` - Diagnostic tools

---

## 3. UTILITY/MAINTENANCE SCRIPTS (~25 files)

These are run manually for maintenance, not part of normal operation.

### Data Migration Scripts
| File | Purpose |
|------|---------|
| `migrate_memories.py` | Format migration |
| `migrate_documents_format.py` | Document format migration |
| `migrate_corruption_markers.py` | Corruption marker migration |
| `migrate_to_versioned_facts.py` | Versioned fact migration |
| `scripts/migrate_identity_phase4.py` | Phase 4 identity migration |

### Cleanup Scripts
| File | Purpose |
|------|---------|
| `aggressive_wipe.py` | Nuclear memory wipe |
| `wipe_memory.py` | Simple memory wipe |
| `preview_wipe.py` | Preview wipe effects |
| `cleanup_memory.py` | Memory cleanup |
| `cleanup_memory_hybrid.py` | Hybrid cleanup |
| `cleanup_imported_bloat.py` | Import bloat cleanup |
| `cleanup_corrupted_import.py` | Corrupted import cleanup |
| `quick_cleanup_imported.py` | Quick cleanup |

### Repair/Fix Scripts
| File | Purpose |
|------|---------|
| `fix_imported_memory_fields.py` | Field repair |
| `fix_layer_rebalancing_volume_problem.py` | Volume fix |
| `reclassify_identity.py` | Identity reclassification |
| `scripts/audit_identity_facts.py` | Identity audit |

### Analysis/Diagnostic Scripts
| File | Purpose |
|------|---------|
| `analyze_tree_structure.py` | Tree analysis |
| `debug_memory_structure.py` | Memory structure debugging |
| `debug_saga_memory.py` | Entity debugging |
| `diagnose_system.py` | System diagnostics |
| `diagnose_memory_composition.py` | Memory composition |
| `diagnose_caching.py` | Caching diagnostics |
| `diagnose_document_system.py` | Document system diagnostics |
| `check_doc_ids.py` | Document ID validation |
| `check_import_ages.py` | Import age validation |
| `check_text_vs_fact.py` | Text vs fact comparison |
| `check_tree_update.py` | Tree update validation |

### Performance Scripts
| File | Purpose |
|------|---------|
| `benchmark_lazy_loading.py` | Performance benchmark |
| `profile_llm_latency.py` | LLM latency profiling |
| `build_memory_indexes.py` | Index building |
| `import_memories.py` | Batch memory import |
| `import_conversations.py` | Conversation import |

---

## 4. ALREADY DEPRECATED (55 files in deprecated/)

These files have been moved to `deprecated/` folder and are no longer used.

### deprecated/engines/ (~30 files)
- `emotion_engine_OLD.py`, `emotion_engine_SIMPLIFIED.py`
- `emotion_engine_BACKUP_PRESCRIPTIVE*.py`
- `document_reader_OLD.py`, `document_reader_simple.py`
- `memory_layer_rebalancing_BACKUP_*.py`
- `lazy_memory_engine.py`, `memory_engine_simple.py`
- `context_builder.py`, `session_memory.py`
- `semantic_knowledge.py`, `document_index.py`
- `memory_index.py`, `memory_debug_tracker.py`
- `inner_monologue.py`, `goal_retirement.py`
- `identity_extractor.py`, `corruption_detection.py`
- `autonomous_integration.py`, `autonomous_memory.py`
- `autonomous_processor.py`, `acoustic_analyzer.py`
- `environmental_sound_detector.py`, `voice_engine.py`
- `panns_classifier.py`, `memory_curation.py`
- `purge_reserve.py`, `smart_import_boost.py`
- `memory_simple.py`

### deprecated/integrations/ (~1 file)
- `llm_integration_simple.py`

### deprecated/root_level/ (~24 files)
- `main_simple.py`, `main_simplified.py`
- `OrnateKayUI.py`, `kay_ui_backup_grid.py`
- `temporal_memory.py`, `consolidation_engine.py`
- `consolidation_integration_example.py`
- `example_emotional_import.py`, `example_full_system.py`
- `duplicate_detector.py`, `purge_reserve_ui.py`
- `import_state_manager.py`, `integrate_emotional_self_report.py`
- `dashboard_logger.py`, `kay_voice.py`
- `autonomous_main.py`, `autonomous_analytics_ui.py`
- `apply_tab_system.py`, `apply_layer_rebalancing.py`
- `demo_entity_matching.py`, `Whispertest.py`
- `CoquiTTSsetup.py`, `setup_voice_chat.py`

---

## 5. K-0 BACKUP FOLDER

The `K-0/` folder is a **complete backup** of the codebase (~570 files), created without sensitive data:

**Excluded from backup:**
- `.env` files (API keys)
- `config.json`
- `memory/` folder (session memories)
- `saved_sessions/` folder
- `data/emotions/`, `data/profiles/`, `data/relationship/`, `data/trees/`
- `.claude/` settings
- `sessions/`, `themes/`, `test_data/`, `test_documents/`
- `memorybackup_*` folders

---

## 6. FILE COUNT SUMMARY

| Category | Count | Percentage |
|----------|-------|------------|
| Core/Connected | ~70 | 24% |
| Test files | ~163 | 55% |
| Utilities/Scripts | ~25 | 8% |
| Deprecated | ~55 | - |
| K-0 Backup | ~570 | - |

**Active codebase size**: ~295 Python files (excluding deprecated and K-0)
**Core system size**: ~70 files (what actually runs)

---

## 7. RECOMMENDATIONS

### High Priority - Already Done ✓
1. ✓ Deprecated files moved to `deprecated/` folder
2. ✓ K-0 backup created without sensitive data
3. ✓ Architecture documentation created

### Medium Priority - Consider
1. **Test organization**: Consider moving all test_*.py files to a `tests/` folder
2. **Utility organization**: Consider moving utility scripts to `scripts/` folder
3. **Documentation consolidation**: Many .md files could be consolidated

### Low Priority - Optional
1. **Remove verify_*.py** after confirming they're no longer needed
2. **Archive old sessions** in `sessions_backup_*` folders

---

## 8. DEPENDENCY GRAPH

```
Entry Points (main.py, kay_ui.py)
    │
    ├── Core State (agent_state.py, protocol_engine.py)
    │
    ├── Engines (35 modules)
    │   ├── Memory System (memory_engine, layers, forest, entity_graph, vector_store)
    │   ├── Emotion System (emotion_engine, extractor, patterns)
    │   ├── Cognitive (momentum, meta_awareness, conversation_monitor)
    │   ├── Document (document_reader, auto_reader, web_reader, llm_retrieval)
    │   └── Support (social, temporal, embodiment, reflection, etc.)
    │
    ├── Integrations (llm_integration, sd_integration)
    │
    ├── Feature Systems
    │   ├── Memory Import (memory_import/)
    │   ├── Memory Continuity (memory_continuity/)
    │   ├── Session Browser (session_browser/)
    │   ├── Media Experience (media_orchestrator, media_watcher)
    │   └── Document Management (document_manager*)
    │
    └── UI Systems (voice_ui, autonomous_ui, curation_ui, tab_system)
```

---

*Generated: December 2024*
*Location: D:\ChristinaStuff\alphakayzero*
