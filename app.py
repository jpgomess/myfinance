import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px

# Configuração da Página - Deve ser o primeiro comando Streamlit
st.set_page_config(page_title="MyFinances", page_icon="💰", layout="wide")

# 1) Conexão Supabase
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Erro ao conectar ao Supabase: {e}")
    st.info("Certifique-se de configurar o arquivo `.streamlit/secrets.toml` com SUPABASE_URL e SUPABASE_KEY.")
    st.stop()

st.title("💰 MyFinances - Gestão Financeira Pessoal")

CATEGORIAS = ["Transporte", "Lazer", "Casa", "Alimentação", "Saúde", "Educação", "Outros", "Pendente"]

# --- FUNÇÕES DE BANCO DE DADOS ---
def get_gastos():
    response = supabase.table("gastos").select("*").execute()
    return pd.DataFrame(response.data)

def inserir_gastos(df_novos):
    if df_novos.empty:
        return 0
    records = df_novos.to_dict("records")
    response = supabase.table("gastos").insert(records).execute()
    return len(response.data)

def atualizar_categoria(gasto_id, nova_categoria):
    supabase.table("gastos").update({"categoria": nova_categoria}).eq("id", gasto_id).execute()

# --- ABAS DA APLICAÇÃO ---
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Registro Manual", "Importar Extrato", "Categorização Pendente"])

# --- ABA 2: REGISTRO MANUAL ---
with tab2:
    st.header("📝 Registro Manual")
    with st.form("form_registro_manual"):
        col1, col2 = st.columns(2)
        with col1:
            data_input = st.date_input("Data")
            valor_input = st.number_input("Valor", min_value=0.01, step=0.01, format="%.2f")
        with col2:
            tipo_input = st.text_input("Tipo")
            detalhes_input = st.text_input("Detalhes")
            # Exclui a opção 'Pendente' do cadastro manual
            categoria_input = st.selectbox("Categoria", [c for c in CATEGORIAS if c != "Pendente"]) 
        
        submitted = st.form_submit_button("Registrar Gasto")
        if submitted:
            if tipo_input and detalhes_input and valor_input > 0:
                novo_registro = pd.DataFrame([{
                    "data": data_input.strftime("%Y-%m-%d"),
                    "tipo": tipo_input,
                    "detalhes": detalhes_input,
                    "entrada_saida": "SAÍDA", # Registros manuais são sempre 'saídas'
                    "valor": float(valor_input),
                    "categoria": categoria_input
                }])
                inserir_gastos(novo_registro)
                st.success("Gasto registrado com sucesso!")
            else:
                st.error("Preencha todos os campos corretamente.")

# --- ABA 3: IMPORTAR EXTRATO ---
with tab3:
    st.header("📥 Importar Extrato (CSV ou Excel)")
    uploaded_file = st.file_uploader("Escolha um arquivo", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                # Pode precisar de ajuste no separador dependendo do CSV do banco
                df_extrato = pd.read_csv(uploaded_file, sep=None, engine='python') 
            else:
                df_extrato = pd.read_excel(uploaded_file)
            
            st.write("Pré-visualização dos dados originais:")
            st.dataframe(df_extrato.head())
            
            # A lógica agora assume um formato de extrato específico, sem mapeamento manual.
            
            if st.button("Processar e Importar"):
                # 1. Validação e Seleção de Colunas
                colunas_necessarias = ['Data', 'Lançamento', 'Detalhes', 'Valor', 'Tipo Lançamento']
                
                if not all(col in df_extrato.columns for col in colunas_necessarias):
                    st.error(f"O arquivo importado não contém as colunas esperadas. Verifique se as colunas `{', '.join(colunas_necessarias)}` existem.")
                    st.stop()

                # 2. Renomear, Reordenar e Transformar
                df_proc = df_extrato[colunas_necessarias].copy()
                df_proc = df_proc.rename(columns={
                    'Lançamento': 'Tipo',
                    'Tipo Lançamento': 'Entrada/Saída'
                })
                
                ordem_desejada = ["Data", "Entrada/Saída", "Tipo", "Detalhes", "Valor"]
                df_proc = df_proc[ordem_desejada]
                
                for col in ['Entrada/Saída', 'Tipo', 'Detalhes']:
                    df_proc[col] = df_proc[col].astype(str).str.upper()

                st.write("Dados transformados antes da importação:")
                st.dataframe(df_proc.head())

                # 3. Padronizar para o formato do banco de dados
                df_import = pd.DataFrame()
                df_import['data'] = df_proc['Data']
                df_import['tipo'] = df_proc['Tipo']
                df_import['detalhes'] = df_proc['Detalhes']
                df_import['entrada_saida'] = df_proc['Entrada/Saída']
                df_import['valor'] = df_proc['Valor']
                
                # Tratar valores vazios
                df_import = df_import.dropna()
                
                # Converter datas
                df_import["data"] = pd.to_datetime(df_import["data"], dayfirst=True, errors='coerce').dt.strftime("%Y-%m-%d")
                df_import = df_import.dropna(subset=['data']) # Remover linhas onde a data não pôde ser convertida
                
                # Padronizar valores (garantir que tudo vire gasto/saída com valor absoluto/positivo)
                # Remove potenciais símbolos de moeda e converte para float
                if df_import["valor"].dtype == 'O': # Se for string
                    df_import["valor"] = df_import["valor"].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
                
                df_import["valor"] = df_import["valor"].apply(lambda x: abs(float(x)))
                
                # Categoria padrão para importação
                df_import["categoria"] = "Pendente"
                
                # 4) Lógica de Deduplicação
                df_existentes = get_gastos()
                if not df_existentes.empty:
                    # Criar chave única combinando data, tipo, detalhes e valor
                    def make_key(row):
                        return f"{row['data']}_{str(row['tipo']).strip().lower()}_{str(row['detalhes']).strip().lower()}_{row['valor']:.2f}"
                    df_existentes['chave'] = df_existentes.apply(make_key, axis=1)
                    df_import['chave'] = df_import.apply(make_key, axis=1)
                    
                    # Filtra apenas os que não existem no banco
                    df_novos = df_import[~df_import['chave'].isin(df_existentes['chave'])].copy()
                    df_novos = df_novos.drop(columns=['chave'])
                else:
                    df_novos = df_import.copy()
                
                if df_novos.empty:
                    st.warning("Nenhum gasto novo para importar. Todos os itens mapeados já existem no banco.")
                else:
                    inseridos = inserir_gastos(df_novos)
                    st.success(f"{inseridos} novos gastos importados com sucesso!")
                    
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            st.info("Verifique se o formato do arquivo corresponde ao esperado e se os dados estão corretos (ex: data válida, valor numérico).")

# --- ABA 4: CATEGORIZAÇÃO PENDENTE ---
with tab4:
    st.header("🏷️ Categorização Pendente")
    df_todos = get_gastos()
    
    if not df_todos.empty:
        df_pendentes = df_todos[df_todos["categoria"] == "Pendente"].copy()
        
        if not df_pendentes.empty:
            st.write("Atualize as categorias dos gastos listados abaixo:")
            
            # Utiliza st.data_editor para edição iterativa e rápida
            df_edit = st.data_editor(
                df_pendentes[["id", "data", "tipo", "detalhes", "valor", "categoria"]],
                column_config={
                    "id": None, # Ocultar coluna ID para o usuário
                    "detalhes": "Detalhes",
                    "valor": st.column_config.NumberColumn(
                        "Valor",
                        format="R$ %.2f",
                    ),
                    "data": st.column_config.DateColumn(
                        "Data",
                        format="DD/MM/YYYY",
                    ),
                    "categoria": st.column_config.SelectboxColumn(
                        "Categoria",
                        help="Selecione a categoria do gasto",
                        options=CATEGORIAS,
                        required=True,
                    )
                },
                disabled=["data", "tipo", "detalhes", "valor"],
                hide_index=True,
                key="editor_pendentes",
                use_container_width=True
            )
            
            if st.button("Salvar Categorias"):
                mudancas = 0
                for index, row in df_edit.iterrows():
                    id_gasto = row["id"]
                    nova_cat = row["categoria"]
                    # Busca a categoria original no dataframe pendentes
                    cat_antiga = df_pendentes.loc[df_pendentes["id"] == id_gasto, "categoria"].values[0]
                    
                    if nova_cat != cat_antiga and nova_cat != "Pendente":
                        atualizar_categoria(id_gasto, nova_cat)
                        mudancas += 1
                
                if mudancas > 0:
                    st.success(f"{mudancas} gastos categorizados com sucesso!")
                    st.rerun() # Recarrega a página para atualizar as abas
                else:
                    st.info("Nenhuma categoria nova foi alterada e salva.")
        else:
            st.success("Não há gastos com categoria 'Pendente'. Ótimo trabalho! 🎉")
    else:
        st.info("Nenhum dado cadastrado.")

# --- ABA 1: DASHBOARD ---
with tab1:
    st.header("📊 Dashboard")
    df_dash = get_gastos()
    
    if not df_dash.empty:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Gastos por Categoria")
            # Agrupar valores por categoria
            df_grp = df_dash.groupby("categoria", as_index=False)["valor"].sum()
            fig = px.pie(df_grp, values='valor', names='categoria', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
            total = df_dash['valor'].sum()
            st.metric("Total Gasto", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
        with col2:
            st.subheader("Histórico de Gastos")
            # Ordenar do mais recente para o mais antigo
            df_dash_sorted = df_dash.sort_values(by="data", ascending=False)

            # Formatando a exibição
            st.dataframe(
                df_dash_sorted,
                column_config={
                    "id": None,
                    "descricao": None,
                    "created_at": None,
                    "entrada_saida": None,
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "tipo": "Tipo",
                    "detalhes": "Detalhes"
                },
                column_order=("data", "tipo", "detalhes", "valor", "categoria"),
                hide_index=True, 
                use_container_width=True
            )
    else:
        st.info("Nenhum gasto registrado ainda. Adicione manualmente ou importe um extrato.")
