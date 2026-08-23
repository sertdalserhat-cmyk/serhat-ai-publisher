$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$pythonCandidates = @(
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if (-not $pythonCandidates) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("Python 3.11 veya üzeri bulunamadı.", "Serhat AI Publisher") | Out-Null
    exit 1
}

$python = $pythonCandidates[0]
if ([IO.Path]::GetFileName($python) -eq "py.exe") {
    & $python -3.11 -m src.webapp
} else {
    & $python -m src.webapp
}
