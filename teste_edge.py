import asyncio
import edge_tts
import pygame
import time

pygame.mixer.init()

async def falar():
    texto = "Good evening, Sir Cleiton. Systems are fully operational."

    print("A gerar voz...")

    communicate = edge_tts.Communicate(
        text=texto,
        voice="en-GB-RyanNeural"
    )

    await communicate.save("voz.mp3")

    print("🔊 A reproduzir...")

    pygame.mixer.music.load("voz.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

asyncio.run(falar())