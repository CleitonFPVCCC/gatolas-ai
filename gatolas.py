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
from flask import Flask, request, jsonify

# =========================
# ⚙️ CONFIG
# =========================
API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
SERVER_URL = "https://gatolas-ai.onrender.com/perguntar"

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
nomes = ["Senhor Cleiton", "Drone Man", "Comandante"]

# =========================
# CONTROLO
# =========================
ativo = False
falando = False
tempo_ultimo_comando = 0
TEMPO_ATIVO = 20
modo_dono = True

# =========================
# 🎤 WAKE WORDS
# =========================
WAKE_WORDS = ["gatolas", "acorda", "wake up"]

# =========================
# 🌐 FLASK (CONTROLO VIA TELEFONE)
# =========================
app = Flask(__name__)

@app.route("/comando", methods=["POST"])
def comando_remoto():
    data = request.json
    texto = data.get("texto", "")

    fila.put(("remoto", texto, True))

    return jsonify({"status": "ok", "comando": texto})

# =========================
# 🧠 IA LOCAL
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
            "messages": historico[-6:]
        }

        response = requests.post(API_URL, headers=headers, json=data)

        if response.status_code == 200:
            resposta = response.json()["choices"][0]["message"]["content"]
            historico.append({"role": "assistant", "content": resposta})
            return resposta.strip()

    except:
        pass

    return "Erro na IA."

# =========================
# 🌐 SERVIDOR
# =========================
def perguntar_servidor(texto, is_dono):
    try:
        r = requests.post(SERVER_URL, json={"texto": texto, "dono": is_dono}, timeout=10)

        if r.status_code == 200:
            data = r.json()
            return data.get("resposta") or data.get("reply")

    except:
        pass

    return None

# =========================
# 🧠 AÇÕES (CONTROLAR PC)
# =========================
def executar_acao(cmd):

    if "abrir youtube" in cmd:
        os.system("start https://youtube.com")
        return "Abrindo YouTube"

    if "abrir google" in cmd:
        os.system("start https://google.com")
        return "Abrindo Google"

    if "abrir vscode" in cmd:
        os.system("code")
        return "Abrindo VS Code"

    if "desligar pc" in cmd:
        os.system("shutdown /s /t 5")
        return "Desligando computador"

    return None

# =========================
# 🧠 CÉREBRO
# =========================
def gatolas_brain(pergunta, is_dono):

    # ações primeiro
    acao = executar_acao(pergunta)
    if acao:
        return acao

    # servidor
    resposta = perguntar_servidor(pergunta, is_dono)
    if resposta:
        return resposta

    # fallback IA
    return perguntar_ia(pergunta)

# =========================
# 🔊 VOZ
# =========================
async def falar_async(texto):
    global falando

    falando = True

    try:
        nome = "voz.mp3"

        communicate = edge_tts.Communicate(text=texto, voice="pt-BR-AntonioNeural")
        await communicate.save(nome)

        pygame.mixer.music.load(nome)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        os.remove(nome)

    except:
        pass

    falando = False

def falar(texto):
    threading.Thread(target=lambda: asyncio.run(falar_async(texto))).start()

# =========================
# 🎤 OUVIR
# =========================
def ouvir():
    global ativo, tempo_ultimo_comando

    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("Microfone ativo")

        while True:
            try:
                audio = r.listen(source)
                texto = r.recognize_google(audio, language="pt-PT").lower()

                if any(w in texto for w in WAKE_WORDS):
                    ativo = True
                    texto = texto.replace("gatolas", "").strip()

                    if texto:
                        fila.put(("voz", texto, True))

                elif ativo:
                    fila.put(("voz", texto, True))

            except:
                pass

# =========================
# ⌨️ TECLADO
# =========================
def teclado():
    while True:
        txt = input("Você: ")
        fila.put(("teclado", txt, True))

# =========================
# 🔁 PROCESSAR
# =========================
def processar(cmd, origem, dono):
    resposta = gatolas_brain(cmd, dono)

    if resposta:
        print("Gatolas:", resposta)

        if origem != "teclado":
            falar(resposta)

# =========================
# 🚀 START
# =========================
threading.Thread(target=ouvir, daemon=True).start()
threading.Thread(target=teclado, daemon=True).start()

# 🔥 servidor remoto
threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()

falar("Sistema Gatolas ativo")

while True:

    while not fila.empty():
        origem, comando, dono = fila.get()
        processar(comando, origem, dono)

    time.sleep(0.1)