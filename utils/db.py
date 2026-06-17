import streamlit as st
from supabase import create_client, Client
import pandas as pd

@st.cache_resource
def init_connection() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
            
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro de configuração do Supabase: {e}. Verifique o arquivo .streamlit/secrets.toml.")
        return None

def fetch_all_data():
    supabase = init_connection()
    if not supabase: return pd.DataFrame()
    response = supabase.table("extrato").select("*").order("data", desc=True).execute()
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

def delete_records(record_ids):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("extrato").delete().in_("id", record_ids).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao remover registros: {e}")
        return False

def update_extrato_record(record_id, data_dict):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("extrato").update(data_dict).eq("id", record_id).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao atualizar registro: {e}")
        return False

def fetch_categories():
    supabase = init_connection()
    if not supabase: return []
    try:
        response = supabase.table("categorias").select("nome").order("nome").execute()
        if response.data:
            return [item['nome'] for item in response.data]
        return []
    except Exception as e:
        st.error(f"Erro ao buscar categorias: {e}")
        return []

def insert_category(nome):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("categorias").insert({"nome": nome}).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao inserir categoria: {e}")
        return False

def delete_category(nome):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("categorias").delete().eq("nome", nome).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao remover categoria: {e}")
        return False

def rename_category(old_nome, new_nome):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("categorias").update({"nome": new_nome}).eq("nome", old_nome).execute()
        if len(response.data) > 0:
            supabase.table("extrato").update({"categoria": new_nome}).eq("categoria", old_nome).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao renomear categoria: {e}")
        return False

def fetch_accounts():
    supabase = init_connection()
    if not supabase: return []
    try:
        response = supabase.table("contas").select("nome").order("nome").execute()
        if response.data:
            return [item['nome'] for item in response.data]
        return []
    except Exception as e:
        st.error(f"Erro ao buscar contas: {e}")
        return []

def fetch_accounts_data():
    supabase = init_connection()
    if not supabase: return []
    try:
        response = supabase.table("contas").select("*").order("nome").execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        st.error(f"Erro ao buscar dados das contas: {e}")
        return []

def insert_account(nome, tipo="Conta Corrente", saldo_inicial=0.0):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("contas").insert({"nome": nome, "tipo": tipo, "saldo_inicial": saldo_inicial}).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao inserir conta: {e}")
        return False

def delete_account(nome):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("contas").delete().eq("nome", nome).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Erro ao remover conta: {e}")
        return False

def update_account(old_nome, new_nome, saldo_inicial):
    supabase = init_connection()
    if not supabase: return False
    try:
        response = supabase.table("contas").update({"nome": new_nome, "saldo_inicial": saldo_inicial}).eq("nome", old_nome).execute()
        if len(response.data) > 0:
            if old_nome != new_nome:
                supabase.table("extrato").update({"conta": new_nome}).eq("conta", old_nome).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar conta: {e}")
        return False
