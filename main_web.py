# main_web.py
import os, json, requests
from datetime import datetime
from flask import Flask, request, jsonify
from supabase import create_client

# Entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MP_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

def verificar_pago_mp(payload):
    data = payload.get("data", {})
    payment_id = data.get("id")
    if not payment_id:
        return False, "ID de pago no encontrado"

    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    r = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers, timeout=10)
    if r.status_code != 200:
        return False, "Error al verificar pago"

    pago = r.json()
    status = pago.get("status")
    amount = pago.get("transaction_amount", 0)
    description = pago.get("description", "")

    if status == "approved" and round(amount) == 499 and "chatbot" in (description or "").lower():
        return True, {
            "user_id": pago.get("payer", {}).get("id"),
            "email": pago.get("payer", {}).get("email"),
            "nicho": description.replace("Chatbot de ", "").strip()
        }
    return False, f"Pago no válido: {status}, ${amount}"

def procesar_pago_exitoso(datos_pago):
    nicho = datos_pago["nicho"]
    email = datos_pago["email"]
    # Aquí invocarías tu fábrica de chatbots; se deja registro en Supabase:
    supabase.table("ventas_chatbots").insert({
        "email": email,
        "nicho": nicho,
        "estado": "entregado",
        "timestamp": datetime.now().isoformat()
    }).execute()
    return True

@app.route("/webhook/mercadopago", methods=["POST"])
def webhook_mercadopago():
    payload = request.get_json() or {}
    es_valido, datos = verificar_pago_mp(payload)
    if es_valido:
        procesar_pago_exitoso(datos)
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": str(datos)}), 400

@app.route("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now().isoformat()})
