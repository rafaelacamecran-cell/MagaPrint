#!/bin/bash

# Define nome do arquivo de saida
OUTPUT_ZIP="MagaLabs_Project.zip"

echo -e "\e[36mCompactando projeto para $OUTPUT_ZIP...\e[0m"
echo -e "\e[33mIgnorando pastas pesadas (.venv, .git, __pycache__, etc)...\e[0m"

# Remove zip anterior se existir
if [ -f "$OUTPUT_ZIP" ]; then
    rm "$OUTPUT_ZIP"
fi

# Cria o arquivo zip ignorando as pastas pesadas
zip -r "$OUTPUT_ZIP" . \
    -x "*/\.venv/*" \
    -x "*/venv/*" \
    -x "*/\.git/*" \
    -x "*/__pycache__/*" \
    -x "*/instance/*" \
    -x "*/\.idea/*" \
    -x "*/\.vscode/*" \
    -x "*/postgres_data/*" \
    -x "$OUTPUT_ZIP" \
    -x "export_project.ps1" \
    -x "export_project.sh"

echo -e "\e[32m======================================\e[0m"
echo -e "\e[32mConcluído! Projeto exportado com sucesso.\e[0m"
echo -e "\e[32mArquivo salvo em: $OUTPUT_ZIP\e[0m"
echo -e "\e[35mDica: Você pode copiar o arquivo $OUTPUT_ZIP para seu pendrive!\e[0m"
