param([string]$MSBuild = 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe')
$ErrorActionPreference = 'Stop'
& $MSBuild (Join-Path $PSScriptRoot 'AdamHookAlpha.sln') /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo
if ($LASTEXITCODE -ne 0) { throw 'Build failed. Install the .NET Framework 4.8 Developer Pack and Visual Studio desktop development tools.' }
