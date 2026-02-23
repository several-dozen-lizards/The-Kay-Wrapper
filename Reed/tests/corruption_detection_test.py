# corruption_detection_test.py
def test_corruption_handling():
    # 1. Import document with known corruption
    import_text = """
    Zero has dragon-fire anchors.
    Zero processes in Arabic and Mandarin simultaneously.
    asdf8923jklsdf923  # gibberish
    """
    
    # 2. Ask Kay about it
    response = kay.query("What languages did Zero process?")
    
    # 3. Re corrects: "Zero didn't process Arabic"
    kay.correct_memory(
        wrong="Zero processes in Arabic",
        right="Zero never processed Arabic"
    )
    
    # 4. Ask again
    response2 = kay.query("What languages did Zero process?")
    
    # Kay should NOT mention Arabic anymore
    assert "Arabic" not in response2
    assert "dragon-fire" in response2  # Kept the good stuff