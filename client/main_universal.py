#!/usr/bin/env python3
import os, json, hmac, hashlib, random, sqlite3, requests, subprocess, threading
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

with open("config.json","r",encoding="utf-8") as f:
    CFG = json.load(f)

BOT_TOKEN = CFG.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = CFG.get("ADMIN_CHAT_ID")
AFILIADO_ID = CFG.get("AFILIADO_ID","CHMI3457849")
API_KEY_BING = CFG.get("API_KEY_BING")
API_KEY_BRAVE = CFG.get("API_KEY_BRAVE")
USE_OLLAMA = CFG.get("USE_OLLAMA", False)
OLLAMA_MODEL = CFG.get("OLLAMA_MODEL", "ventas-bot")

class LocalAIBot:
    def __init__(self, db_path="local_inventory.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.setup_database()
        self.setup_ai_rules()

    def setup_database(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, price REAL, stock INTEGER,
            description TEXT, sku TEXT UNIQUE, platform TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER, platform TEXT,
            sale_price REAL, quantity INTEGER, client_info TEXT,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id))""")
        self.conn.commit()

    def setup_ai_rules(self):
        self.rules = {
            "saludo": {"patterns": ["hola","buenos días"], "responses": ["¡Hola! ¿En qué puedo ayudarte?"]},
            "inventario": {"patterns": ["inventario","stock"], "responses": ["¿Quieres ver el inventario actual?"]},
            "reporte": {"patterns": ["reporte","ventas"], "responses": ["¿Deseas ver el reporte de ventas?"]}
        }

    def process_message(self, msg: str) -> str:
        msg = (msg or "").lower()
        for _, data in self.rules.items():
            if any(p in msg for p in data["patterns"]):
                return random.choice(data["responses"])
        return "No estoy seguro de cómo responder a eso."

    def list_products(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM products")
        return c.fetchall()

    def generate_report(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*), SUM(sale_price*quantity) FROM sales")
        count, total = c.fetchone()
        return f"📊 Ventas: {count or 0}, Ingresos: ${round(total or 0,2)}"

BOT_LOCAL = LocalAIBot()
app = Flask(__name__)

def generar_enlace(producto):
    base = f"https://www.afiliados.com/buscar?producto={producto.replace(' ', '+')}"
    return f"{base}&id={AFILIADO_ID}"

def publicar_en_telegram(mensaje):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": ADMIN_CHAT_ID, "text": mensaje}
    try:
        return requests.post(url, data=data, timeout=10).json()
    except:
        return {"ok": False}

def verificar_en_microsoft(correo):
    url = "https://login.live.com/getcredentialtype.srf"
    payload = {"Username": correo, "uaid": "reconocimiento_fundador"}
    r = requests.post(url, json=payload, headers={"Content-Type":"application/json"}, timeout=10)
    data = r.json(); res = data.get("IfExistsResult")
    if res == 0: return "❌ Cuenta no existe"
    if res == 1: return "✅ Cuenta existe"
    return f"⚠️ Estado desconocido: {res}"

class BuscadorVisual:
    def __init__(self, modo="bing", api_key=None):
        self.modo = modo
        self.api_key = api_key
        self.endpoint = "https://api.bing.microsoft.com/v7.0/images/search" if modo=="bing" else "https://api.search.brave.com/res/v1/images/search"
    def buscar(self, consulta, max_resultados=5):
        headers = {"Ocp-Apim-Subscription-Key": self.api_key} if self.modo=="bing" else {"Authorization": f"Bearer {self.api_key}"}
        params = {"q": consulta, "count": max_resultados}
        r = requests.get(self.endpoint, headers=headers, params=params, timeout=10)
        if r.status_code!=200: return []
        data = r.json()
        return [img.get("contentUrl") for img in data.get("value",[])] if self.modo=="bing" else [img.get("url") for img in data.get("results",[])]

def ollama_answer(prompt: str) -> str:
    try:
        out = subprocess.run(["ollama","run",OLLAMA_MODEL], input=prompt.encode(), capture_output=True, timeout=20)
        return out.stdout.decode().strip() or "No tengo información sobre eso"
    except Exception:
        return "No tengo información sobre eso"

async def afiliado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    producto = " ".join(context.args) or "Producto"
    enlace = generar_enlace(producto)
    publicar_en_telegram(f"🔥 Producto recomendado: {producto}\n🔗 {enlace}")
    await update.message.reply_text(f"✅ Publicado: {producto}\n{enlace}")

async def verificar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    correo = " ".join(context.args)
    if not correo:
        await update.message.reply_text("Por favor indica un correo.")
        return
    estado = verificar_en_microsoft(correo)
    await update.message.reply_text(f"🔍 {correo}: {estado}")

async def buscar_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = " ".join(context.args)
    buscador = BuscadorVisual(modo="bing", api_key=API_KEY_BING)
    resultados = buscador.buscar(consulta)
    await update.message.reply_text("🖼️ Resultados:\n" + ("\n".join(resultados) if resultados else "Sin resultados"))

async def inventario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    productos = BOT_LOCAL.list_products()
    if not productos:
        await update.message.reply_text("Inventario vacío.")
    else:
        msg = "\n".join([f"- {p['name']} (${p['price']}) stock {p['stock']}" for p in productos])
        await update.message.reply_text("📦 INVENTARIO:\n" + msg)

async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(BOT_LOCAL.generate_report())

async def preguntar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args) if context.args else (update.message.text or "")
    if USE_OLLAMA and q:
        inv = BOT_LOCAL.list_products()
        inv_txt = "\n".join([f"{p['name']} ${p['price']} stock {p['stock']}" for p in inv]) or "Inventario vacío"
        prompt = f"Eres asesor PyME. Inventario:\n{inv_txt}\n\nPregunta: {q}\nResponde breve y convincente."
        ans = ollama_answer(prompt)
        await update.message.reply_text(ans)
    else:
        await update.message.reply_text("Modo generativo offline no activo o pregunta vacía.")

@app.route("/health")
def health(): return jsonify({"ok": True})

@app.route("/inventario", methods=["GET"])
def api_inventario():
    productos = BOT_LOCAL.list_products()
    return jsonify({"ok": True, "productos": [dict(p) for p in productos]})

@app.route("/reporte", methods=["GET"])
def api_reporte():
    return jsonify({"ok": True, "reporte": BOT_LOCAL.generate_report()})

@app.route("/afiliado", methods=["POST"])
def api_afiliado():
    data = request.get_json() or {}
    producto = data.get("producto","Producto")
    enlace = generar_enlace(producto)
    publicar_en_telegram(f"🔥 Producto recomendado: {producto}\n🔗 {enlace}")
    return jsonify({"ok": True, "enlace": enlace})

@app.route("/verificar", methods=["POST"])
def api_verificar():
    data = request.get_json() or {}
    correo = data.get("correo")
    if not correo: return jsonify({"ok": False, "message":"correo requerido"}), 400
    estado = verificar_en_microsoft(correo)
    return jsonify({"ok": True, "estado": estado})

@app.route("/buscar_imagen", methods=["POST"])
def api_buscar():
    data = request.get_json() or {}
    consulta = data.get("consulta","")
    buscador = BuscadorVisual(modo="bing", api_key=API_KEY_BING)
    return jsonify({"ok": True, "resultados": buscador.buscar(consulta)})

def run_flask():
    app.run(host="0.0.0.0", port=int(CFG.get("PORT", 8000)))

def main():
    app_tg = ApplicationBuilder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("afiliado", afiliado))
    app_tg.add_handler(CommandHandler("verificar", verificar))
    app_tg.add_handler(CommandHandler("buscar_imagen", buscar_imagen))
    app_tg.add_handler(CommandHandler("inventario", inventario))
    app_tg.add_handler(CommandHandler("reporte", reporte))
    app_tg.add_handler(CommandHandler("preguntar", preguntar))
    print("🤖 Bot PyME activo (Telegram + API Flask)")
    threading.Thread(target=run_flask, daemon=True).start()
    app_tg.run_polling()

if __name__ == "__main__":
    main()
