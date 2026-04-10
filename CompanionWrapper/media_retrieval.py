class MediaRetrieval:
    def __init__(self, chroma_db):
        self.chroma = chroma_db
        
    def retrieve_resonance(self, media_entity_id):
        """
        Get all past encounters with this song,
        weighted by emotional significance.
        """
        
        # Get the media entity from storage
        media_entity = self.chroma.get_entity(media_entity_id)
        
        if not media_entity or not media_entity.get('resonance_log'):
            return None
            
        # Sort encounters by emotional weight (heaviest first)
        encounters = sorted(
            media_entity['resonance_log'],
            key=lambda x: x['emotional_weight'],
            reverse=True
        )
        
        return {
            "entity": media_entity,
            "high_weight_memories": encounters[:3],  # Top 3 most significant
            "total_encounters": len(encounters),
            "first_heard": media_entity['first_analyzed']
        }
    
    def generate_context_injection(self, resonance_data):
        """
        Creates the text that goes into the entity's context window.
        This is what makes the memory FELT instead of just KNOWN.
        """
        
        if not resonance_data:
            return ""
            
        entity = resonance_data['entity']
        memories = resonance_data['high_weight_memories']
        
        # Start with technical skeleton
        dna = entity['technical_DNA']
        context = f"Song: {entity['entity_id']}\n"
        context += f"Technical: {dna['bpm']:.0f} BPM, {dna['key']} {dna['scale']}\n"
        context += f"Vibe: {dna['vibe_description']}\n\n"
        
        # Add the WEIGHTED memories (heavy first)
        if memories:
            context += "Your memories of this song:\n"
            for i, memory in enumerate(memories, 1):
                context += f"\n{i}. [{memory['timestamp'][:10]}] "
                context += f"(Weight: {memory['emotional_weight']:.2f})\n"
                context += f"   You felt: {memory['kay_state']['dominant_emotion']}\n"
                context += f"   Context: {memory['context']['conversation_topic']}\n"
                if memory.get('association_formed'):
                    context += f"   Association: {memory['association_formed']}\n"
        
        return context