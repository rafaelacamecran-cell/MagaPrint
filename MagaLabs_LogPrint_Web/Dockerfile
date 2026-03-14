FROM python:3.12-slim

WORKDIR /app

# Instalar dependências de compilação caso existam pacotes que exijam C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar os arquivos da aplicação
COPY . .

# Expor a porta 5000 do Flask
EXPOSE 5000

# Usar Gunicorn (ou Werkzeug default) para rodar o Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
