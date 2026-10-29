# pip install streamlit pymupdf
# Rode com:  streamlit run interface.py
import base64
import threading

import pymupdf  # PyMuPDF — desenha as páginas do PDF como imagem
import streamlit as st

st.set_page_config(page_title="Busca no PDF", page_icon="📄", layout="wide")


# Carrega o PDF e a chain UMA vez (o Streamlit roda o script de novo a cada clique)
@st.cache_resource(show_spinner="Lendo o PDF...")
def carregar():
    from app import ARQUIVO, chain, paginas
    return chain, pymupdf.open(ARQUIVO), len(paginas), threading.Lock()


chain, pdf, total_paginas, trava_pdf = carregar()

# Celular: tela estreita, o PDF abre numa janela por cima. Teste no PC com ?celular=1
agente = st.context.headers.get("User-Agent", "")
celular = st.query_params.get("celular") == "1" or "Mobi" in agente or "Android" in agente

# Memória da conversa e da página aberta no visualizador
st.session_state.setdefault("historico", [])   # [{"trecho": ..., "achados": [...]}]
st.session_state.setdefault("pagina", 1)
st.session_state.setdefault("destaque", "")    # trecho a marcar na página
st.session_state.setdefault("zoom", 100)       # % da largura do visualizador


def abrir_pagina(numero, destaque=""):
    st.session_state.pagina = max(1, min(numero, total_paginas))
    st.session_state.destaque = destaque


def clicar_resposta(numero, destaque):
    abrir_pagina(numero, destaque)
    st.session_state.abrir_janela = celular


def desenhar_pagina(numero, destaque, dpi):
    # O PDF é compartilhado entre todos os usuários: um desenho por vez
    with trava_pdf:
        pagina = pdf[numero - 1]
        if destaque:
            for area in pagina.search_for(destaque):  # marca o trecho se ele aparecer literalmente
                pagina.add_highlight_annot(area)
        imagem = pagina.get_pixmap(dpi=dpi).tobytes("png")
        # Remove as marcações para não acumular no PDF aberto em memória
        for anotacao in list(pagina.annots() or []):
            pagina.delete_annot(anotacao)
    return imagem


def visualizador():
    pag = st.session_state.pagina
    if celular:
        # Um só campo com − / +: no celular as colunas ficariam empilhadas
        nova = st.number_input(f"Página (de {total_paginas})", 1, total_paginas, pag)
    else:
        st.subheader(f"Documento — página {pag} de {total_paginas}")
        anterior, campo, proxima = st.columns([1, 2, 1])
        anterior.button("◀ Anterior", on_click=abrir_pagina, args=(pag - 1,),
                        disabled=pag <= 1, width="stretch")
        proxima.button("Próxima ▶", on_click=abrir_pagina, args=(pag + 1,),
                       disabled=pag >= total_paginas, width="stretch")
        nova = campo.number_input("Ir para a página", 1, total_paginas, pag,
                                  label_visibility="collapsed")
    if nova != pag:
        abrir_pagina(int(nova))
        st.rerun(scope="fragment" if celular else "app")

    zoom = st.slider("🔍 Zoom", 50, 300, step=25, format="%d%%", key="zoom")
    # Mais zoom, mais resolução — assim a página não fica borrada ao ampliar
    imagem = desenhar_pagina(pag, st.session_state.destaque, dpi=min(300, 150 * zoom // 100))
    png = base64.b64encode(imagem).decode()
    altura = "70vh" if celular else "800px"
    # Caixa com rolagem nos dois sentidos: com zoom alto a página fica maior que a tela
    st.html(
        f'<div style="height:{altura}; overflow:auto; border:1px solid #ddd; border-radius:8px">'
        f'<img src="data:image/png;base64,{png}" style="width:{zoom}%; max-width:none; display:block">'
        "</div>"
    )


@st.dialog("Documento", width="large")
def janela_pdf():
    visualizador()


st.title("📄 Busca de trechos no PDF")
if celular:
    col_chat = st.container()
else:
    col_chat, col_pdf = st.columns([1, 1], gap="large")

# ---------- Conversa ----------
with col_chat:
    st.subheader("Conversa")
    for i, item in enumerate(st.session_state.historico):
        with st.chat_message("user"):
            st.write(item["trecho"])
        with st.chat_message("assistant"):
            if not item["achados"]:
                st.write("Nenhum conteúdo relacionado encontrado.")
            for j, a in enumerate(item["achados"]):
                st.button(
                    f"📄 Página {a['pagina']} — {a['resumo']}",
                    key=f"resp-{i}-{j}",
                    on_click=clicar_resposta,
                    args=(a["pagina"], item["trecho"]),
                    width="stretch",
                )

trecho = st.chat_input("Digite um trecho para buscar no documento")
if trecho:
    with col_chat:
        with st.spinner("Procurando no documento..."):
            achados = chain.invoke({"trecho": trecho})
    st.session_state.historico.append({"trecho": trecho, "achados": achados})
    if achados:
        abrir_pagina(achados[0]["pagina"], trecho)  # já abre a mais relevante
    st.rerun()

# ---------- PDF ----------
if celular:
    if st.session_state.pop("abrir_janela", False):
        janela_pdf()
else:
    with col_pdf:
        visualizador()
