import threading
import queue
import time
import random
import os
import requests
import asyncio
import edge_tts
import pygame
import speech_recognition as sr
import webbrowser

# =========================
# 🔊 AUDIO
# =========================
pygame.mixer.init()

# =========================
# 📥 FILA
# =========================
fila = queue.Queue()

# =========================
# 🧠 MEMÓRIA
# =========================
memoria = {"tarefas": []}
historico = []

# =========================
# 👤 NOMES
# =========================
nomes = ["Senhor C", "Senhor Cleiton", "Young Drone Man"]

# =========================
# 🔑 API
# =========================
API_KEY = ""
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# =========================
# 🌐 SERVIDOR
# =========================
SERVER_URL = "https://gatolas-ai.onrender.com/perguntar"
CONTROL_URL = "https://gatolas-ai.onrender.com/controlar"

# =========================
# ⏱️ CONTROLO
# =========================
ativo = False
falando = False
tempo_ultimo_comando = 0
TEMPO_ATIVO = 20

# =========================
# 🔥 MODO DONO INTELIGENTE
# =========================
modo_dono = False
voz_dono_assinatura = None  # futuro: reconhecimento de voz real

# =========================
# 🔥 WAKE WORDS
# =========================
WAKE_WORDS = [
    "gatolas", "gatola", "gato", "wake up",
    "acorda", "ok gatolas"
]

# =========================
# 🌐 CONTROLO DE DISPOSITIVOS
# =========================
def controlar_dispositivo(acao, destino="pc"):
    try:
        requests.post(CONTROL_URL, json={
            "acao": acao,
            "destino": destino
        }, timeout=5)
    except:
        pass

# =========================
# 🧠 IA LOCAL (backup)
# =========================
def perguntar_ia(pergunta):
    global historico

    try:
        historico.append({"role": "user", "content": pergunta})

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openai/gpt-3.5-turbo",
            "max_tokens": 120,
            "messages": historico[-6:]
        }

        r = requests.post(API_URL, headers=headers, json=data)

        if r.status_code == 200:
            resposta = r.json()["choices"][0]["message"]["content"]
            return resposta

    except:
        pass

    return "Erro na IA."

# =========================
# 🌐 SERVIDOR
# =========================
def perguntar_servidor(texto, is_dono):
    try:
        r = requests.post(SERVER_URL, json={
            "texto": texto,
            "dono": is_dono
        }, timeout=10)

        if r.status_code == 200:
            data = r.json()
            return data.get("resposta")

    except:
        return None

# =========================
# 🧠 CÉREBRO
# =========================
def gatolas_brain(cmd, is_dono):

    # 🔹 comandos locais primeiro
    r = resposta(cmd, is_dono)
    if r:
        return r

    # 🌐 servidor
    r = perguntar_servidor(cmd, is_dono)
    if r:
        return r

    # fallback IA
    return perguntar_ia(cmd)

# =========================
# 🔊 VOZ
# =========================
def detectar_idioma(texto):
    if any(p in texto for p in ["the", "is", "you"]):
        return "en"
    return "pt"

async def falar_async(texto):
    global falando

    if not texto:
        return

    print("Gatolas:", texto)

    try:
        falando = True

        voice = "pt-BR-AntonioNeural"
        if detectar_idioma(texto) == "en":
            voice = "en-US-GuyNeural"

        file = f"voz_{time.time()}.mp3"

        tts = edge_tts.Communicate(texto, voice)
        await tts.save(file)

        pygame.mixer.music.load(file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        os.remove(file)

    except Exception as e:
        print("Erro voz:", e)

    falando = False

def falar(texto):
    threading.Thread(target=lambda: asyncio.run(falar_async(texto))).start()

# =========================
# 🎤 OUVIR
# =========================
def ouvir_continuo():
    global ativo, tempo_ultimo_comando, modo_dono

    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎧 Ouvindo...")

        while True:
            try:
                audio = r.listen(source)
                texto = r.recognize_google(audio, language="pt-PT").lower()

                print("Você:", texto)

                if any(w in texto for w in WAKE_WORDS):
                    ativo = True
                    modo_dono = True
                    tempo_ultimo_comando = time.time()

                    for w in WAKE_WORDS:
                        texto = texto.replace(w, "")

                    if texto.strip():
                        fila.put(("voz", texto, True))
                    else:
                        falar("Sim, estou ouvindo.")

                elif ativo:
                    fila.put(("voz", texto, modo_dono))

            except:
                pass

# =========================
# 🧠 COMANDOS REAIS (IMPORTANTE)
# =========================
def resposta(cmd, is_dono):
    cmd = cmd.lower()

    # 📅 hora
    if "horas" in cmd:
        return time.strftime("Agora são %H:%M")

    # 🌐 abrir youtube (PC)
    if "youtube" in cmd:
        webbrowser.open("https://youtube.com")
        return "Abrindo YouTube no computador."

    # 📱 abrir whatsapp no telefone
    if "whatsapp" in cmd:
        controlar_dispositivo("abrir_whatsapp", "telefone")
        return "Abrindo WhatsApp no telefone."

    # 💻 abrir chrome
    if "chrome" in cmd:
        os.system("start chrome")
        return "Abrindo Chrome."

    if not is_dono:
        return "Acesso limitado."

    return None

# =========================
# 🔁 PROCESSAR
# =========================
def processar(cmd, origem, is_dono):

    resposta_texto = gatolas_brain(cmd, is_dono)

    if resposta_texto:
        if origem == "voz":
            falar(resposta_texto)
        else:
            print("Gatolas:", resposta_texto)

# =========================
# ⌨️ TECLADO
# =========================
def ler_teclado():
    while True:
        entrada = input("\nVocê: ")
        fila.put(("teclado", entrada, True))

# =========================
# 🚀 START
# =========================
falar("Sistema Gatolas ativo.")

threading.Thread(target=ouvir_continuo, daemon=True).start()
threading.Thread(target=ler_teclado, daemon=True).start()

while True:

    while not fila.empty():
        origem, comando, dono = fila.get()
        processar(comando, origem, dono)

    time.sleep(0.1)