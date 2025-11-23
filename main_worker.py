# main_worker.py
import os, json, sqlite3, random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
AFILIADO_ID = os.getenv("AFILIADO_ID", "CHMI3457849")

class Inventory:
    def __init__(self, db="local_inventory.db"):
        self.conn = sqlite3.connect(db)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, price REAL, stock INTEGER,
            description TEXT, sku TEXT UNIQUE, platform TEXT)""")
        self.conn.commit()

    def list(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM products")
        return c.fetchall()

INV = Inventory()

def generar_enlace(producto):
    base = f"https://www.afiliados.com/buscar?producto={producto.replace(' ', '+')}"
    return f"{base}&id={AFILIADO_ID}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot PyME activo. Usa /inventario, /afiliado <producto>.")

async def inventario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods = INV.list()
    if not prods:
        await update.message.reply_text("Inventario vacío.")
        return
    msg = "\n".join([f"- {p['name']} (${p['price']}) stock {p['stock']}" for p in prods])
    await update.message.reply_text("📦 INVENTARIO:\n" + msg)

async def afiliado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    producto = " ".join(context.args) or "Producto"
    await update.message.reply_text(f"🔗 Enlace afiliado: {generar_enlace(producto)}")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Comando no reconocido. Prueba /inventario o /afiliado <producto>.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("inventario", inventario))
    app.add_handler(CommandHandler("afiliado", afiliado))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()

if __name__ == "__main__":
    main()
