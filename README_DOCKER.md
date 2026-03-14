# Guia Docker - MagaLabs LogPrint

Este projeto foi preparado para rodar em containers Docker usando Docker Compose.

## Pré-requisitos
- Docker instalado
- Docker Compose instalado

## Como Rodar

1. **Configuração de Variáveis de Ambiente:**
   - Copie o arquivo `.env.example` para `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edite o arquivo `.env` e preencha com suas chaves de API (Gemini, OpenAI) e configurações de e-mail.

2. **Subir os Containers:**
   ```bash
   docker-compose up --build
   ```

3. **Acessar as Aplicações:**
   - **Sistema Web (Flask):** [http://localhost:5000](http://localhost:5000)
   - **Deployer de Impressoras (Streamlit):** [http://localhost:8501](http://localhost:8501)
   - **Banco de Dados (Postgres):** Port 5432 no host.

## Estrutura do Docker Compose
- `db`: Banco de dados PostgreSQL 15.
- `web`: Aplicação principal Flask, servida pelo `waitress` para produção.
- `deployer`: Ferramenta auxiliar de deployer de impressoras feita em Streamlit.

## Notas Importantes
- O banco de dados é sincronizado automaticamente na inicialização do container `web`.
- Os uploads de arquivos são persistidos no diretório local `MagaLabs_LogPrint_Web/static/uploads` através de um volume.
- O banco de dados postgres é persistido no volume nomeado `postgres_data`.
