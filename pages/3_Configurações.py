import streamlit as st
import sys
import os

utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if utils_path not in sys.path:
    sys.path.append(utils_path)

import pandas as pd
from utils.db import fetch_categories, insert_category, delete_category, rename_category, fetch_accounts_data, insert_account, update_account, delete_account

st.set_page_config(page_title="MyFinance-Configurações", page_icon="⚙️")
st.title("Configurações")

tab1, tab2 = st.tabs(["Gerenciar Categorias", "Gerenciar Contas"])

with tab1:
    st.header("Categorias")
    categorias_opcoes = fetch_categories()
    df_categorias = pd.DataFrame(categorias_opcoes, columns=["nome"])
    df_categorias_original = df_categorias.copy()
    
    edited_df_cat = st.data_editor(
        df_categorias,
        num_rows="dynamic",
        width='stretch',
        column_config={"nome": st.column_config.TextColumn("Nome da Categoria", required=True)}
    )

    has_changes_cat = not edited_df_cat.equals(df_categorias_original)

    if has_changes_cat:
        if st.button(label="Salvar Alterações", key="save_cat", type="primary"):
            success = True
            # Deletions
            deleted_indices = set(df_categorias_original.index) - set(edited_df_cat.index)
            for idx in deleted_indices:
                cat_to_delete = df_categorias_original.loc[idx]['nome']
                if not delete_category(cat_to_delete): success = False

            # Additions and Updates
            for idx, row in edited_df_cat.iterrows():
                if idx in df_categorias_original.index: # Update
                    original_row = df_categorias_original.loc[idx]
                    if not original_row.equals(row):
                        if not rename_category(original_row['nome'], row['nome']): success = False
                else: # Addition
                    if not insert_category(row['nome']): success = False
            
            if success:
                st.success("Categorias atualizadas com sucesso!")
                st.rerun()
            else:
                st.error("Ocorreu um erro ao atualizar as categorias.")

with tab2:
    st.header("Contas")
    accounts_data = fetch_accounts_data()
    df_contas = pd.DataFrame(accounts_data)[["nome", "tipo", "saldo_inicial"]] if accounts_data else pd.DataFrame(columns=["nome", "tipo", "saldo_inicial"])
    df_contas_original = df_contas.copy()

    edited_df_acc = st.data_editor(
        df_contas,
        num_rows="dynamic",
        width='stretch',
        column_config={
            "nome": st.column_config.TextColumn("Nome da Conta", required=True),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["Conta Corrente", "Cartão de Crédito", "Benefício", "Outro"], required=True),
            "saldo_inicial": st.column_config.NumberColumn("Saldo Inicial", format="R$ %.2f", required=True)
        }
    )
    
    has_changes_acc = not edited_df_acc.equals(df_contas_original)

    if has_changes_acc:
        if st.button("Salvar Alterações", key="save_acc", type="primary"):
            success = True
            # Deletions
            deleted_indices = set(df_contas_original.index) - set(edited_df_acc.index)
            for idx in deleted_indices:
                acc_to_delete = df_contas_original.loc[idx]['nome']
                if not delete_account(acc_to_delete): success = False

            # Additions and Updates
            for idx, row in edited_df_acc.iterrows():
                row = row.fillna(0) # Saldo inicial pode ser NaN se adicionado e não preenchido
                if idx in df_contas_original.index: # Update
                    original_row = df_contas_original.loc[idx]
                    if not original_row.equals(row):
                        if not update_account(original_row['nome'], row['nome'], float(row['saldo_inicial'])): success = False
                else: # Addition
                    if not insert_account(row['nome'], row['tipo'], float(row['saldo_inicial'])): success = False

            if success:
                st.success("Contas atualizadas com sucesso!")
                st.rerun()
            else:
                st.error("Ocorreu um erro ao atualizar as contas.")