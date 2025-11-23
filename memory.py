from supabase import create_client, Client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

def registrar_oportunidad(data):
    response = supabase.table("oportunidades").insert(data).execute()
    return response

def registrar_venta(data):
    response = supabase.table("ventas").insert(data).execute()
    return response
