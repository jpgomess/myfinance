import streamlit as st
import pandas as pd
import datetime
import sys
import os
import warnings

utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if utils_path not in sys.path:
    sys.path.append(utils_path)

# Suprimir avisos inofensivos de estilo do openpyxl ao ler planilhas
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

from utils.db import insert_record, check_duplicate, fetch_categories, fetch_accounts
from utils.bb_proc import process_bb_file

st.set_page_config(page_title="MyFinance-Lançamento", page_icon="📝")
st.title("Adicionar Lançamento")

# Buscar categorias dinâmicas
categorias_opcoes = fetch_categories()

# Buscar contas dinâmicas
contas_opcoes = fetch_accounts()
if not contas_opcoes: contas_opcoes = ["Conta Padrão"]

tab1, tab2 = st.tabs(["Manual", "Importar Extrato"])

with tab1:
    with st.form("manual_entry_form"):
        col1, col2, col3, col4 = st.columns(4)
        data = col1.date_input("Data", datetime.date.today())
        entrada_saida = col2.selectbox("Entrada/Saída", ["Entrada", "Saída"])
        tipo = col3.text_input("Tipo")
        detalhes = col4.text_input("Detalhes")

        col1, col2, col3, col4 = st.columns(4)
        valor = col1.number_input("Valor", min_value=0.01, format="%.2f")
        conta = col2.selectbox("Conta", contas_opcoes)
        categoria = col3.selectbox("Categoria", categorias_opcoes)
        descricao = col4.text_input("Descrição")
        
        submitted = st.form_submit_button("Salvar Registro")
        
        if submitted:
            data_dict = {
                "data": data.strftime("%Y-%m-%d"),
                "entrada_saida": entrada_saida,
                "tipo": tipo,
                "detalhes": detalhes,
                "valor": float(valor),
                "conta": conta,
                "categoria": categoria,
                "descricao": descricao
            }
            
            if insert_record(data_dict):
                st.success("Registro adicionado com sucesso!")
            else:
                st.error("Erro ao adicionar registro. Verifique a conexão com o banco ou os nomes das colunas.")

with tab2:
    conta_import = st.selectbox("Selecione a Conta deste extrato:", contas_opcoes)

    if conta_import == "Banco do Brasil":
        st.markdown("""
        **Formato Esperado (Banco do Brasil):**
        O arquivo CSV deve conter pelo menos as colunas: `Data`, `Lançamento`, `Detalhes`, `Valor`, `Tipo Lançamento`.
        """)

    uploaded_file = st.file_uploader("Escolha um arquivo CSV ou Excel", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        try:
            # Lendo o arquivo com suporte a múltiplas codificações (UTF-8 e Latin-1)
            def load_csv(file_obj):
                file_obj.seek(0)
                try:
                    df_temp = pd.read_csv(file_obj, sep=';', encoding='utf-8')
                    if len(df_temp.columns) <= 1:
                        file_obj.seek(0)
                        df_temp = pd.read_csv(file_obj, sep=',', encoding='utf-8')
                    return df_temp
                except UnicodeDecodeError:
                    file_obj.seek(0)
                    df_temp = pd.read_csv(file_obj, sep=';', encoding='latin-1')
                    if len(df_temp.columns) <= 1:
                        file_obj.seek(0)
                        df_temp = pd.read_csv(file_obj, sep=',', encoding='latin-1')
                    return df_temp

            if uploaded_file.name.lower().endswith('.csv'):
                df = load_csv(uploaded_file)
            else:
                try:
                    df = pd.read_excel(uploaded_file)
                except Exception as read_ex:
                    # Em alguns casos, arquivos de bancos são CSVs com a extensão .xls ou .xlsx
                    try:
                        df = load_csv(uploaded_file)
                    except Exception:
                        raise read_ex
                
            with st.expander("Mostrar Dados Originais"):
                st.dataframe(df)
            
            df_parsed = process_bb_file(df)
                
            # Preparar dataframe final (reordenação e renomeio p/ banco de dados)
            df_final = pd.DataFrame({
                'data': df_parsed['Data'],
                'entrada_saida': df_parsed['entrada_saida'],
                'tipo': df_parsed['Tipo'],
                'detalhes': df_parsed['Detalhes'],
                'valor': df_parsed['Valor'],
                'categoria': "",
                'descricao': ''
            })
            
            st.info("Categorize os lançamentos para enviar")
            
            column_config = {
                "data": st.column_config.TextColumn("Data", disabled=True),
                "entrada_saida": st.column_config.TextColumn("Entrada/Saída", disabled=True),
                "tipo": st.column_config.TextColumn("Tipo", disabled=True),
                "detalhes": st.column_config.TextColumn("Detalhes", disabled=True),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", disabled=True),
                "categoria": st.column_config.SelectboxColumn("Categoria", options=categorias_opcoes, required=True),
                "descricao": st.column_config.TextColumn("Descrição")
            }
            
            edited_df = st.data_editor(
                df_final,
                column_config=column_config,
                hide_index=True,
                width='stretch',
                key="import_editor"
            )
            
            if st.button("Enviar"):
                # Converte o texto DD/MM/YYYY do visualizador de volta para o formato de banco YYYY-MM-DD
                edited_df["data"] = pd.to_datetime(edited_df["data"], format="%d/%m/%Y", errors="coerce").dt.strftime("%Y-%m-%d")
                
                # Trata os valores vazios (NaN) gerados pelo Pandas, que quebram o JSON do Supabase
                edited_df = edited_df.fillna("")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                inserted = 0
                duplicates = 0
                errors = 0
                total = len(edited_df)
                
                if total == 0:
                    st.warning("Não há lançamentos para processar.")
                
                for i, (idx, row) in enumerate(edited_df.iterrows()):
                    row_dict = row.to_dict()
                    row_dict['conta'] = conta_import
                    
                    # Lógica de Deduplicação
                    is_dup = check_duplicate(
                        row_dict['data'], 
                        row_dict['entrada_saida'], 
                        row_dict['tipo'], 
                        row_dict['detalhes'], 
                        row_dict['valor']
                    )
                    
                    if is_dup:
                        duplicates += 1
                    else:
                        # Inserção
                        success = insert_record(row_dict)
                        if success:
                            inserted += 1
                        else:
                            errors += 1
                    
                    progress_bar.progress((i + 1) / total)
                    status_text.text(f"Processando: {i+1}/{total}")
                
                st.success(f"Importação concluída! Inseridos: {inserted}, Duplicados ignorados: {duplicates}, Erros: {errors}")

        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
