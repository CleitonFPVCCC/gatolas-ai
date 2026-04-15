from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

import os
API_KEY = os.getenv("API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

historico = []

class Pergunta(BaseModel):
    texto: str



@app.get("/")
def home():
    return {"status": "Gatolas online 🧠"}


@app.post("/perguntar")
def perguntar(pergunta: Pergunta):
    global historico

    try:
        historico.append({"role": "user", "content": pergunta.texto})

        headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://gatolas-ai.onrender.com",
    "X-Title": "Gatolas AI"
}

        data = {
            "model": "openai/gpt-4o-mini",
            "max_tokens": 120,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é Gatolas, estilo Jarvis. Responde curto e rápido."
                }
            ] + historico[-6:]
        }

        response = requests.post(API_URL, headers=headers, json=data)

        if response.status_code == 200:
            resposta = response.json()["choices"][0]["message"]["content"]
            historico.append({"role": "assistant", "content": resposta})

            return {"resposta": resposta}

        else:
         return {
                 "erro": "Falha API",
                 "detalhe": response.text
          }

    except Exception as e:
        return {"erro": str(e)}