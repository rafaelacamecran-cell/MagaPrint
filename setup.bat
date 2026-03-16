@echo off
title MagaLabs LogPrint - Start Environment
echo ==============================================
echo [1/3] Iniciando configuracao (Windows)
echo ==============================================

:: Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao esta instalado ou rodando!
    echo Instale o Docker Desktop em: https://www.docker.com/products/docker-desktop/
    pause
    exit /b
)

:: Copy .env.example to .env if .env doesn't exist
if not exist .env (
    echo [2/3] Arquivo .env nao encontrado. Criando a partir de .env.example...
    copy .env.example .env >nul
    echo Por favor, edite as chaves no arquivo '.env' e rode este script novamente.
    pause
    exit /b
) else (
    echo [2/3] Arquivo .env encontrado!
)

echo [3/3] Subindo os containers do Docker...
docker-compose up -d --build

echo ==============================================
echo [SUCESSO] Sistema MagaLabs LogPrint Online!
echo ==============================================
echo [ACESSO]
echo - Sistema Web:        http://localhost:5001/
echo - Painel Deployer:    http://localhost:8501/
echo.
pause
