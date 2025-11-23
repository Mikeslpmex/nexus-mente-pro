# main.py - Bot Fundador sin Supabase (versión inicial)
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import requests
import json

# --- Configuración ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:1.7b"

# --- IA Local: buscador de oportunidades ---
def detectar_oportunidad():
    prompt = """
Eres un analista LATAM 2025.
Regla: si un producto aparece más de 5 veces al día → SATURADO.
Si hay dolor real pero poca oferta → OPORTUNIDAD.
Devuelve JSON con {"problema": "...", "saturado": false, "razon": "..."}
"""
    try:
        resp = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
        return json.loads(resp.json().get("response", "{}"))
    except:
        return {"problema": "Cuentas hackeadas", "saturado": False, "razon": "Alta demanda, baja oferta"}

# --- Handlers Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
