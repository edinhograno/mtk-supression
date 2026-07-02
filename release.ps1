param(
    [string]$Tag = "v1.0.0"
)

$envFile = "$PSScriptRoot\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
        }
    }
}

$token = $env:GITHUB_TOKEN
if (-not $token) {
    Write-Host "ERRO: defina GITHUB_TOKEN no arquivo .env" -ForegroundColor Red
    exit 1
}

$repo = "edinhograno/mtk-supression"
$exe  = "$PSScriptRoot\installer\Output\mtk-noise-canceller-setup.exe"

if (-not (Test-Path $exe)) {
    Write-Host "ERRO: setup.exe nao encontrado. Rode .\build.ps1 primeiro." -ForegroundColor Red
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
    Accept        = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$notes = "## MTK Noise Canceller $Tag`n`nNoise cancellation for microphone on Windows via VB-Cable.`n`n### How to use`n1. Run mtk-noise-canceller.exe as administrator`n2. On first run, the app downloads and installs VB-Cable automatically`n3. Select your microphone in the settings window`n4. Enable filter and set Discord/Teams to use CABLE Output as microphone`n`n### Requirements`n- Windows 10/11 (64-bit)`n- Internet connection on first run (VB-Cable download ~5MB)`n- UAC: driver installer requires admin permission"

Write-Host "Criando release $Tag..."
$body = @{
    tag_name   = $Tag
    name       = "$Tag - MTK Noise Canceller"
    body       = $notes
    draft      = $false
    prerelease = $false
} | ConvertTo-Json -Compress

$release = Invoke-RestMethod `
    -Uri "https://api.github.com/repos/$repo/releases" `
    -Method Post `
    -Headers $headers `
    -Body $body `
    -ContentType "application/json; charset=utf-8"

Write-Host "Release criada: $($release.html_url)" -ForegroundColor Green

Write-Host "Fazendo upload do exe..."
$uploadUrl = $release.upload_url -replace '\{.*\}', ''
$fileBytes = [System.IO.File]::ReadAllBytes($exe)

Invoke-RestMethod `
    -Uri "${uploadUrl}?name=mtk-noise-canceller-setup.exe" `
    -Method Post `
    -Headers $headers `
    -Body $fileBytes `
    -ContentType "application/octet-stream" | Out-Null

Write-Host "Upload concluido!" -ForegroundColor Green
Write-Host "Release: $($release.html_url)"
