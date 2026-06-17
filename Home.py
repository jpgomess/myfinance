import plotly.express as px
import streamlit as st
import pandas as pd

from utils.db import fetch_all_data, delete_records, fetch_accounts_data, fetch_categories, fetch_accounts, update_extrato_record

st.set_page_config(page_title="MyFinance Dashboard", page_icon="💰", layout="wide")

st.title("MyFinance - Dashboard Financeiro")

df = fetch_all_data()

if df.empty:
    st.info("Nenhum dado encontrado no banco. Comece adicionando registros manualmente ou importando um extrato.")
else:
    # Converter tipos caso venham como string do BD
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.date
    
    # 1) Remover coluna created_at
    if 'created_at' in df.columns:
        df = df.drop(columns=['created_at'])
    
    # Guardar cópia original para detectar mudanças
    df_original = df.copy()
    
    # 2 e 3) Configuração visual para renomear e formatar as colunas
    categorias_opcoes = fetch_categories() or ["Sem Categoria"]
    contas_opcoes = fetch_accounts() or ["Sem Conta"]
    base_column_config = {
        "id": None, # Ocultar ID
        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
        "entrada_saida": st.column_config.SelectboxColumn("Entrada/Saída", options=["Entrada", "Saída"]),
        "tipo": st.column_config.TextColumn("Tipo"),
        "detalhes": st.column_config.TextColumn("Detalhes"),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0.0),
        "conta": st.column_config.SelectboxColumn("Conta", options=contas_opcoes),
        "categoria": st.column_config.SelectboxColumn("Categoria", options=categorias_opcoes),
        "descricao": st.column_config.TextColumn("Descrição")
    }

    # Calcular Resumo
    total_entradas = df[df['entrada_saida'] == 'Entrada']['valor'].sum()
    total_saidas = df[df['entrada_saida'] == 'Saída']['valor'].sum()
    
    accounts_data = fetch_accounts_data()
    total_saldo_inicial = sum(float(acc.get('saldo_inicial') or 0.0) for acc in accounts_data)
    
    saldo = total_entradas - total_saidas + total_saldo_inicial
    
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
            df_original.sort_values(by="data", ascending=False).head(20),
            width="stretch",
            column_config=base_column_config,
            hide_index=True
        )

    st.markdown("---")
    st.subheader("Todos os Lançamentos")
    
    edited_df = st.data_editor(
        df,
        hide_index=True,
        column_config=base_column_config,
        num_rows="dynamic",
        width='stretch',
        key="main_editor"
    )
    
    has_changes = not edited_df.equals(df_original)

    if has_changes:
        if st.button("Salvar Alterações", type='primary'):
            success = True
            # Lida com valores nulos que podem quebrar a comparação
            df_original_compare = df_original.fillna("").astype(str)
            edited_df_compare = edited_df.fillna("").astype(str)

            # Deletions
            original_ids = set(df_original_compare['id'])
            edited_ids = set(edited_df_compare['id'])
            deleted_ids = [int(id_str) for id_str in (original_ids - edited_ids)]
            if deleted_ids:
                if not delete_records(deleted_ids): success = False

            # Additions and Updates
            for _, row in edited_df.iterrows():
                row_id = row.get('id')
                # Garante que a linha não está vazia
                if pd.isna(row_id) and row.notna().sum() > 1:
                    st.warning("Novos lançamentos devem ser adicionados pela página 'Lançamento' para garantir a integridade. A linha adicionada foi ignorada.")
                    continue
                
                if pd.notna(row_id):
                    original_row = df_original_compare[df_original_compare['id'] == str(int(row_id))]
                    if not original_row.empty and not original_row.iloc[0].equals(row.fillna("").astype(str)):
                        update_dict = {
                            "data": pd.to_datetime(row['data']).strftime("%Y-%m-%d"),
                            "entrada_saida": row['entrada_saida'],
                            "tipo": row['tipo'],
                            "detalhes": row['detalhes'],
                            "valor": float(row['valor']) if row['valor'] else 0.0,
                            "conta": row['conta'],
                            "categoria": row['categoria'],
                            "descricao": row['descricao']
                        }
                        if not update_extrato_record(int(row_id), update_dict): success = False
            if success:
                st.success("Lançamentos atualizados com sucesso!")
                st.rerun()
            else:
                st.error("Ocorreu um erro ao atualizar os lançamentos.")
