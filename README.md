# 🖨️ MagaPrint - Infraestrutura & Suprimentos

![MagaPrint Banner](MagaLabs_LogPrint_Web/static/img/LabsPrint.png)

O **MagaPrint** é uma solução centralizada para gestão de ativos de TI, monitoramento de infraestrutura e controle de suprimentos (toners) para o centro de distribuição LuizaLabs/ Magalu.

## 🚀 Principais Recursos

- **Monitoramento em Tempo Real**: Status (Ping) de impressoras HP Laser, Zebra (ZT411, ZD420/421) e links de rede.
- **Gestão de Suprimentos**: Alertas automáticos de toner baixo e formulário obrigatório de troca para auditoria técnica.
- **Estoque Virtual**: Controle de entrada e saída de hardware e insumos.
- **Alertas GChat**: Integração total com Google Chat para notificações críticas de queda de link ou troca de toner.
- **Inteligência Artificial**: MagaBot integrado (Gemini API) para auxílio técnico e sugestão de soluções.
- **Infraestrutura Ágil**: Preparado para rodar em **Docker** na porta 80.

---

## 🛠️ Como Iniciar (Quick Start)

### Maneira Mais Rápida (Recomendado)

O projeto inclui scripts automatizados para subir a infraestrutura completa no Docker com apenas um clique.

1. Clone ou extraia o repositório.
2. Dê um duplo-clique no script de configuração adequado ao seu sistema:
   - **No Windows:** Execute `setup.bat`
   - **No Linux/Mac:** Execute `sh setup.sh`
3. O script criará o arquivo `.env` para você. **Edite o `.env` gerado** para adicionar suas chaves de API.
4. Rode o script novamente para subir o sistema.
5. Acesse a aplicação em: `http://localhost:5001`

### Usando Docker Manualmente

1. Copie o arquivo `.env.example` para `.env` e configure-o.
2. Execute:

   ```bash
   docker-compose up --build -d
   ```

3. Acesse em: `http://localhost:5001`

### Como exportar para o Pendrive (Versão Leve)

Se você precisar copiar o projeto para outro computador ou notebook e quiser ignorar pastas super pesadas (como `.venv` ou `__pycache__`), use os scripts de exportação:

- **No Windows:** Execute `.\export_project.ps1` (ou clique com botão direito > "Executar com o PowerShell")
- **No Linux/Mac:** Execute `./export_project.sh`

Isso irá gerar um arquivo incrivelmente leve chamado `MagaLabs_Project.zip` na raiz do projeto. Basta levar esse ZIP no seu pendrive!

## 📁 Estrutura do Projeto

- `/MagaLabs_LogPrint_Web`: Aplicação Web principal (Flask).
- `/cds_infra`: Robô de monitoramento e integração com GChat.
- `Dockerfile` & `docker-compose.yml`: Configurações de containerização.
- `devices.txt`: Listagem categorizada de IPs e ativos para o robô.

---

## 📝 Documentação Adicional

- [Guia de Implantação na Intranet](deployment_guide.md)
- [Instruções Docker Detalhadas](README_DOCKER.md)

---
Desenvolvido por **T.I Rafaela Camecran - Magalu**
