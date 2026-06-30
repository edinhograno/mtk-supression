param(
    [switch]$Clean
)

$root = $PSScriptRoot
Set-Location $root

if ($Clean -and (Test-Path "$root\dist")) {
    Remove-Item -Recurse -Force "$root\dist", "$root\build" -ErrorAction SilentlyContinue
    Write-Host "Cleaned dist/ and build/"
}

Write-Host "Building..."
pyinstaller build.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

$exe = "$root\dist\mtk-noise-canceller.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "OK -> dist\mtk-noise-canceller.exe ($size MB)" -ForegroundColor Green
} else {
    Write-Host "Build finished but exe not found" -ForegroundColor Yellow
}
