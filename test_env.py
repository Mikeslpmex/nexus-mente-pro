from dotenv import load_dotenv
import os
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ Variables faltantes")
else:
    print(f"✅ SUPABASE_URL cargada: {url[:30]}...")
    print(f"✅ SUPABASE_KEY cargada: {'*' * len(key)}")
    try:
        from supabase import create_client
        supabase = create_client(url, key)
        print("✅ Conexión a Supabase: OK")
    except Exception as e:
        print(f"❌ Error Supabase: {e}")
