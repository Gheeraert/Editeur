# Recette de génération de l'exécutable Windows d'Éditeur avec Nuitka.
#
# Usage (depuis la racine du dépôt) :
#   powershell -File scripts\build_windows.ps1
#
# Prérequis :
#   - Windows, avec Microsoft Word installé (pywin32 pilote Word via COM) ;
#   - Python 3.11+ ;
#   - un compilateur C (MinGW64 ou MSVC). Nuitka propose de télécharger et
#     d'installer un MinGW64 portable automatiquement si aucun compilateur
#     n'est trouvé (voir --assume-yes-for-downloads ci-dessous).
#
# Résultat : dist\editeur.exe (dossier non suivi par Git, voir .gitignore).

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

python -m pip install --quiet -r requirements.txt

python -m pip show nuitka *> $null
if ($LASTEXITCODE -ne 0) {
    python -m pip install --quiet nuitka
}

# main.py insère src/ dans sys.path à l'exécution ; Nuitka a besoin de la
# même information au moment de la compilation pour résoudre le paquet.
$env:PYTHONPATH = Join-Path $RepoRoot "src"

python -m nuitka main.py `
    --standalone `
    --onefile `
    --enable-plugin=tk-inter `
    --include-package=purh_editorial `
    --windows-console-mode=disable `
    --assume-yes-for-downloads `
    --output-dir=dist `
    --output-filename=editeur.exe `
    --company-name="PURH" `
    --product-name="Editeur" `
    --file-description="Correcteur ortho-typographique PURH" `
    --file-version=0.1.0 `
    --product-version=0.1.0

Write-Host "Exécutable généré : dist\editeur.exe"
