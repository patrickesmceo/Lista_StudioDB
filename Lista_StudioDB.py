import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# --- CONFIGURAÇÕES DO STUDIO ---
# Número da CEO com código do país (55) e DDD (65)
NUMERO_CEO = "5565996677698"
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1jVov3bjoJXAUUpjj0yx5J98IyDI_RphmmpHZnzZ0x8s/edit?gid=0#gid=0"

# Configuração visual do App
st.set_page_config(page_title="StudioDB - Chamada Digital", page_icon="🩰", layout="centered")

# Inicializa conexão segura com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def carregar_dados():
    """Lê os dados da planilha mestre"""
    return conn.read(spreadsheet=URL_PLANILHA)

# Carregamento dos dados
df = carregar_dados()

# --- BARRA LATERAL: LOGIN E PRIVACIDADE ---
st.sidebar.title("🩰 StudioDB Access")
lista_professoras = sorted(df['Professora'].unique().tolist())
professora_logada = st.sidebar.selectbox("Selecione seu nome:", ["Selecionar..."] + lista_professoras)

# Bloqueio de acesso: Só mostra o conteúdo se a professora se identificar
if professora_logada == "Selecionar...":
    st.title("Sistema de Chamada")
    st.info("Olá! Por favor, identifique-se na barra lateral para acessar suas turmas e alunas.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.title(f"Painel: {professora_logada.title()}")

# Seletor de Data para registro histórico
data_aula = st.date_input("Data da Aula:", datetime.now())

# Filtro de segurança: A professora só enxerga os dados dela
df_privado = df[df['Professora'] == professora_logada]

# Seleção Dinâmica de Horário e Modalidade (baseado na sua planilha)
col1, col2 = st.columns(2)
with col1:
    horarios = sorted(df_privado['Horário'].unique().tolist())
    horario_sel = st.selectbox("Horário da Aula:", horarios)

with col2:
    categorias = df_privado[df_privado['Horário'] == horario_sel]['Sub Categoria'].unique().tolist()
    categoria_sel = st.selectbox("Modalidade:", categorias)

# Filtra a lista nominal de alunas
turma_final = df_privado[(df_privado['Horário'] == horario_sel) & (df_privado['Sub Categoria'] == categoria_sel)]
lista_alunas = turma_final['Alunas'].tolist()

# --- ÁREA DA CHAMADA ---
st.write("---")
st.subheader(f"Lista de Presença - {data_aula.strftime('%d/%m/%Y')}")
presencas = []

if not lista_alunas:
    st.warning("Nenhuma aluna cadastrada para este horário.")
else:
    for aluna in lista_alunas:
        if st.checkbox(aluna, key=f"check_{aluna}"):
            presencas.append(aluna)

# --- FINALIZAÇÃO E RELATÓRIO WHATSAPP ---
st.write("---")
if st.button("🚀 FINALIZAR E ENVIAR PARA CEO"):
    if presencas:
        total = len(lista_alunas)
        qtd = len(presencas)
        faltas = list(set(lista_alunas) - set(presencas))
        
        # Montagem do texto formatado para o WhatsApp
        mensagem = (
            f"🩰 *CHAMADA DIGITAL - StudioDB*\n\n"
            f"📅 *Data:* {data_aula.strftime('%d/%m/%Y')}\n"
            f"👩‍🏫 *Professora:* {professora_logada}\n"
            f"⏰ *Aula:* {horario_sel} ({categoria_sel})\n"
            f"--------------------------\n"
            f"✅ *Presentes:* {qtd} de {total}\n"
            f"👥 *Alunas:* {', '.join(presencas)}\n"
        )
        
        if faltas:
            mensagem += f"\n❌ *Faltas:* {', '.join(faltas)}"
            
        # Codificação do link da API do WhatsApp
        texto_url = urllib.parse.quote(mensagem)
        link_zap = f"https://api.whatsapp.com/send?phone={NUMERO_CEO}&text={texto_url}"
        
        st.success("Relatório gerado com sucesso!")
        
        # Botão de ação direta
        st.markdown(f'''
            <a href="{link_zap}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 15px; text-align: center; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    📱 Abrir WhatsApp e Enviar para CEO
                </div>
            </a>
        ''', unsafe_allow_html=True)
        st.balloons()
    else:
        st.error("Por favor, marque ao menos uma presença.")

# --- NOVO CADASTRO (COLUNA: Fornecedor/Cliente) ---
with st.expander("➕ Adicionar Aluna Nova"):
    with st.form("form_nova_aluna", clear_on_submit=True):
        nome_aluna = st.text_input("Nome completo da Aluna:")
        nome_responsavel = st.text_input("Responsável (Fornecedor/Cliente):")
        
        btn_salvar = st.form_submit_button("Confirmar e Salvar na Planilha")
        
        if btn_salvar:
            if nome_aluna and nome_responsavel:
                # Criando a nova linha com o nome exato da sua coluna
                nova_linha = pd.DataFrame([{
                    "Alunas": f"{nome_aluna} (NOVA)",
                    "Fornecedor/Cliente": nome_responsavel, # Nome exato da coluna
                    "Professora": professora_logada,
                    "Horário": horario_sel,
                    "Sub Categoria": categoria_sel,
                    "Data Cadastro": data_aula.strftime('%d/%m/%Y'),
                    "Origem": "App_Chamada"
                }])
                
                try:
                    # Adiciona e faz o update na planilha
                    df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, data=df_atualizado)
                    
                    st.success(f"✅ Sucesso! {nome_aluna} cadastrada para {nome_responsavel}.")
                    st.balloons()
                    st.cache_data.clear() # Atualiza a lista de chamada na hora
                except Exception as e:
                    st.error("Erro ao gravar. Verifique se a planilha está aberta para edição no Google Drive.")
            else:
                st.warning("Preencha o nome da aluna e do responsável.")
