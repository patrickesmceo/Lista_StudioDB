import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# --- CONFIGURAÇÕES DO STUDIO ---
NUMERO_CEO = "5565996677698" #
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1jVov3bjoJXAUUpjj0yx5J98IyDI_RphmmpHZnzZ0x8s/edit#gid=0"

st.set_page_config(page_title="StudioDB - Chamada Digital", page_icon="🩰", layout="centered")

# Inicializa conexão
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def carregar_dados():
    return conn.read(spreadsheet=URL_PLANILHA)

df = carregar_dados()

# Memória temporária para alunas novas na sessão atual
if 'alunas_novas' not in st.session_state:
    st.session_state.alunas_novas = []

# --- BARRA LATERAL ---
st.sidebar.title("🩰 StudioDB Access")
lista_professoras = sorted(df['Professora'].unique().tolist())
professora_logada = st.sidebar.selectbox("Selecione seu nome:", ["Selecionar..."] + lista_professoras)

if professora_logada == "Selecionar...":
    st.title("Sistema de Chamada")
    st.info("Olá! Identifique-se na barra lateral para acessar suas turmas.")
    st.stop()

# --- FILTRO DE UNIDADE (ORIGEM) ---
# Filtra as unidades onde a professora selecionada atua
unidades_disponiveis = sorted(df[df['Professora'] == professora_logada]['Origem'].unique().tolist())
unidade_sel = st.sidebar.selectbox("Selecione a Unidade:", unidades_disponiveis)

# --- INTERFACE PRINCIPAL ---
st.title(f"Painel: {professora_logada.title()}")
st.subheader(f"Unidade: {unidade_sel}")
data_aula = st.date_input("Data da Aula:", datetime.now())

# Filtro mestre por Professora e Unidade
df_privado = df[(df['Professora'] == professora_logada) & (df['Origem'] == unidade_sel)]

col1, col2 = st.columns(2)
with col1:
    horarios = sorted(df_privado['Horário'].unique().tolist())
    horario_sel = st.selectbox("Horário da Aula:", horarios)

with col2:
    categorias = df_privado[df_privado['Horário'] == horario_sel]['Sub Categoria'].unique().tolist()
    categoria_sel = st.selectbox("Modalidade:", categorias)

# Junta alunas da planilha + alunas novas cadastradas agora
turma_planilha = df_privado[(df_privado['Horário'] == horario_sel) & (df_privado['Sub Categoria'] == categoria_sel)]
lista_fixas = turma_planilha['Alunas'].tolist()

# Filtra alunas novas temporárias para esta aula e unidade específica
novas_aula = [a for a in st.session_state.alunas_novas if a['horario'] == horario_sel and a['categoria'] == categoria_sel and a['unidade'] == unidade_sel]
lista_completa = lista_fixas + [n['nome'] for n in novas_aula]

# --- ÁREA DA CHAMADA ---
st.write("---")
st.subheader(f"Lista de Presença - {data_aula.strftime('%d/%m/%Y')}")
presencas = []

if not lista_completa:
    st.warning(f"Nenhuma aluna encontrada para {categoria_sel} neste horário na unidade {unidade_sel}.")
else:
    for aluna in lista_completa:
        if st.checkbox(aluna, key=f"check_{aluna}"):
            presencas.append(aluna)

# --- CADASTRO MANUAL ---
with st.expander("➕ Adicionar Aluna Nova"):
    with st.form("form_nova", clear_on_submit=True):
        n_aluna = st.text_input("Nome da Aluna:")
        n_resp = st.text_input("Responsável (Fornecedor/Cliente):")
        if st.form_submit_button("Adicionar à lista de hoje"):
            if n_aluna and n_resp:
                st.session_state.alunas_novas.append({
                    'nome': f"{n_aluna} (NOVA)",
                    'responsavel': n_resp,
                    'horario': horario_sel,
                    'categoria': categoria_sel,
                    'unidade': unidade_sel # Salva a unidade no registro temporário
                })
                st.success("Adicionada! Agora marque a presença dela acima.")
                st.rerun()

# --- FINALIZAÇÃO ---
if st.button("🚀 FINALIZAR E ENVIAR PARA ADM"):
    if presencas:
        # Montagem do Relatório incluindo a Unidade
        mensagem = (
            f"🩰 *CHAMADA DIGITAL - StudioDB*\n\n"
            f"🏢 *Unidade:* {unidade_sel}\n"
            f"📅 *Data:* {data_aula.strftime('%d/%m/%Y')}\n"
            f"👩‍🏫 *Professora:* {professora_logada}\n"
            f"⏰ *Aula:* {horario_sel} ({categoria_sel})\n"
            f"--------------------------\n"
            f"✅ *Presentes:* {len(presencas)}\n"
            f"👥 *Alunas:* {', '.join(presencas)}\n"
        )
        
        if novas_aula:
            mensagem += f"\n✨ *CADASTRAR NA PLANILHA:*\n"
            for n in novas_aula:
                mensagem += f"• {n['nome']} | Resp: {n['responsavel']}\n"

        texto_url = urllib.parse.quote(mensagem)
        link_zap = f"https://api.whatsapp.com/send?phone={NUMERO_CEO}&text={texto_url}"
        
        st.markdown(f'''
            <a href="{link_zap}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 15px; text-align: center; border-radius: 8px; font-weight: bold;">
                    📱 Abrir WhatsApp e Enviar para CEO
                </div>
            </a>
        ''', unsafe_allow_html=True)
    else:
        st.error("Marque ao menos uma presença.")
