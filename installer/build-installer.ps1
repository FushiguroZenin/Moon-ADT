$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'build-runtime.ps1')
if ($LASTEXITCODE -ne 0) { throw "Moon runtime packaging failed with exit code $LASTEXITCODE." }

$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
  $iscc = @(
    "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) {
  $registryKeys = @(
    'HKCU:\Software\Classes\InnoSetupScript\shell\compile\command',
    'HKLM:\Software\Classes\InnoSetupScript\shell\compile\command',
    'HKLM:\Software\WOW6432Node\Classes\InnoSetupScript\shell\compile\command'
  )
  foreach ($key in $registryKeys) {
    try {
      $command = (Get-ItemProperty -Path $key -ErrorAction Stop).'(default)'
      if ($command -match '"([^"]*ISCC\.exe)"') { $candidate = $matches[1] }
      elseif ($command -match '([^\s]+ISCC\.exe)') { $candidate = $matches[1] }
      if ($candidate -and (Test-Path $candidate)) { $iscc = $candidate; break }
    } catch { }
  }
}
if (-not $iscc) { throw 'Inno Setup was not found. Install Inno Setup 6 or 7, then reopen PowerShell and run this script again.' }
& $iscc (Join-Path $PSScriptRoot 'moon.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed with exit code $LASTEXITCODE. Close any running or previewed Moon-Setup.exe, then run the build again." }
Write-Host "Installer created under $root\installer-output"
