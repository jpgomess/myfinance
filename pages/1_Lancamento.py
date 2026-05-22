import streamlit as st
import pandas as pd
import datetime
from utils.db import insert_record, check_duplicate

st.set_page_config(page_title="MyFinance-Lançamento", page_icon="📝")
st.title("Adicionar Lançamento")

tab1, tab2 = st.tabs(["Manual", "Importar Extrato"])

with tab1:
    with st.form("manual_entry_form"):
        col1, col2, col3, col4 = st.columns(4)
        data = col1.date_input("Data", datetime.date.today())
        entrada_saida = col2.selectbox("Entrada/Saída", ["Entrada", "Saída"])
        tipo = col3.text_input("Tipo")
        detalhes = col4.text_input("Detalhes")

        col1, col2, col3 = st.columns([1,1,2])
        valor = col1.number_input("Valor", min_value=0.01, format="%.2f")
        categoria = col2.selectbox("Categoria", ["Transporte", "Lazer", "Casa", "Alimentação", "Saúde", "Educação", "Outros", "Pendente"])
        descricao = col3.text_input("Descrição")
        
        submitted = st.form_submit_button("Salvar Registro")
        
        if submitted:
            data_dict = {
                "data": data.strftime("%Y-%m-%d"),
                "entrada_saida": entrada_saida,
                "tipo": tipo,
                "detalhes": detalhes,
                "valor": float(valor),
                "categoria": categoria,
                "descricao": descricao
            }
            
            if insert_record(data_dict):
                st.success("Registro adicionado com sucesso!")
            else:
                st.error("Erro ao adicionar registro. Verifique a conexão com o banco ou os nomes das colunas.")

with tab2:
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
                st.dataframe(df.head())
            
            # Colunas requeridas pelo extrato original
            required_cols = ['Data', 'Lançamento', 'Detalhes', 'Valor', 'Tipo Lançamento']
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Faltam as seguintes colunas no arquivo: {', '.join(missing_cols)}")
            else:
                # Processamento
                df_parsed = df[required_cols].copy()
                df_parsed = df_parsed.rename(columns={
                    'Lançamento': 'Tipo',
                    'Tipo Lançamento': 'Entrada_Saida_Raw'
                })
                
                # Formatar Data
                df_parsed['Data'] = pd.to_datetime(df_parsed['Data'], errors='coerce', dayfirst=True)
                df_parsed = df_parsed.dropna(subset=['Data'])
                df_parsed['Data'] = df_parsed['Data'].dt.strftime('%Y-%m-%d')
                
                # Limpar e converter Valor
                if df_parsed['Valor'].dtype == 'object':
                    df_parsed['Valor'] = df_parsed['Valor'].astype(str).str.replace(r'[R$\s]', '', regex=True)
                    df_parsed['Valor'] = df_parsed['Valor'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                
                df_parsed['Valor_Num'] = pd.to_numeric(df_parsed['Valor'], errors='coerce')
                df_parsed = df_parsed.dropna(subset=['Valor_Num'])
                
                # Lógica para definir Entrada/Saída e Valor absoluto
                def get_entrada_saida(row):
                    val = row['Valor_Num']
                    raw_type = str(row['Entrada_Saida_Raw']).upper()
                    if 'D' in raw_type or val < 0:
                        return 'Saída'
                    elif 'C' in raw_type or val > 0:
                        return 'Entrada'
                    return 'Saída'
                    
                df_parsed['entrada_saida'] = df_parsed.apply(get_entrada_saida, axis=1)
                df_parsed['valor'] = df_parsed['Valor_Num'].abs()
                
                # Preparar dataframe final (reordenação e renomeio p/ banco de dados)
                df_final = pd.DataFrame({
                    'data': df_parsed['Data'],
                    'entrada_saida': df_parsed['entrada_saida'],
                    'tipo': df_parsed['Tipo'],
                    'detalhes': df_parsed['Detalhes'],
                    'valor': df_parsed['valor'],
                    'categoria': '',
                    'descricao': ''
                })
                
                st.subheader("Categorize os Lançamentos Antes da Importação")
                
                categorias_opcoes = sorted(["Transporte", "Lazer", "Casa", "Mercado", "Saúde", "Educação", "Outros"])
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
                
                if st.button("Confirmar Importação no Supabase"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    inserted = 0
                    duplicates = 0
                    errors = 0
                    total = len(edited_df)
                    
                    for idx, row in edited_df.iterrows():
                        # Lógica de Deduplicação
                        is_dup = check_duplicate(
                            row['data'], 
                            row['entrada_saida'], 
                            row['tipo'], 
                            row['detalhes'], 
                            row['valor']
                        )
                        
                        if is_dup:
                            duplicates += 1
                        else:
                            # Inserção
                            success = insert_record(row.to_dict())
                            if success:
                                inserted += 1
                            else:
                                errors += 1
                        
                        progress_bar.progress((idx + 1) / total)
                        status_text.text(f"Processando: {idx+1}/{total}")
                    
                    st.success(f"Importação concluída! Inseridos: {inserted}, Duplicados ignorados: {duplicates}, Erros: {errors}")

        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")
