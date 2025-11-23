#!/bin/bash
echo "🔧 Auto-reparando nexus-mente-pro..."

# 1. Crea .env si no existe
[ -f .env ] || { echo "CREA TU .env primero con: nano .env"; exit 1; }

# 2. Instala dependencias
pip install -r requirements.txt python-dotenv supabase python-telegram-bot

# 3. Valida sintaxis de main.py
echo "🔍 Checando sintaxis..."
if python -m py_compile main.py; then
  echo "✅ main.py OK"
else
  echo "❌ Error en main.py — edítalo con: nano main.py"
  exit 1
fi

# 4. Prueba conexión a Supabase
python test_env.py

echo "✅ Listo. Ejecuta: python main.py"
