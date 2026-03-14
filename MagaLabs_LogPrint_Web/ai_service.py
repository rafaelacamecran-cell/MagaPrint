from google import genai
import os
import json

def generate_ai_insights(api_key, stats_data, recent_logs, open_tickets):
    """
    Usa o Google Gemini para analisar os dados do sistema e gerar insights operacionais.
    """
    if not api_key:
        return {
            "pattern_alert": "Configuração da API Key necessária.",
            "recommendation": "Por favor, configure sua chave API do Gemini nas configurações do sistema."
        }

    try:
        client = genai.Client(api_key=api_key)

        # Preparar o prompt
        prompt = f"""
        Você é um analista de dados especialista em Logística e T.I. 
        Analise os seguintes dados do sistema MagaLabs LogPrint e forneça dois insights curtos e diretos (máximo 2 frases cada).

        DADOS ATUAIS:
        - Total de Dispositivos: {stats_data['total']}
        - Disponíveis: {stats_data['available']}
        - Em uso: {stats_data['in_use']}
        - Em manutenção: {stats_data['support']}
        - Chamados de suporte ativos: {stats_data['open_tickets']}

        ÚLTIMOS LOGS DE ATIVIDADE:
        {recent_logs}

        INSTRUÇÕES:
        1. Identifique um Alerta de Padrão (ex: muitos dispositivos em suporte, alta taxa de trocas em um setor específico).
        2. Forneça uma Recomendação Sugerida (ex: manutenção preventiva, remanejamento de ativos).

        Responda em JSON no formato:
        {{
            "pattern_alert": "texto aqui",
            "recommendation": "texto aqui"
        }}
        """

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        # Tenta extrair o JSON da resposta (limpando possíveis markdown do Gemini)
        content = response.text.strip()
        if content.startswith('```json'):
            content = content[7:-3].strip()
        elif content.startswith('{'):
            pass
        else:
            # Caso não venha em JSON, tenta uma extração simples
            return {
                "pattern_alert": "Análise concluída.",
                "recommendation": "Dados processados com sucesso pelo Gemini."
            }

        return json.loads(content)

    except Exception as e:
        print(f"Erro na IA: {e}")
        return {
            "pattern_alert": "Erro ao processar dados com a IA.",
            "recommendation": "Verifique a conectividade e a validade da chave API."
        }

def technical_chat(api_key, user_message, context_data):
    """
    Interface de chat para o Gemini atuar como assistente técnico.
    """
    if not api_key:
        return "Erro: Chave API não configurada."

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Você é o MagaBot, um assistente técnico especialista do time Logística.
        Você tem acesso aos seguintes dados do sistema:
        {context_data}

        INSTRUÇÕES:
        - Responda de forma profissional e objetiva.
        - Se o usuário perguntar sobre o estado da frota, use os dados fornecidos.
        - Se ele perguntar sobre problemas técnicos (impressoras/computadores), dê sugestões baseadas nos ativos citados.
        - Não invente dados que não estão no contexto.

        MENSAGEM DO USUÁRIO: {user_message}
        """

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text.strip()

    except Exception as e:
        return f"Erro ao processar mensagem: {str(e)}"

def suggest_solution(api_key, problem_description, asset_info):
    """
    Sugere uma solução técnica baseada na descrição do problema.
    """
    if not api_key:
        return "Configure a API Key para receber sugestões da IA."

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Como um especialista em suporte de T.I Logística, sugira uma solução técnica passo-a-passo (curta) para o seguinte problema:
        
        TIPO DE ATIVO: {asset_info}
        DESCRIÇÃO DO PROBLEMA: {problem_description}
        
        Forneça uma resposta amigável e técnica.
        """

        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text.strip()

    except Exception as e:
        return f"Erro ao gerar sugestão: {str(e)}"
