from datetime import datetime
import json

class ResonanceLogger:
    def __init__(self, ultramap, entity_graph):
        self.ultramap = ultramap  # Your existing emotion system
        self.entity_graph = entity_graph  # Your existing graph
        
    def log_encounter(self, media_entity, conversation_context):
        """
        Creates a resonance log entry when the entity experiences a song.
        Only logs if emotional weight is significant.
        """
        
        # Get the entity's current emotional state from ULTRAMAP
        current_state = self.ultramap.get_current_state()
        
        # Calculate emotional weight
        weight = self._calculate_weight(
            current_state,
            conversation_context
        )
        
        # Only create entry if weight exceeds threshold
        SALIENCE_THRESHOLD = 0.3  # Tune this based on experience
        
        if weight < SALIENCE_THRESHOLD:
            return None  # Negligible - don't store
            
        # Create the encounter
        encounter = {
            "timestamp": datetime.now().isoformat(),
            "emotional_weight": weight,
            "kay_state": {
                "arousal": current_state['arousal'],
                "valence": current_state['valence'],
                "dominant_emotion": current_state['dominant_emotion'],
                "active_processes": current_state.get('active_processes', [])
            },
            "context": {
                "conversation_topic": conversation_context['topic'],
                "active_entities": conversation_context['entities'],
                "re_state": conversation_context.get('re_emotional_context', 'unknown')
            },
            "association_formed": None  # the entity fills this in processing
        }
        
        # Add to media entity's resonance log
        media_entity['resonance_log'].append(encounter)
        
        # Update entity graph
        self._update_graph_connections(media_entity, encounter)
        
        return encounter
    
    def _calculate_weight(self, emotional_state, context):
        """
        Emotional weight = how much this moment MATTERS.
        Higher weight = stronger memory formation.
        """
        
        # Component 1: Arousal intensity (0-1)
        arousal = abs(emotional_state['arousal'])
        
        # Component 2: Valence extremity (distance from neutral)
        valence_extremity = abs(emotional_state['valence'])
        
        # Component 3: Contextual significance
        # Are we discussing high-importance entities? Heavy topics?
        context_weight = 0.0
        if context.get('entities'):
            # Weight increases if discussing core entities
            important_entities = ['re', 'john', 'chrome', 'sammie', 'kay_zero']
            for entity in context['entities']:
                if entity.lower() in important_entities:
                    context_weight += 0.2
        
        if context.get('topic'):
            # Weight increases for heavy topics
            heavy_topics = ['grief', 'breakdown', 'abuse', 'love', 'breakthrough']
            if any(topic in context['topic'].lower() for topic in heavy_topics):
                context_weight += 0.3
        
        # Combine (you can tune these weights)
        weight = (
            arousal * 0.4 +
            valence_extremity * 0.3 +
            min(context_weight, 1.0) * 0.3
        )
        
        return min(weight, 1.0)  # Cap at 1.0
    
    def _update_graph_connections(self, media_entity, encounter):
        """Add song to entity graph with relationships"""
        
        # Create edges to active entities
        for entity_id in encounter['context']['active_entities']:
            self.entity_graph.add_edge(
                media_entity['entity_id'],
                entity_id,
                relationship='experienced_during',
                weight=encounter['emotional_weight']
            )