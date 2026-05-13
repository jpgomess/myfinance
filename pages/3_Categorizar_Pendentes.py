import streamlit as st
import pandas as pd
from utils.db import fetch_pending_data, update_category_description

st.set_page_config(page_title="Categorizar Pendentes", page_icon="🏷️", layout="wide")
st.title("Categorizar Lançamentos Pendentes")

st.markdown("""
Use a tabela abaixo para categorizar rapidamente os itens importados do extrato.
""")

df_pendentes = fetch_pending_data()

if df_pendentes.empty:
    st.success("🎉 Não há lançamentos pendentes de categorização!")
else:
    st.info(f"Você tem {len(df_pendentes)} lançamentos para categorizar.")
    
    # Preparar DataFrame para edição (apenas colunas de interesse)
    # Certificando-se de que a coluna ID está presente para atualização
    colunas_edicao = ['id', 'data', 'entrada_saida', 'tipo', 'detalhes', 'valor', 'categoria', 'descricao']
    editor_df = df_pendentes[colunas_edicao].copy()
    
    categorias_opcoes = ["Transporte", "Lazer", "Casa", "Alimentação", "Saúde", "Educação", "Outros", "Pendente"]
    
    # Configurar as colunas do data_editor
    column_config = {
        "id": None,  # Ocultar a coluna ID
        "data": st.column_config.DateColumn("Data", disabled=True),
        "entrada_saida": st.column_config.TextColumn("Entrada/Saída", disabled=True),
        "tipo": st.column_config.TextColumn("Tipo", disabled=True),
        "detalhes": st.column_config.TextColumn("Detalhes", disabled=True),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", disabled=True),
        "categoria": st.column_config.SelectboxColumn("Categoria", options=categorias_opcoes, required=True),
        "descricao": st.column_config.TextColumn("Descrição")
    }
    
    with st.form("categorize_form"):
        edited_df = st.data_editor(
            editor_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
            key="pendentes_editor"
        )
        
        submitted = st.form_submit_button("Salvar Alterações")
        
        if submitted:
            changes_made = 0
            errors = 0
            
            # Comparar alterações
            for idx, row in edited_df.iterrows():
                original_row = editor_df.iloc[idx]
                
                # Se a categoria mudou (deixou de ser pendente) ou se adicionou uma descrição
                if row['categoria'] != original_row['categoria'] or row['descricao'] != original_row['descricao']:
                    success = update_category_description(row['id'], row['categoria'], row['descricao'])
                    if success:
                        changes_made += 1
                    else:
                        errors += 1
            
            if changes_made > 0:
                if errors == 0:
                    st.success(f"{changes_made} lançamentos atualizados com sucesso!")
                else:
                    st.warning(f"{changes_made} lançamentos atualizados. {errors} falharam.")
                # Rerun para atualizar a tabela de pendentes
                st.rerun()
            else:
                if errors > 0:
                    st.error("Erro ao tentar salvar alterações.")
                else:
                    st.info("Nenhuma alteração detectada para salvar.")
