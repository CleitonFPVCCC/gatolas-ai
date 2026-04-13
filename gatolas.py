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

# 🔊 AUDIO
pygame.mixer.init()

# 📥 FILA
fila = queue.Queue()

# 🧠 MEMÓRIA
memoria = {"tarefas": []}
historico = []

# 👤 NOMES
nomes = ["Senhor C", "Senhor Cleiton", "Young Drone Man"]

# 🔑 API
API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ⏱️ CONTROLO
ativo = False
falando = False
tempo_ultimo_comando = 0
TEMPO_ATIVO = 20

# 🔥 CONTROLO DE UTILIZADOR
modo_dono = False

# 🔥 WAKE WORDS (NÃO ALTERADO)
WAKE_WORDS = [
    "gatolas", "gatola", "gato", "wakeup", "wa", "canto", "12", "ca", "123",
    "hora de acordar", "ok gatolas", "one two three",
    "wake up", "acorde", "acorda", "cartolas", "cartola"
]

# =========================
# 🧠 IA
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
            "temperature": 0.7,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você é Gatolas, estilo Jarvis.\n"
                        "- Fala natural, elegante e humano\n"
                        "- Responde rápido e curto (máx 2 frases)\n"
                        "- Só chama 'senhor' quando for o dono\n"
                        "- Se falarem português responde português\n"
                        "- Se falarem inglês responde inglês"
                    )
                }
            ] + historico[-6:]
        }

        response = requests.post(API_URL, headers=headers, json=data)

        if response.status_code == 200:
            resposta = response.json()["choices"][0]["message"]["content"]
            historico.append({"role": "assistant", "content": resposta})
            return resposta.strip()

        else:
            print("Erro API:", response.text)
            return "Não consegui responder agora."

    except Exception as e:
        print("Erro IA:", e)
        return "Erro na inteligência."

def perguntar_servidor(texto, is_dono):
    try:
        response = requests.post(
            "http://127.0.0.1:8000/perguntar",
            json={
                "texto": texto,
                "dono": is_dono
            },
            timeout=5
        )

        if response.status_code == 200:
            return response.json()["resposta"]

        return "Erro ao comunicar com o cérebro."

    except Exception as e:
        print("Erro servidor:", e)
        return "Servidor não disponível."

# =========================
# 🧠 CÉREBRO CENTRAL
# =========================
def gatolas_brain(pergunta, is_dono):
    # 🔹 primeiro tenta comandos locais
    resposta_local = resposta(pergunta, is_dono)

    if resposta_local:
        return resposta_local

    # 🔥 fallback para IA
    return perguntar_ia(pergunta)


# =========================
# 🔊 VOZ
# =========================
def detectar_idioma(texto):
    texto = texto.lower()

    palavras_pt = ["não", "sim", "você", "está", "como", "para", "obrigado"]
    palavras_en = ["the", "is", "are", "you", "how", "what", "thanks"]

    pt = sum(p in texto for p in palavras_pt)
    en = sum(p in texto for p in palavras_en)

    return "pt" if pt >= en else "en"

async def falar_async(texto):
    global falando

    if not texto:
        return

    print("Gatolas:", texto)

    try:
        falando = True

        # 🔥 DETECTAR IDIOMA
        idioma = detectar_idioma(texto)

        if idioma == "en":
            voice = "en-US-GuyNeural"
        else:
            voice = "pt-BR-AntonioNeural"

        nome_arquivo = f"voz_{int(time.time())}.mp3"

        communicate = edge_tts.Communicate(text=texto, voice=voice)
        await communicate.save(nome_arquivo)

        pygame.mixer.music.load(nome_arquivo)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

        os.remove(nome_arquivo)

    except Exception as e:
        print("Erro voz:", e)

    falando = False

def falar(texto):
    threading.Thread(
        target=lambda: asyncio.run(falar_async(texto))
    ).start()


# =========================
# 🎤 OUVIR
# =========================
def ouvir_continuo():
    global ativo, tempo_ultimo_comando, falando, modo_dono

    r = sr.Recognizer()
    r.energy_threshold = 400
    r.dynamic_energy_threshold = False
    r.pause_threshold = 0.6
    r.non_speaking_duration = 0.3

    with sr.Microphone() as source:
        print("🎧 Microfone ativo...")
        r.adjust_for_ambient_noise(source, duration=1)

        while True:

            if falando:
                time.sleep(0.1)
                continue

            try:
                print("🎤 A escutar...")
                audio = r.listen(source)

                texto = r.recognize_google(audio, language="pt-PT").lower()
                print("🎤 Você disse:", texto)

                ativado = any(p in texto for p in WAKE_WORDS)

                if ativado:
                    ativo = True
                    modo_dono = True
                    tempo_ultimo_comando = time.time()

                    for p in WAKE_WORDS:
                        texto = texto.replace(p, "")

                    texto = texto.strip()

                    if len(texto) > 3:
                        fila.put(("voz", texto, True))
                    else:
                        falar("Sim, estou ouvindo.")

                elif ativo and len(texto) > 3:
                    fila.put(("voz", texto, modo_dono))
                    tempo_ultimo_comando = time.time()

            except sr.UnknownValueError:
                pass

            except Exception as e:
                print("❌ Erro:", e)
                time.sleep(1)


# =========================
# 🧠 RESPOSTAS
# =========================
def resposta(cmd, is_dono):
    nome = random.choice(nomes)
    cmd = cmd.lower().strip()

    if "dia" in cmd:
        return time.strftime("Hoje é %A, %d de %B.")

    elif "horas" in cmd:
        return time.strftime("Agora são %H:%M.")

    elif "o que é" in cmd:
        resp = perguntar_ia(cmd)
        return f"{nome}, {resp}" if is_dono else resp

    if not is_dono:
        return "Acesso limitado."

    if "adicionar tarefa" in cmd:
        memoria["tarefas"].append(cmd)
        return f"Tarefa registada, {nome}."

    elif "tarefas" in cmd:
        return "Suas tarefas: " + ", ".join(memoria["tarefas"]) if memoria["tarefas"] else "Nenhuma tarefa."

    elif "ccc" in cmd:
        return "CCC Express Delivery está a crescer."

    if len(cmd) < 10:
        return ""

    resp = perguntar_ia(cmd)
    return f"{nome}, {resp}"


# =========================
# 🔁 PROCESSAR
# =========================
def processar(cmd, origem, is_dono):
    resposta_texto = perguntar_servidor(cmd, is_dono)

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
        try:
            entrada = input("\nVocê: ")
            if entrada:
                fila.put(("teclado", entrada.lower(), True))
        except EOFError:
            break


# =========================
# 🚀 START
# =========================
falar("Sistema Gatolas ativo. Pronto para servir.")

threading.Thread(target=ouvir_continuo, daemon=True).start()
threading.Thread(target=ler_teclado, daemon=True).start()

# LOOP
while True:

    while not fila.empty():
        origem, comando, is_dono = fila.get()
        processar(comando, origem, is_dono)

    if ativo and not falando and (time.time() - tempo_ultimo_comando > TEMPO_ATIVO):
        ativo = False
        modo_dono = False
        print("🔕 Gatolas em standby...")

    time.sleep(0.1)