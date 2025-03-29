import streamlit as st
import pymongo
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Definir o intervalo para a atualização automática (1 minuto)
time_interval = 10  # 60 segundos (1 minuto)

# Recarregar automaticamente após 1 minuto
if time.time() - st.session_state.get('last_run', 0) > time_interval:
    st.session_state['last_run'] = time.time()  # Armazena o tempo da última execução
    st.rerun()   # Recarrega a página


st.set_page_config(page_title="BovTag Masters", page_icon=":bar_chart:",layout="wide")
# 🔹 Reset CSS Profissional + Ajustes para ocupar toda a tela
st.markdown(
    """
    <style>
        /* RESET CSS */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            border: none;
            outline: none;
            font-family: Arial, sans-serif;
        }

        html, body {
            width: 100%;
            height: 100%;
            overflow-x: hidden;
            background-color: #f8f9fa;
            padding: 10px; /* Adiciona espaçamento de 10px ao redor */
        }

        /* Remove espaçamentos laterais no Streamlit */
        .main, .block-container {
            padding: 10px !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        /* Garante que as tabelas ocupem 100% da largura */
        .dataframe-container {
            width: 100% !important;
            overflow-x: auto;
        }

        .dataframe {
            width: 100% !important;
            border-collapse: collapse;
        }

        /* Ajusta os gráficos para ocupar 100% da largura */
        .element-container {
            width: 100% !important;
        }

        /* Remove margens internas da sidebar */
        .sidebar .block-container {
            padding: 10px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# URI = "mongodb+srv://masters:TV9GFQdPZVgOXwvc@masters.jatpq.mongodb.net/?appName=Masters"
# BANCO = "db_master"
# COLECAO = "sensores"

URI = os.getenv("URI")
BANCO = os.getenv("BANCO")
COLECAO = os.getenv("COLECAO")


# Configuração do MongoDB
client = pymongo.MongoClient(URI)
db = client["db_master"]
collection = db["sensores"]

# Função para obter dados do MongoDB
def obter_dados():

    dados = list(collection.find({}, {"_id": 1, "fazenda": 1, "id_boi": 1, "createdAt": 1}))
    df = pd.DataFrame(dados)

    if "_id" in df.columns:
        df["quantidade"] = 1  # Cada ID é um registro único, então usamos 1 por linha

    if "createdAt" in df.columns:
        df["createdAt"] = pd.to_datetime(df["createdAt"])  # Converte para datetime

    return df

# Criar a interface no Streamlit
st.title("BOVTAG - Dashboard")

df = obter_dados()

# Definir o fuso horário de Manaus (GMT-4)
timezone = pytz.timezone("America/Manaus")

# Se houver dados, aplicar filtros
if not df.empty:
    df["createdAt"] = df["createdAt"].dt.tz_localize('UTC').dt.tz_convert(timezone)
    df["data"] = df["createdAt"].dt.date
    df["mes"] = df["createdAt"].dt.to_period("M")
    df["hora"] = df["createdAt"].dt.hour  # Extraímos a hora para análise de registros por hora

    # 🎛️ Filtros no sidebar
    with st.sidebar:
        st.header("Filtros")

        # Filtro por data
        data_selecionada = st.date_input("Selecione a Data", df["data"].max())

        # Filtro por mês
        mes_selecionado = st.selectbox("Selecione o Mês", df["mes"].unique().astype(str))

        # Filtro por id_boi
        boi_selecionado = st.selectbox("Selecione o ID do Boi", ["Todos"] + sorted(df["id_boi"].unique()))

    # Aplicando os filtros
    df_filtrado = df[(df["data"] == data_selecionada) & (df["mes"].astype(str) == mes_selecionado)]
    if boi_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["id_boi"] == boi_selecionado]

    # 📌 Criando as 4 colunas, todas com mesmo tamanho
    col1, col2, col3, col4 = st.columns(4)

    # Função para criar uma caixa estilizada com tamanho fixo
    # Função para criar uma caixa estilizada com fundo em gradiente
    def create_box(title, content):
        # Ajusta a fonte dependendo do tamanho do texto
        font_size = "24px" if len(str(content)) <= 10 else "18px"
        
        # Cor de destaque mais vibrante (para o gradiente)
        box_color_start = "#28a745"  # Verde inicial
        box_color_end = "#2D738E"  # Verde mais claro ou uma variação

        return f"""
        <div style="border: 2px solid {box_color_end}; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); text-align: center; background: linear-gradient(135deg, {box_color_start}, {box_color_end}); height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <h3 style="color: white; font-size: 24px;">{title}</h3>
            <p style="font-size: {font_size}; color: white; margin: 0;">{content}</p>
        </div>
        """



    # 📌 Exibindo os KPIs com caixas estilizadas
    with col1:
        st.markdown(create_box("Fazenda", df_filtrado["fazenda"].iloc[0] if not df_filtrado.empty else "N/A"), unsafe_allow_html=True)

    with col2:
        st.markdown(create_box("Total Curral", len(df_filtrado)), unsafe_allow_html=True)

    with col3:
        st.markdown(create_box("Total Fazenda", df_filtrado["id_boi"].nunique() if not df_filtrado.empty else 0), unsafe_allow_html=True)

    with col4:
        st.markdown(create_box("BOVTAG", df_filtrado["id_boi"].iloc[-1] if not df_filtrado.empty else "N/A"), unsafe_allow_html=True)


    # 📌 Criando a linha com 2 gráficos
    col1, col2 = st.columns(2)

    # 🔹 Primeiro gráfico: Linhas por Hora
    with col1:
        if not df_filtrado.empty:
            horas_completas = pd.DataFrame({"hora": range(0, 24)})
            linhas_por_hora = df_filtrado.groupby("hora").size().reset_index(name="quantidade")
            linhas_por_hora = horas_completas.merge(linhas_por_hora, on="hora", how="left").fillna(0)

            fig = px.line(
                linhas_por_hora, 
                x="hora", 
                y="quantidade", 
                markers=True, 
                title="Linhas por Hora no Dia Selecionado",
                labels={"hora": "Hora do Dia", "quantidade": "Número de Registros"},
                

            )

            # Centraliza o título
            fig.update_layout(
                title=dict(
                    x=0.5,  # Centraliza o título
                    xanchor='center',  # Alinha o título no centro
                ),
                xaxis=dict(
                    tickmode='linear',  # Força a exibição de todos os ticks de forma contínua
                    dtick=1,  # Intervalo de 1 para os ticks (de 1 a 31)
                )
            )
            st.plotly_chart(fig, use_container_width=True)

    # 🔹 Segundo gráfico: Distribuição das Quantidades Diárias
    with col2:
        if not df_filtrado.empty:
            # Gráfico de barras para a distribuição das quantidades diárias
            # Cria uma lista de dias de 1 a 31
            dias_mes = pd.DataFrame({"dia": range(1, 32)})

            # Agrupa os dados por dia e conta as quantidades
            df_diario = df_filtrado.groupby(df_filtrado["createdAt"].dt.day).size().reset_index(name="quantidade")
            
            # Mescla os dados de dias com o DataFrame para garantir todos os dias do mês
            df_diario_completo = dias_mes.merge(df_diario, left_on="dia", right_on="createdAt", how="left").fillna(0)

            # Gráfico de barras para a distribuição das quantidades diárias
            fig_diario = px.bar(
                df_diario_completo, 
                x="dia", 
                y="quantidade", 
                title="Distribuição das Quantidades Diárias",
                labels={"dia": "Dia do Mês", "quantidade": "Quantidade"},
                # color="quantidade",  # Aplica a paleta de cores com base na quantidade
                color_continuous_scale="RdYlBu",  # Define a paleta de cores contínua (opcional)
            )

            # Centraliza o título
            fig_diario.update_layout(
                title=dict(
                    x=0.5,  # Centraliza o título
                    xanchor='center',  # Alinha o título no centro
                ),
                xaxis=dict(
                    tickmode='linear',  # Força a exibição de todos os ticks de forma contínua
                    dtick=1,  # Intervalo de 1 para os ticks (de 1 a 31)
                )
            )
            st.plotly_chart(fig_diario, use_container_width=True)
        else:
            st.warning("Sem dados para o dia selecionado.")

            # 🔢 Valores para o gráfico de pizza

        # 📌 Criando a linha com 2 gráficos
    col1, col2 = st.columns(2)
    with col1:
        if not df_filtrado.empty:
            total_registros = len(df_filtrado)
            total_bois_fazenda = df_filtrado["id_boi"].nunique() if not df_filtrado.empty else 0

            # 📊 Pequeno gráfico de Pizza na quarta coluna
            fig_pizza_small = px.pie(
                values=[total_registros, total_bois_fazenda],
                title="Qty Curral X Qty Fazenda - Dia Selecionado",
                names=["Curral", "Fazenda"],
                hole=0.5,  # Formato de donut
                # height=350,  # Diminuído para ser discreto
                # width=350,  # Mantém a suavidade
                color=["Curral", "Fazenda"],  # Aplica uma paleta de cores com base na quantidade
                color_discrete_sequence=["#2D738E", "#2AAB81"]  # Paleta de cores personalizada
            )

            # Centraliza o título
            fig_pizza_small.update_layout(
                title=dict(
                    x=0.5,  # Centraliza o título
                    xanchor='center',  # Alinha o título no centro
                )
            )
            st.plotly_chart(fig_pizza_small, use_container_width=True)

    # 🔹 Gráfico de barras para quantidade de _id por mês
    with col2:
    # 🔹 Gráfico de barras para quantidade de _id por mês (mostrando todos os meses)
        if not df_filtrado.empty:
            # Converter a coluna "mes" para o formato abreviado (ex: jan, fev, mar, etc.)
            df_filtrado['mes'] = df_filtrado['mes'].dt.strftime('%b')  # %b retorna o nome abreviado do mês
            
            # Garantir que todos os meses sejam exibidos
            meses_completos = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            
            # Agrupar os dados por mês e contar o número de registros (_id)
            df_mensal = df_filtrado.groupby('mes').size().reset_index(name="quantidade")
            
            # Adicionando os meses que não têm dados (preenchendo com 0)
            df_mensal = df_mensal.set_index('mes').reindex(meses_completos, fill_value=0).reset_index()
            df_mensal.columns = ['mes', 'quantidade']
            
            # Gráfico de barras para a quantidade de _id por mês
            fig_mensal = px.bar(
                df_mensal, 
                x="mes", 
                y="quantidade", 
                title="Quantidade de Registros por Mês",
                labels={"mes": "Mês", "quantidade": "Quantidade de Registros"},
                category_orders={"mes": meses_completos},  # Garantir a ordenação correta

                # color="quantidade",  # Aplica uma paleta de cores com base na quantidade
                color_continuous_scale="Viridis"  # Define a paleta de cores contínua
            )

            # Centraliza o título
            fig_mensal.update_layout(
                title=dict(
                    x=0.5,  # Centraliza o título
                    xanchor='center',  # Alinha o título no centro
                )
            )

            st.plotly_chart(fig_mensal, use_container_width=True)
        else:
            st.warning("Sem dados para o mês selecionado.")



    # 🔹 Exibição da tabela de dados filtrados (Agora ocupando toda a tela)
    st.subheader("Tabela de Dados Filtrados")
    st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
    st.dataframe(df_filtrado.style.set_properties(**{'width': '100%'}))
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("Nenhum dado encontrado no MongoDB.")

# Fechar conexão com o MongoDB
client.close()