import streamlit as st
import datetime
from utils.db import insert_record

st.set_page_config(page_title="Registro Manual", page_icon="📝")
st.title("Adicionar Lançamento Manual")

with st.form("manual_entry_form"):
    data = st.date_input("Data", datetime.date.today())
    entrada_saida = st.selectbox("Entrada/Saída", ["Entrada", "Saída"])
    tipo = st.text_input("Tipo")
    detalhes = st.text_input("Detalhes")
    valor = st.number_input("Valor", min_value=0.01, format="%.2f")
    categoria = st.selectbox("Categoria", ["Transporte", "Lazer", "Casa", "Alimentação", "Saúde", "Educação", "Outros", "Pendente"])
    descricao = st.text_area("Descrição")
    
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
