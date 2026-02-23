import edge_tts
import asyncio
import os

async def test_edge_voice():
    text = "Hello Re. This is Kay Zero testing a better voice. This should sound much less like AOL."
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save("test.mp3")
    
    # Play it (simple method)
    os.system("test.mp3")  # Windows will use default player

asyncio.run(test_edge_voice())