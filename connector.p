import os
import telebot
from supabase import create_client, Client
from plugins.ideas_bot import IdeaGenerator

# 🔐 Credenciales fundadoras
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
TELEGRAM_TOKEN = "8511825156:AAFt56Ku-WhjygeHAfkybxtQjaZEF0CcyeI"
TELEGRAM_CHAT_ID = "7318862870"

# 🧠 Inicializa Telegram
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 🗄️ Inicializa Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🧬 Inicializa Nexus-Mente-Pro (ideas_bot)
ideas = IdeaGenerator()

# 📌 Función para registrar oportunidad
def registrar_oportunidad(texto):
    idea = ideas.generate(texto)
    data = {
        "tema": texto,
        "idea": idea,
        "autor": "Hunter Orion",
        "timestamp": os.getenv("NOW", "auto")
    }
    supabase.table("oportunidades").insert(data).execute()
    bot.send_message(TELEGRAM_CHAT_ID, f"🧠 Nueva idea registrada:\n{idea}")

# 📌 Activación desde Telegram
@bot.message_handler(commands=["scan"])
def handle_scan(message):
    tema = message.text.replace("/scan ", "")
    registrar_oportunidad(tema)
    bot.reply_to(message, f"🔍 Escaneando oportunidades sobre: {tema}")

# 🧭 Inicio ritual
if __name__ == "__main__":
    print("🔗 Conexión Hunter-Orion iniciada...")
    bot.polling()
