# pip install streamlit pymupdf
# Rode com:  streamlit run interface.py
import pymupdf  # PyMuPDF — desenha as páginas do PDF como imagem
import streamlit as st

st.set_page_config(page_title="Busca no PDF", page_icon="📄", layout="wide")


# Carrega o PDF e a chain UMA vez (o Streamlit roda o script de novo a cada clique)
@st.cache_resource(show_spinner="Lendo o PDF...")
def carregar():
    from app import ARQUIVO, chain, paginas
    return chain, pymupdf.open(ARQUIVO), len(paginas)


chain, pdf, total_paginas = carregar()

# Memória da conversa e da página aberta no visualizador
st.session_state.setdefault("historico", [])   # [{"trecho": ..., "achados": [...]}]
st.session_state.setdefault("pagina", 1)
st.session_state.setdefault("destaque", "")    # trecho a marcar na página


def abrir_pagina(numero, destaque=""):
    st.session_state.pagina = max(1, min(numero, total_paginas))
    st.session_state.destaque = destaque


def desenhar_pagina(numero, destaque):
    pagina = pdf[numero - 1]
    if destaque:
        for area in pagina.search_for(destaque):  # marca o trecho se ele aparecer literalmente
            pagina.add_highlight_annot(area)
    imagem = pagina.get_pixmap(dpi=110).tobytes("png")
    # Remove as marcações para não acumular no PDF aberto em memória
    for anotacao in list(pagina.annots() or []):
        pagina.delete_annot(anotacao)
    return imagem


st.title("📄 Busca de trechos no PDF")
col_chat, col_pdf = st.columns([1, 1], gap="large")

# ---------- Coluna da conversa ----------
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
                    on_click=abrir_pagina,
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

# ---------- Coluna do PDF ----------
with col_pdf:
    pag = st.session_state.pagina
    st.subheader(f"Documento — página {pag} de {total_paginas}")

    anterior, campo, proxima = st.columns([1, 2, 1])
    anterior.button("◀ Anterior", on_click=abrir_pagina, args=(pag - 1,),
                    disabled=pag <= 1, width="stretch")
    proxima.button("Próxima ▶", on_click=abrir_pagina, args=(pag + 1,),
                   disabled=pag >= total_paginas, width="stretch")
    ir_para = campo.number_input("Ir para a página", 1, total_paginas, pag,
                                 label_visibility="collapsed")
    if ir_para != pag:
        abrir_pagina(int(ir_para))
        st.rerun()

    with st.container(height=800):
        st.image(desenhar_pagina(pag, st.session_state.destaque),
                 width="stretch")
