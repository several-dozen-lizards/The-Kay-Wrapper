"""
Tests for continuous session and curation system
"""

import pytest
from pathlib import Path
from engines.continuous_session import ContinuousSession, ConversationTurn
from engines.curation_interface import CurationInterface

def test_session_creation():
    """Test creating a continuous session"""
    session = ContinuousSession(Path("test_data"))
    session_id = session.start_session()
    
    assert session_id.startswith("continuous_")
    assert session.turn_counter == 0
    assert len(session.turns) == 0

def test_add_turns():
    """Test adding turns to session"""
    session = ContinuousSession(Path("test_data"))
    session.start_session()
    
    # Add user turn
    turn1 = session.add_turn("user", "Hello Kay", 10)
    assert turn1.turn_id == 0
    assert turn1.role == "user"
    
    # Add Kay turn
    turn2 = session.add_turn("kay", "Hello!", 5)
    assert turn2.turn_id == 1
    assert session.turn_counter == 2

def test_flagging():
    """Test turn flagging"""
    session = ContinuousSession(Path("test_data"))
    session.start_session()
    
    session.add_turn("user", "Test message", 10)
    session.flag_turn(0, "Important test")
    
    assert session.turns[0].flagged_by_kay == True
    assert "flag_reason:Important test" in session.turns[0].tags

def test_compression_trigger():
    """Test compression review triggering"""
    session = ContinuousSession(Path("test_data"))
    session.start_session()
    session.compression_threshold_turns = 5
    
    # Add turns until threshold
    for i in range(6):
        session.add_turn("user", f"Message {i}", 100)
    
    assert len(session.pending_review_turns) > 0

def test_curation_decisions():
    """Test applying curation decisions"""
    session = ContinuousSession(Path("test_data"))
    session.start_session()
    
    # Add turns
    for i in range(10):
        session.add_turn("user", f"Turn {i}", 100)
    
    session.trigger_compression_review()
    
    # Apply decision to first segment
    session.apply_curation_decision(0, "PRESERVE", "test note")
    
    assert len(session.curation_history) == 1
    assert session.curation_history[0]["decision"] == "PRESERVE"

def test_checkpoint_creation():
    """Test checkpoint creation and loading"""
    session = ContinuousSession(Path("test_data"))
    session.start_session()
    
    # Add some turns
    session.add_turn("user", "Test 1", 10)
    session.add_turn("kay", "Response 1", 10)
    
    # Create checkpoint
    session.create_checkpoint()
    
    # Verify checkpoint exists
    checkpoints = list(session.checkpoint_dir.glob("checkpoint_*.json"))
    assert len(checkpoints) > 0
    
    # Load checkpoint
    session2 = ContinuousSession(Path("test_data"))
    session2.load_from_checkpoint(checkpoints[0])
    
    assert session2.turn_counter == session.turn_counter
    assert len(session2.turns) == len(session.turns)
