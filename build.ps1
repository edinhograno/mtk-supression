param(
    [switch]$Clean,
    [switch]$SkipInstaller
)

$root = $PSScriptRoot
Set-Location $root

if ($Clean) {
    Remove-Item -Recurse -Force "$root\dist", "$root\build" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$root\installer\Output" -ErrorAction SilentlyContinue
    Write-Host "Cleaned dist/, build/, installer/Output/"
}

Write-Host "Building exe..."
& .venv\Scripts\pyinstaller build.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$exe = "$root\dist\mtk-noise-canceller.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build finished but exe not found" -ForegroundColor Yellow
    exit 1
}
$exeSize = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "Exe -> dist\mtk-noise-canceller.exe ($exeSize MB)" -ForegroundColor Green

if ($SkipInstaller) {
    Write-Host "Skipping installer (-SkipInstaller)" -ForegroundColor Yellow
    exit 0
}

$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) {
    Write-Host "Inno Setup not found at: $iscc" -ForegroundColor Yellow
    Write-Host "Install from https://jrsoftware.org/isinfo.php or use -SkipInstaller" -ForegroundColor Yellow
    exit 1
}

$version = (& .venv\Scripts\python -c "from version import __version__; print(__version__)").Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to read version from version.py" -ForegroundColor Red
    exit $LASTEXITCODE
}
$issPath = "$root\installer\mtk.iss"
$issContent = (Get-Content $issPath) -replace 'AppVersion=.*', "AppVersion=$version"
[System.IO.File]::WriteAllLines($issPath, $issContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "Injected version $version into mtk.iss"

Write-Host "Building installer..."
& $iscc $issPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "ISCC FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$setup = "$root\installer\Output\mtk-noise-canceller-setup.exe"
if (Test-Path $setup) {
    $setupSize = [math]::Round((Get-Item $setup).Length / 1MB, 1)
    Write-Host "OK -> installer\Output\mtk-noise-canceller-setup.exe ($setupSize MB)" -ForegroundColor Green
} else {
    Write-Host "Installer not found at expected path: $setup" -ForegroundColor Red
    exit 1
}
