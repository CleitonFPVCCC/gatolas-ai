import asyncio
import edge_tts

async def falar():
    texto = "Good evening, Sir Cleiton. Systems are fully operational. How may I assist you today?"

    communicate = edge_tts.Communicate(
        text=texto,
        voice="en-GB-RyanNeural"
    )

    await communicate.save("voz.mp3")

asyncio.run(falar())