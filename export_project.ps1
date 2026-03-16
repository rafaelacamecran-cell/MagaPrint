<#
.SYNOPSIS
Exporta o projeto MagaLabs LogPrint ignorando pastas pesadas como .venv e __pycache__.
.DESCRIPTION
Cria um arquivo .zip contendo apenas os dados essenciais do projeto para que seja
fácil e rápido transferir via pendrive.
#>

$sourceDirectory = "."
$destinationZip = ".\MagaLabs_Project.zip"

If (Test-Path $destinationZip) {
    Remove-Item $destinationZip -Force
}

$excludeList = @(
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "instance",
    ".idea",
    ".vscode",
    "postgres_data",
    "MagaLabs_Project.zip",
    "export_project.ps1",
    "export_project.sh"
)

Write-Host "Compactando projeto para $destinationZip..." -ForegroundColor Cyan
Write-Host "Ignorando as seguintes pastas: $($excludeList -join ', ')" -ForegroundColor Yellow

# Pega apenas os arquivos que NÃO estão no excludeList
Get-ChildItem -Path $sourceDirectory -Recurse -Force |
    Where-Object { 
        $path = $_.FullName
        $exclude = $false
        foreach ($ex in $excludeList) {
            if ($path -match "\\$ex\\?" -or $path -match "\\$ex$") {
                $exclude = $true
                break
            }
        }
        return -not $exclude
    } | Compress-Archive -DestinationPath $destinationZip -Update

Write-Host "======================================" -ForegroundColor Green
Write-Host "Concluído! Projeto exportado com sucesso." -ForegroundColor Green
Write-Host "Arquivo salvo em: $destinationZip" -ForegroundColor Green
Write-Host "Dica: Você pode copiar o arquivo MagaLabs_Project.zip para seu pendrive!" -ForegroundColor Magenta
Write-Host "Pressione qualquer tecla para fechar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
