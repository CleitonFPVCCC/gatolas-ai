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
import json
import subprocess

# =========================
# 🔊 AUDIO
# =========================
pygame.mixer.init()

# =========================
# 📥 FILA
# =========================
fila = queue.Queue()

# =========================
# 🧠 MEMÓRIA (JSON)
# =========================
MEM_FILE = "memoria.json"

def carregar_memoria():
    if os.path.exists(MEM_FILE):
        with open(MEM_FILE, "r") as f:
            return json.load(f)
    return {"tarefas": [], "dono": "cleiton"}

def salvar_memoria():
    with open(MEM_FILE, "w") as f:
        json.dump(memoria, f, indent=4)

memoria = carregar_memoria()

# =========================
# 👤 NOMES
# =========================
nomes = ["Senhor Cleiton", "Comandante", "Drone Man"]

# =========================
# 🔑 API
# =========================
API_KEY = ""
API_URL = "https://openrouter.ai/api/v1/chat/completions"

SERVER_URL = "https://gatolas-ai.onrender.com/perguntar"

# =========================
# ⏱️ CONTROLO
# =========================
ativo = False
falando = False
modo_dono = False
tempo_ultimo_comando = 0
TEMPO_ATIVO = 20

# =========================
# 🔥 WAKE WORDS
# =========================
WAKE_WORDS = ["gatolas", "ok gatolas", "acorda"]

DONO_KEY = ["sou eu", "cleiton", "modo dono"]

# =========================
# 🧠 IA
# =========================
def perguntar_ia(pergunta):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Você é um assistente estilo Jarvis."},
                {"role": "user", "content": pergunta}
            ]
        }

        r = requests.post(API_URL, headers=headers, json=data)

        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]

    except:
        pass

    return "Erro na IA."

# =========================
# 🌐 SERVIDOR
# =========================
def perguntar_servidor(texto, dono):
    try:
        r = requests.post(SERVER_URL, json={"texto": texto, "dono": dono})
        if r.status_code == 200:
            return r.json().get("resposta")
    except:
        pass
    return None

# =========================
# 🖥️ CONTROLO DO PC
# =========================
def executar_comando(cmd):

    cmd = cmd.lower()

    if "abrir chrome" in cmd:
        subprocess.Popen("start chrome", shell=True)
        return "Abrindo Chrome."

    if "abrir vscode" in cmd:
        subprocess.Popen("code", shell=True)
        return "Abrindo VS Code."

    if "desligar pc" in cmd:
        os.system("shutdown /s /t 5")
        return "Desligando o computador."

    if "reiniciar pc" in cmd:
        os.system("shutdown /r /t 5")
        return "Reiniciando."

    return None

# =========================
# 🔊 VOZ
# =========================
async def falar_async(texto):
    global falando

    falando = True
    try:
        file = "voz.mp3"
        tts = edge_tts.Communicate(texto, "pt-BR-AntonioNeural")
        await tts.save(file)

        pygame.mixer.music.load(file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        os.remove(file)

    except Exception as e:
        print(e)

    falando = False

def falar(texto):
    threading.Thread(target=lambda: asyncio.run(falar_async(texto))).start()

# =========================
# 🎤 MICROFONE
# =========================
def ouvir():
    global ativo, modo_dono, tempo_ultimo_comando

    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("Microfone ativo")

        while True:
            try:
                audio = r.listen(source)
                texto = r.recognize_google(audio, language="pt-PT").lower()

                print("Você:", texto)

                if any(w in texto for w in WAKE_WORDS):
                    ativo = True
                    tempo_ultimo_comando = time.time()

                    if any(d in texto for d in DONO_KEY):
                        modo_dono = True
                        falar("Modo dono ativado.")

                    texto = texto.replace("gatolas", "").strip()

                    if texto:
                        fila.put(("voz", texto, modo_dono))

                elif ativo:
                    fila.put(("voz", texto, modo_dono))
                    tempo_ultimo_comando = time.time()

            except:
                pass

# =========================
# 🧠 RESPOSTAS
# =========================
def resposta_local(cmd, dono):

    if "hora" in cmd:
        return time.strftime("Agora são %H:%M")

    if "tarefas" in cmd:
        return str(memoria["tarefas"])

    if dono:

        if "adicionar tarefa" in cmd:
            tarefa = cmd.replace("adicionar tarefa", "").strip()
            memoria["tarefas"].append(tarefa)
            salvar_memoria()
            return "Tarefa adicionada."

    return None

# =========================
# 🔁 PROCESSAR
# =========================
def processar(cmd, origem, dono):

    # 🔥 comandos do PC
    if dono:
        r = executar_comando(cmd)
        if r:
            falar(r)
            return

    # 🧠 local
    r = resposta_local(cmd, dono)
    if r:
        falar(r)
        return

    # 🌐 servidor
    r = perguntar_servidor(cmd, dono)
    if r:
        falar(r)
        return

    # 🤖 IA fallback
    r = perguntar_ia(cmd)
    falar(r)

# =========================
# ⌨️ TECLADO
# =========================
def teclado():
    while True:
        t = input("Você: ")
        fila.put(("teclado", t, True))

# =========================
# 🚀 START
# =========================
falar("Gatolas online.")

threading.Thread(target=ouvir, daemon=True).start()
threading.Thread(target=teclado, daemon=True).start()

while True:

    while not fila.empty():
        origem, cmd, dono = fila.get()
        processar(cmd, origem, dono)

    if ativo and time.time() - tempo_ultimo_comando > TEMPO_ATIVO:
        ativo = False
        modo_dono = False
        print("Standby")

    time.sleep(0.1)