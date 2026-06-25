# PowerShell script to prepare flat Hugging Face Spaces deployment directory
$workspaceDir = "c:\Users\AUM\OneDrive\Documents\Project 1\India Runs"
$deployDir = "$workspaceDir\hf_deploy_tmp"

# Clean previous deployment folder
if (Test-Path $deployDir) {
    Write-Host "Cleaning existing deployment directory: $deployDir..."
    Remove-Item -Recurse -Force $deployDir
}

# Recreate folder structure
Write-Host "Creating deployment folders..."
New-Item -ItemType Directory -Path $deployDir | Out-Null
New-Item -ItemType Directory -Path "$deployDir\.streamlit" | Out-Null

# Copy requirements.txt to root
Copy-Item "$workspaceDir\verdikt\requirements.txt" -Destination "$deployDir\requirements.txt"

# Copy local Streamlit config.toml if it exists, otherwise generate default
Write-Host "Configuring Streamlit settings..."
if (Test-Path "$workspaceDir\verdikt\.streamlit\config.toml") {
    Write-Host "Copying local Streamlit config..."
    Copy-Item "$workspaceDir\verdikt\.streamlit\config.toml" -Destination "$deployDir\.streamlit\config.toml"
} else {
    Write-Host "Generating default Streamlit config..."
    python -c "import os; os.makedirs(r'$deployDir\.streamlit', exist_ok=True); f = open(r'$deployDir\.streamlit\config.toml', 'w', encoding='utf-8'); f.write('[server]\nheadless = true\nenableCORS = false\nenableXsrfProtection = false\nmaxUploadSize = 100\n'); f.close()"
}

# Create README.md with Hugging Face Space metadata
# Copy source files to root (excluding large datasets, requirements, and README.md)
Write-Host "Copying sandbox source files..."
$sourceFiles = Get-ChildItem "$workspaceDir\verdikt" -File
foreach ($file in $sourceFiles) {
    $name = $file.Name
    if ($name -eq "candidates.jsonl" -or $name -eq "sample_candidates.jsonl" -or $name -eq "requirements.txt" -or $name -eq "README.md") {
        Write-Host "Skipping dataset/root/doc file: $name"
        continue
    }
    Copy-Item $file.FullName -Destination "$deployDir\$name"
}

# Copy auth folder recursively
if (Test-Path "$workspaceDir\verdikt\auth") {
    Write-Host "Copying auth folder..."
    Copy-Item "$workspaceDir\verdikt\auth" -Destination "$deployDir\auth" -Recurse -Force
}

# Clean __pycache__ folders in deployDir
Write-Host "Cleaning __pycache__ folders..."
Get-ChildItem -Path $deployDir -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force



# Create README.md combining Hugging Face Space YAML metadata and our project README
Write-Host "Creating merged README.md..."
@'
import sys
import os
deploy_dir = sys.argv[1]
workspace_dir = sys.argv[2]

metadata = """---
title: Calipr AI
emoji: \U0001F3C6
colorFrom: indigo
colorTo: purple
sdk: streamlit
sdk_version: 1.38.0
app_file: app.py
pinned: false
---

"""

readme_path = os.path.join(workspace_dir, 'verdikt', 'README.md')
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
else:
    readme_content = ""

with open(os.path.join(deploy_dir, 'README.md'), 'w', encoding='utf-8') as f:
    f.write(metadata + readme_content)
'@ | Out-File -FilePath "$deployDir\make_metadata.py" -Encoding utf8
python "$deployDir\make_metadata.py" "$deployDir" "$workspaceDir"
Remove-Item "$deployDir\make_metadata.py"

# Initialize fresh Git repository
Write-Host "Initializing git repository..."
Set-Location $deployDir
git init
git checkout -b main
git remote add hf-space https://huggingface.co/spaces/Aumus/calipr

# Commit files
git add .
git commit -m "Deploy Streamlit app sandbox to Hugging Face Spaces"

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "Hugging Face deployment files prepared in $deployDir" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "To complete the push, please run the following in your terminal:" -ForegroundColor Yellow
Write-Host "cd '$deployDir'" -ForegroundColor Yellow
Write-Host "git push hf-space main --force" -ForegroundColor Yellow
