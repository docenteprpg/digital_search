# Busca de trechos em PDF

Você digita um trecho e o `gpt-4o-mini` (OpenAI, via LangChain) encontra até 5 páginas do PDF que tratam do mesmo assunto, cada uma com um resumo de uma linha.

## Preparação (uma vez)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install langchain-openai langchain-community pypdf python-dotenv truststore streamlit pymupdf
```

Crie um arquivo `.env` com `OPENAI_API_KEY=sua-chave-aqui` e coloque o PDF na pasta como `documento.pdf` (ou altere `ARQUIVO` em `app.py`).

## Executar com a interface (recomendado)

```bash
.venv\Scripts\activate
streamlit run interface.py
```

O navegador abre em `http://localhost:8501`. Digite o trecho na caixa de chat; cada resposta vira um botão que, ao ser clicado, abre a página correspondente no PDF exibido à direita.

> Se aparecer "streamlit não é reconhecido", use `python -m streamlit run interface.py`.

## Executar no terminal

```bash
python app.py
```

Digite um trecho para buscar, ou `sair` para encerrar.

> O PDF é enviado inteiro ao modelo, então documentos acima de ~100 mil tokens podem passar do limite.
