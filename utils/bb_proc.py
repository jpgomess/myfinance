import streamlit as st
import pandas as pd
import numpy as np

def process_bb_file(df):
    # Colunas requeridas pelo extrato original
    required_cols = ['Data', 'Lançamento', 'Detalhes', 'Valor', 'Tipo Lançamento']

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Faltam as seguintes colunas no arquivo: {', '.join(missing_cols)}")
    else:
        # Renomear colunas
        df_parsed = df[required_cols].copy()
        df_parsed = df_parsed.rename(columns={
            'Lançamento': 'Tipo',
            'Tipo Lançamento': 'entrada_saida'
        })

        # Excluir linhas indesejadas
        df_parsed = df_parsed[df_parsed["entrada_saida"] != " "]
        
        # Formatar Data
        df_parsed['Data'] = pd.to_datetime(df_parsed['Data'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y')
        
        # Formatar Valor
        df_parsed['Valor'] = df_parsed["Valor"].str.replace(".", "").str.replace(",", ".", regex=True)
        df_parsed['Valor'] = pd.to_numeric(df_parsed['Valor'], errors='coerce').abs()

        return df_parsed