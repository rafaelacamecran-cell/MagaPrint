import streamlit as st
import pandas as pd
from openai import OpenAI
import subprocess
import os

# Configuração da IA via Variável de Ambiente
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "SUA_CHAVE_AQUI"))

def gerar_ps_script(modelo, caminho):
    """Usa IA para gerar o comando de mapeamento perfeito"""
    prompt = f"Gere apenas o comando PowerShell para mapear a impressora '{modelo}' no caminho '{caminho}'. Use Add-Printer."
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# --- INTERFACE ---
st.set_page_config(page_title="Deployer de Impressoras IA", layout="wide")
st.title("🖨️ Printer Deployer Nível Analista N3")

with st.sidebar:
    st.header("Configurações")
    modelo_printer = st.text_input("Modelo da Impressora", "HP LaserJet M404")
    caminho_printer = st.text_input("Caminho de Rede", r"\\servidor\impressora")
    
    st.divider()
    if st.button("Validar Comando com IA"):
        comando = gerar_ps_script(modelo_printer, caminho_printer)
        st.code(comando, language="powershell")
        st.session_state['comando_validado'] = comando

# Área Central
st.subheader("Lista de Máquinas")
txt_maquinas = st.text_area("Cole os Hostnames ou IPs (um por linha)", "PC-USER-01\nPC-USER-02")
lista_pcs = [line.strip() for line in txt_maquinas.split('\n') if line.strip()]

if st.button("🚀 Iniciar Mapeamento em Massa"):
    if 'comando_validado' not in st.session_state:
        st.error("Por favor, valide o comando com a IA na barra lateral primeiro!")
    else:
        comando_final = st.session_state['comando_validado']
        resultados = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, pc in enumerate(lista_pcs):
            status_text.text(f"Instalando em: {pc}...")
            
            # Comando remoto via PowerShell Invoke-Command
            # Nota: Requer WinRM habilitado no parque de máquinas
            shell_cmd = f"Invoke-Command -ComputerName {pc} -ScriptBlock {{ {comando_final} }} -ErrorAction Stop"
            
            try:
                # Simulando a execução (Para testar local, use shell=True)
                process = subprocess.run(["powershell", "-Command", shell_cmd], capture_output=True, text=True, timeout=15)
                
                if process.returncode == 0:
                    resultados.append({"Máquina": pc, "Status": "✅ Sucesso", "Log": "OK"})
                else:
                    resultados.append({"Máquina": pc, "Status": "❌ Falha", "Log": process.stderr})
            except Exception as e:
                resultados.append({"Máquina": pc, "Status": "⚠️ Erro de Conexão", "Log": str(e)})
            
            progress_bar.progress((i + 1) / len(lista_pcs))

        # Exibição do Relatório Final
        st.divider()
        st.subheader("Relatório de Execução")
        df = pd.DataFrame(resultados)
        st.table(df)
        
        # Opção de exportar para Excel/CSV
        st.download_button("Baixar Relatório", df.to_csv(index=False), "relatorio_impressoras.csv")