import streamlit as st
from supabase import create_client, Client
import pandas as pd

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        # Sanitize URL to prevent PGRST125 Invalid path errors
        # If the user included /rest/v1 in the URL, remove it since create_client appends it.
        url = url.rstrip('/')
        if url.endswith('/rest/v1'):
            url = url[:-8]
            
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de configuração do Supabase: {e}. Verifique o arquivo .streamlit/secrets.toml.")
        return None

def fetch_all_data():
    supabase = init_connection()
    if not supabase: return pd.DataFrame()
    response = supabase.table("extrato").select("*").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def fetch_pending_data():
    supabase = init_connection()
    if not supabase: return pd.DataFrame()
    response = supabase.table("extrato").select("*").eq("categoria", "Pendente").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

def insert_record(data_dict):
    supabase = init_connection()
    if not supabase: return False
    # data_dict chaves devem corresponder exatamente aos nomes das colunas no Supabase.
    try:
        response = supabase.table("extrato").insert(data_dict).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao inserir: {e}")
        return False

def check_duplicate(data_date, entrada_saida, tipo, detalhes, valor):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("extrato").select("id").eq("data", data_date)\
            .eq("entrada_saida", entrada_saida).eq("tipo", tipo)\
            .eq("detalhes", detalhes).eq("valor", valor).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao checar duplicidade: {e}")
        return False

def update_category_description(record_id, category, description):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("extrato").update({
            "categoria": category, 
            "descricao": description
        }).eq("id", record_id).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False
