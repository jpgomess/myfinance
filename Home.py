import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db import fetch_all_data

st.set_page_config(page_title="MyFinance Dashboard", page_icon="💰", layout="wide")

st.title("MyFinance - Dashboard Financeiro")

df = fetch_all_data()

if df.empty:
    st.info("Nenhum dado encontrado no banco. Comece adicionando registros manualmente ou importando um extrato.")
else:
    # Converter tipos caso venham como string do BD
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    
    # Calcular Resumo
    total_entradas = df[df['entrada_saida'] == 'Entrada']['valor'].sum()
    total_saidas = df[df['entrada_saida'] == 'Saída']['valor'].sum()
    saldo = total_entradas - total_saidas
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas", f"R$ {total_entradas:,.2f}")
    col2.metric("Saídas", f"R$ {total_saidas:,.2f}")
    col3.metric("Saldo", f"R$ {saldo:,.2f}")
    
    st.markdown("---")
    
    col_chart, col_data = st.columns([1, 1])
    
    with col_chart:
        st.subheader("Despesas por Categoria")
        # Filtrar apenas saídas e ignorar categoria Pendente no gráfico se desejar (aqui mostraremos todas as saídas)
        df_saidas = df[df['entrada_saida'] == 'Saída']
        if not df_saidas.empty:
            df_grouped = df_saidas.groupby("categoria")['valor'].sum().reset_index()
            fig = px.pie(df_grouped, values='valor', names='categoria', hole=0.4)
            st.plotly_chart(fig, width="stretch")
        else:
            st.write("Nenhuma saída registrada para exibir no gráfico.")
            
    with col_data:
        st.subheader("Histórico Recente")
        st.dataframe(
            df.sort_values(by="data", ascending=False).drop(columns=['id'], errors='ignore').head(20),
            width="stretch"
        )

    st.markdown("---")
    st.subheader("Todos os Lançamentos")
    st.dataframe(df.sort_values(by="data", ascending=False).drop(columns=['id'], errors='ignore'), width="stretch")
