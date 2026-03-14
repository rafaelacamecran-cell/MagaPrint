import subprocess
from openai import OpenAI

# Configuração da IA para gerar scripts específicos se necessário
client = OpenAI(api_key="SUA_CHAVE")

def gerar_comando_impressora(modelo, caminho_rede):
    """
    Usa a IA para garantir que o comando PowerShell 
    seja compatível com o modelo específico.
    """
    prompt = f"Gere apenas uma linha de comando PowerShell para instalar a impressora '{modelo}' no caminho '{caminho_rede}'."
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def mapear_remoto(hostname, comando_ps):
    """
    Executa o comando PowerShell na máquina remota via Invoke-Command.
    Nota: Exige privilégios de Admin e WinRM habilitado.
    """
    try:
        # Comando para rodar via PowerShell do seu PC para o remoto
        script_remoto = f"Invoke-Command -ComputerName {hostname} -ScriptBlock {{ {comando_ps} }}"
        subprocess.run(["powershell", "-Command", script_remoto], check=True)
        print(f"✅ Sucesso em: {hostname}")
    except Exception as e:
        print(f"❌ Erro em {hostname}: {e}")

# --- EXECUÇÃO EM MASSA ---
lista_maquinas = ["PC-SALA01", "PC-SALA02", "192.168.1.50"] # Sua lista de 100 máquinas
modelo_printer = "HP LaserJet M404"
caminho_printer = r"\\servidor-print\hp-financeiro"

# 1. IA prepara o comando
comando_ideal = gerar_comando_impressora(modelo_printer, caminho_printer)
print(f"Comando gerado pela IA: {comando_ideal}")

# 2. Python distribui para as 100 máquinas
for pc in lista_maquinas:
    mapear_remoto(pc, comando_ideal)