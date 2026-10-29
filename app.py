# pip install langchain-openai langchain-community pypdf python-dotenv truststore
import truststore
truststore.inject_into_ssl()   # usa os certificados do Windows (evita erro SSL atrás de proxy/antivírus)

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

ARQUIVO = "documento.pdf"   # troque pelo seu PDF

# 0. O LEITOR — lê o PDF inteiro (1 Document por página, SEM chunks)
paginas = PyPDFLoader(ARQUIVO).load()
texto_pdf = "\n\n".join(
    f"[PÁGINA {p.metadata['page'] + 1}]\n{p.page_content}" for p in paginas
)

# Conta aproximada: ~4 caracteres por token. O gpt-4o-mini aceita 128k tokens.
tokens = len(texto_pdf) // 4
print(f"PDF com {len(paginas)} páginas, ~{tokens} tokens.")
if tokens > 100_000:
    print(tokens)
    print("Atenção: o PDF está perto do limite do modelo; considere dividir.")

# 2. MODELO — o cérebro
modelo = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=800)

# 1a. O FORMULÁRIO — o que o modelo deve devolver
class Trecho(BaseModel):
    pagina: int = Field(description="Número da página onde o conteúdo aparece")
    resumo: str = Field(description="O que a página diz sobre o trecho, em 1 linha")

class Resultado(BaseModel):
    encontrados: list[Trecho] = Field(
        description="Páginas relacionadas, da mais para a menos relevante (no máximo 5)"
    )

# 1b. O faxineiro entrega DADOS
faxineiro = JsonOutputParser(pydantic_object=Resultado)

# 1c. PROMPT TEMPLATE — o documento inteiro vai fixo no carimbo (.partial)
prompt_busca = ChatPromptTemplate.from_messages([
    ("system",
     "Você é um bibliotecário. Abaixo está o documento inteiro, marcado com [PÁGINA N]. "
     "Encontre as páginas que tratam do mesmo assunto do trecho enviado pelo usuário. "
     "Use SÓ números de página que existem nos marcadores. "
     "Se nada for relacionado, devolva a lista vazia. Responda SÓ com JSON.\n"
     "{formato}\n\nDOCUMENTO:\n{documento}"),
    ("user", "Trecho: {trecho}"),
]).partial(formato=faxineiro.get_format_instructions(), documento=texto_pdf)

# 0b. As "mãos": transforma número de página em link clicável
def montar_links(resultado):
    base = Path(ARQUIVO).resolve().as_uri()        # file:///.../material.pdf
    return [
        {**t, "link": f"{base}#page={t['pagina']}"}  # #page=N abre direto na página
        for t in resultado["encontrados"]
    ]

# 3. A fila de montagem: molde -> cérebro -> faxineiro -> mãos
chain = prompt_busca | modelo | faxineiro | RunnableLambda(montar_links)

# Conversa com o usuário (só no terminal; a interface web está em interface.py)
if __name__ == "__main__":
    while True:
        trecho = input("\nDigite um trecho (ou 'sair'): ").strip()
        if trecho.lower() == "sair":
            break
        achados = chain.invoke({"trecho": trecho})
        if not achados:
            print("Nenhum conteúdo relacionado encontrado.")
        for a in achados:
            print(f"- Página {a['pagina']}: {a['resumo']}\n  {a['link']}")
