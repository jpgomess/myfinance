import streamlit as st
import datetime
from utils.db import insert_record

st.set_page_config(page_title="Registro Manual", page_icon="📝")
st.title("Adicionar Lançamento Manual")

with st.form("manual_entry_form"):
    col1, col2, col3, col4 = st.columns(4)
    data = col1.date_input("Data", datetime.date.today())
    entrada_saida = col2.selectbox("Entrada/Saída", ["Entrada", "Saída"])
    tipo = col3.text_input("Tipo")
    detalhes = col4.text_input("Detalhes")
    
    col1, col2, col3 = st.columns([1,1,2])
    valor = col1.number_input("Valor", min_value=0.01, format="%.2f")
    categoria = col2.selectbox("Categoria", ["Transporte", "Lazer", "Casa", "Alimentação", "Saúde", "Educação", "Outros", "Pendente"])
    descricao = col3.text_area("Descrição")
    
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
