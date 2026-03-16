#!/bin/bash

echo -e "\e[36m==============================================\e[0m"
echo -e "\e[36m[1/3] Iniciando configuracao (Linux/Mac)\e[0m"
echo -e "\e[36m==============================================\e[0m"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "\e[31m[ERRO] Docker nao esta instalado ou rodando!\e[0m"
    echo "Instale o Docker em: https://docs.docker.com/engine/install/"
    exit 1
fi

# Copy .env.example to .env if .env doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\e[33m[2/3] Arquivo .env nao encontrado. Criando a partir de .env.example...\e[0m"
    cp .env.example .env
    echo -e "\e[31mPor favor, edite as chaves (OPENAI_KEY, MAIL etc) no arquivo '.env' e rode este script novamente.\e[0m"
    exit 1
else
    echo -e "\e[32m[2/3] Arquivo .env encontrado!\e[0m"
fi

echo -e "\e[36m[3/3] Subindo os containers do Docker...\e[0m"
docker-compose up -d --build

echo -e "\e[32m==============================================\e[0m"
echo -e "\e[32m[SUCESSO] Sistema MagaLabs LogPrint Online!\e[0m"
echo -e "\e[32m==============================================\e[0m"
echo -e "\e[36m[ACESSO]\e[0m"
echo -e "\e[36m- Sistema Web:        http://localhost:5001/\e[0m"
echo -e "\e[36m- Painel Deployer:    http://localhost:8501/\e[0m"
echo ""
