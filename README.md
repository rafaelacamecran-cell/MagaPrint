# 🖨️ MagaPrint - Hub de Infraestrutura & Suprimentos

![MagaPrint Banner](MagaLabs_LogPrint_Web/static/img/LabsPrint.png)

O **MagaPrint** é uma solução centralizada para gestão de ativos de TI, monitoramento de infraestrutura e controle de suprimentos (toners) para os centros de distribuição LuizaLabs.

## 🚀 Principais Recursos

- **Monitoramento em Tempo Real**: Status (Ping) de impressoras HP Laser, Zebra (ZT411, ZD420/421) e links de rede.
- **Gestão de Suprimentos**: Alertas automáticos de toner baixo e formulário obrigatório de troca para auditoria técnica.
- **Estoque Virtual**: Controle de entrada e saída de hardware e insumos.
- **Alertas GChat**: Integração total com Google Chat para notificações críticas de queda de link ou troca de toner.
- **Inteligência Artificial**: MagaBot integrado (Gemini API) para auxílio técnico e sugestão de soluções.
- **Infraestrutura Ágil**: Preparado para rodar em **Docker** na porta 80.

---

## 🛠️ Como Iniciar (Quick Start)

### Usando Docker (Recomendado)

1. Clone o repositório.
2. Configure o arquivo `.env` (use o `.env.example` como base).
3. Execute:

   ```bash
   docker-compose up --build -d
   ```

4. Acesse em: `http://localhost`

### Local (Desenvolvimento)

1. Crie um ambiente virtual: `python -m venv .venv`
2. Instale as dependências: `pip install -r requirements.txt`
3. Configure o banco PostgreSQL.
4. Rode as tabelas: `python create_tables.py`
5. Inicie o servidor: `python MagaLabs_LogPrint_Web/app.py`

---

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
**Desenvolvido por T.I Rafaela Camecran - Magalu**
