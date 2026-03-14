#!/bin/bash
set -e

# Opcional: esperar o banco de dados iniciar
# sleep 5 

echo "Sincronizando o banco de dados..."
python MagaLabs_LogPrint_Web/sync_db.py

echo "Iniciando a aplicação..."
exec "$@"
