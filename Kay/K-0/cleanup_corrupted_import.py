"""
Memory Cleanup Script - Remove contaminated data from corrupted import.

Kay read "Archive Zero Log 1.docx" as raw binary/XML instead of parsed text,
creating 357 segments of corrupted data. This script removes all contaminated:
- Memory entries (full turns, facts, glyphs)
- Entity graph entries
- Identity facts
- Relationship data

USAGE:
    python cleanup_corrupted_import.py

SAFETY:
    - Creates backup before modifying anything
    - Shows preview of what will be deleted
    - Asks for confirmation
    - Can be run multiple times safely
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Set

MEMORY_FILE = "memory/memory_layers.json"
ENTITY_FILE = "memory/entity_graph.json"
DOCUMENTS_FILE = "memory/documents.json"
BACKUP_DIR = "memory/backups"

# Document that was corrupted
CORRUPTED_DOC = "Archive Zero Log 1.docx"


class MemoryCleanup:
    """Clean up contaminated memories from corrupted import."""
    
    def __init__(self):
        self.memory_data = None
        self.entity_data = None
        self.documents_data = None
        
        self.contaminated_turns = set()
        self.contaminated_memory_ids = set()
        self.contaminated_entity_ids = set()
        
    def load_data(self):
        """Load all memory-related files."""
        print("Loading memory data...")
        
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                self.memory_data = json.load(f)
            
            # Combine all tier memories into single list for processing
            all_memories = []
            tier_counts = {}
            
            for tier in ['working', 'episodic', 'semantic']:
                tier_data = self.memory_data.get(tier, [])
                if isinstance(tier_data, list):
                    tier_counts[tier] = len(tier_data)
                    all_memories.extend(tier_data)
            
            total = sum(tier_counts.values())
            print(f"  [OK] Loaded {total} memories across tiers:")
            for tier, count in tier_counts.items():
                print(f"       {tier}: {count}")
            
            # Store combined list for processing
            self.all_memories = all_memories
            
        except Exception as e:
            print(f"  [ERROR] Failed to load memory file: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        try:
            with open(ENTITY_FILE, 'r', encoding='utf-8') as f:
                self.entity_data = json.load(f)
            
            # Count entities properly regardless of structure
            entities_count = 0
            if isinstance(self.entity_data, dict):
                if 'entities' in self.entity_data:
                    entities = self.entity_data.get('entities', {})
                    if isinstance(entities, dict):
                        entities_count = len(entities)
                    elif isinstance(entities, list):
                        entities_count = len(entities)
                else:
                    # Top-level might be entities directly
                    entities_count = len(self.entity_data)
            
            print(f"  [OK] Loaded {entities_count} entities")
        except Exception as e:
            print(f"  [ERROR] Failed to load entity file: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        try:
            with open(DOCUMENTS_FILE, 'r', encoding='utf-8') as f:
                self.documents_data = json.load(f)
            print(f"  ✓ Loaded {len(self.documents_data)} documents")
        except Exception as e:
            print(f"  ! No documents file (this is okay)")
            self.documents_data = []
        
        return True
    
    def identify_contaminated_data(self):
        """Identify all contaminated memories, entities, and turns."""
        print(f"\nScanning for contaminated data from '{CORRUPTED_DOC}'...")
        
        # Search through combined memory list
        contaminated = []
        for mem in self.all_memories:
            # Handle both dict and other formats
            if not isinstance(mem, dict):
                continue
                
            # Check multiple possible fields for corruption markers
            is_contaminated = (
                mem.get('source_file') == CORRUPTED_DOC or
                mem.get('_cluster_source') == CORRUPTED_DOC or
                mem.get('doc_name') == CORRUPTED_DOC or
                mem.get('doc_id', '').find('Archive Zero Log') != -1 or
                (isinstance(mem.get('fact'), str) and 
                 'Archive Zero Log' in mem.get('fact', '') and 
                 'corruption' in mem.get('fact', '')) or
                (isinstance(mem.get('user_input'), str) and 
                 'Archive Zero Log' in mem.get('user_input', '')) or
                (isinstance(mem.get('response'), str) and 
                 'corruption' in mem.get('response', '') and
                 'encoding' in mem.get('response', '')) or
                # Look for specific corruption phrases Kay mentioned
                (isinstance(mem.get('response'), str) and
                 ('digital static' in mem.get('response', '') or
                  'encoding artifacts' in mem.get('response', '') or
                  'character encoding' in mem.get('response', '')))
            )
            
            if is_contaminated:
                contaminated.append(mem)
                
                # Track turn number for entity cleanup
                turn = mem.get('turn') or mem.get('parent_turn') or mem.get('turn_number')
                if turn:
                    self.contaminated_turns.add(turn)
                
                # Track memory by its actual object (since no stable ID)
                self.contaminated_memory_ids.add(id(mem))
        
        print(f"  Found {len(contaminated)} contaminated memories")
        print(f"  Spanning {len(self.contaminated_turns)} contaminated turns")
        
        # Sample contaminated facts
        if contaminated:
            print(f"\n  Sample contaminated entries:")
            for mem in contaminated[:5]:
                fact = (mem.get('fact') or 
                       mem.get('user_input') or 
                       mem.get('response') or 
                       'N/A')
                if isinstance(fact, str):
                    print(f"    - {fact[:80]}...")
        
        # Find contaminated entities
        entities = self.entity_data.get('entities', {})
        if not isinstance(entities, dict):
            print(f"  [WARNING] Unexpected entities format, skipping entity cleanup")
            return len(contaminated) > 0
            
        for entity_id, entity_info in entities.items():
            if not isinstance(entity_info, dict):
                continue
                
            # Check if entity was created/modified during contaminated turns
            attributes = entity_info.get('attributes', {})
            
            if isinstance(attributes, dict):
                for attr_name, attr_values in attributes.items():
                    if not isinstance(attr_values, list):
                        continue
                    for attr_data in attr_values:
                        if not isinstance(attr_data, dict):
                            continue
                        turn = attr_data.get('turn')
                        if turn in self.contaminated_turns:
                            self.contaminated_entity_ids.add(entity_id)
                            break
                    if entity_id in self.contaminated_entity_ids:
                        break
        
        print(f"  Found {len(self.contaminated_entity_ids)} contaminated entities")
        
        # Sample contaminated entities
        if self.contaminated_entity_ids:
            print(f"\n  Sample contaminated entities:")
            sample_entities = list(self.contaminated_entity_ids)[:5]
            for entity_id in sample_entities:
                print(f"    - {entity_id}")
        
        return len(contaminated) > 0
    
    def create_backup(self):
        """Create backup of all files before modification."""
        print("\nCreating backups...")
        
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files_to_backup = [
            (MEMORY_FILE, f"{BACKUP_DIR}/memory_layers_{timestamp}.json"),
            (ENTITY_FILE, f"{BACKUP_DIR}/entity_graph_{timestamp}.json"),
        ]
        
        if os.path.exists(DOCUMENTS_FILE):
            files_to_backup.append(
                (DOCUMENTS_FILE, f"{BACKUP_DIR}/documents_{timestamp}.json")
            )
        
        for source, dest in files_to_backup:
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                with open(dest, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"  ✓ Backed up: {os.path.basename(source)}")
            except Exception as e:
                print(f"  ✗ Failed to backup {source}: {e}")
                return False
        
        print(f"\n  Backups saved to: {BACKUP_DIR}/")
        return True
    
    def clean_memories(self):
        """Remove contaminated memories from all tiers."""
        print("\nCleaning memory tiers...")
        
        total_removed = 0
        
        for tier in ['working', 'episodic', 'semantic']:
            tier_data = self.memory_data.get(tier, [])
            original_count = len(tier_data)
            
            # Filter out contaminated memories (using object id)
            clean_tier = [
                mem for mem in tier_data
                if id(mem) not in self.contaminated_memory_ids
            ]
            
            removed = original_count - len(clean_tier)
            total_removed += removed
            
            self.memory_data[tier] = clean_tier
            
            if removed > 0:
                print(f"  [{tier}] Removed {removed}, kept {len(clean_tier)}")
        
        print(f"\n  Total removed: {total_removed} contaminated memories")
        
        return total_removed
    
    def clean_entities(self):
        """Remove contaminated entities and relationships."""
        print("\nCleaning entity graph...")
        
        entities = self.entity_data.get('entities', {})
        relationships = self.entity_data.get('relationships', {})
        
        original_entity_count = len(entities) if isinstance(entities, dict) else 0
        original_rel_count = len(relationships) if isinstance(relationships, dict) else 0
        
        # Remove contaminated entities
        if isinstance(entities, dict):
            for entity_id in list(self.contaminated_entity_ids):
                if entity_id in entities:
                    del entities[entity_id]
        
        # Remove relationships involving contaminated entities
        if isinstance(relationships, dict):
            clean_relationships = {}
            for rel_id, rel_data in relationships.items():
                # Handle dict relationships with entity1/entity2 format
                if isinstance(rel_data, dict):
                    entity1 = rel_data.get('entity1', '')
                    entity2 = rel_data.get('entity2', '')
                    
                    if entity1 not in self.contaminated_entity_ids and entity2 not in self.contaminated_entity_ids:
                        clean_relationships[rel_id] = rel_data
                # Handle string relationships
                elif isinstance(rel_data, str):
                    if rel_data not in self.contaminated_entity_ids:
                        clean_relationships[rel_id] = rel_data
                else:
                    # Unknown format, keep it
                    clean_relationships[rel_id] = rel_data
            
            self.entity_data['relationships'] = clean_relationships
        
        entity_removed = original_entity_count - len(entities)
        rel_removed = original_rel_count - len(clean_relationships) if isinstance(relationships, dict) else 0
        
        print(f"  Removed {entity_removed} contaminated entities")
        print(f"  Removed {rel_removed} contaminated relationships")
        print(f"  Kept {len(entities)} clean entities")
        
        return entity_removed + rel_removed
    
    def clean_documents(self):
        """Remove corrupted document entry."""
        print("\nCleaning documents file...")
        
        if not self.documents_data:
            print("  (No documents to clean)")
            return 0
        
        original_count = len(self.documents_data)
        
        # Filter out corrupted document
        self.documents_data = [
            doc for doc in self.documents_data
            if doc.get('filename') != CORRUPTED_DOC
        ]
        
        removed_count = original_count - len(self.documents_data)
        
        print(f"  Removed {removed_count} document entries")
        
        return removed_count
    
    def save_cleaned_data(self):
        """Save cleaned data back to files."""
        print("\nSaving cleaned data...")
        
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.memory_data, f, indent=2)
            print(f"  ✓ Saved: {MEMORY_FILE}")
        except Exception as e:
            print(f"  ✗ Failed to save memory file: {e}")
            return False
        
        try:
            with open(ENTITY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.entity_data, f, indent=2)
            print(f"  ✓ Saved: {ENTITY_FILE}")
        except Exception as e:
            print(f"  ✗ Failed to save entity file: {e}")
            return False
        
        if self.documents_data:
            try:
                with open(DOCUMENTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.documents_data, f, indent=2)
                print(f"  ✓ Saved: {DOCUMENTS_FILE}")
            except Exception as e:
                print(f"  ✗ Failed to save documents file: {e}")
                return False
        
        return True
    
    def run(self):
        """Run full cleanup process."""
        print("="*60)
        print("MEMORY CLEANUP - Corrupted Import Removal")
        print("="*60)
        
        # Load data
        if not self.load_data():
            print("\n✗ Failed to load data files. Aborting.")
            return False
        
        # Identify contamination
        if not self.identify_contaminated_data():
            print("\n✓ No contaminated data found. Nothing to clean.")
            return True
        
        # Confirm with user
        print("\n" + "="*60)
        print("CLEANUP SUMMARY")
        print("="*60)
        print(f"Will remove:")
        print(f"  - {len(self.contaminated_memory_ids)} memories")
        print(f"  - {len(self.contaminated_entity_ids)} entities")
        print(f"  - Relationships involving contaminated entities")
        print(f"  - Document entry for '{CORRUPTED_DOC}'")
        
        response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\n✗ Cleanup cancelled by user.")
            return False
        
        # Create backup
        if not self.create_backup():
            print("\n✗ Failed to create backup. Aborting for safety.")
            return False
        
        # Clean data
        mem_removed = self.clean_memories()
        entity_removed = self.clean_entities()
        doc_removed = self.clean_documents()
        
        # Save cleaned data
        if not self.save_cleaned_data():
            print("\n✗ Failed to save cleaned data.")
            print("   Your original data is safe in backups.")
            return False
        
        print("\n" + "="*60)
        print("CLEANUP COMPLETE")
        print("="*60)
        print(f"✓ Removed {mem_removed} contaminated memories")
        print(f"✓ Removed {entity_removed} contaminated entities/relationships")
        print(f"✓ Removed {doc_removed} document entries")
        print(f"\n✓ Kay's memory is now clean!")
        print(f"✓ Backups saved to: {BACKUP_DIR}/")
        
        return True


if __name__ == "__main__":
    cleanup = MemoryCleanup()
    success = cleanup.run()
    
    if not success:
        print("\nCleanup did not complete successfully.")
        exit(1)
    
    print("\nYou can now:")
    print("  1. Re-import the document correctly (after fixing the bug)")
    print("  2. Or just continue without that document")
    print("\nKay won't remember the corruption nightmare.")