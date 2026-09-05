param(
    [string]$RomPath = "Star Ocean (Japan).sfc",
    [string]$OutDir = "out\aot-static",
    [switch]$InPlace,
    [string[]]$ProfileManifest = @(),
    [string]$Python = "",
    [string]$ExpectedSha1 = "A616EE3466256482BC0ADC11F1FDA7C30E66EF8D",
    [string]$ExpectedSha256 = "",
    [switch]$AllowPatchedRom
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
# El toolchain v2 (recompiler python + analizador nativo) vive en el submodulo
# snesrecomp/ (fork SupraBT/snesrecomp). El build del exe solo necesita el
# generated/ resultante.
$AnalyzerProject = Join-Path $Root "snesrecomp\recompiler-rs"
$Analyzer = Join-Path $AnalyzerProject "target\release\snesrecomp-analyze.exe"
$Rom = if ([System.IO.Path]::IsPathRooted($RomPath)) {
    $RomPath
} else {
    Join-Path $Root $RomPath
}
$Output = if ($InPlace) {
    Join-Path $Root "generated"
} elseif ([System.IO.Path]::IsPathRooted($OutDir)) {
    $OutDir
} else {
    Join-Path $Root $OutDir
}

if (-not (Test-Path -LiteralPath $Rom -PathType Leaf)) {
    throw "ROM not found: $Rom"
}

$RomLeaf = [System.IO.Path]::GetFileNameWithoutExtension($Rom)
if (-not $AllowPatchedRom -and $RomLeaf -match '(?i)(\btr\b|translated|traducida|patched|patch|hack)') {
    throw "Refusing likely patched ROM '$([System.IO.Path]::GetFileName($Rom))'. Use an unmodified authentic dump for AOT/config work, or pass -AllowPatchedRom for diagnostics only."
}

if (-not $AllowPatchedRom -and $ExpectedSha1) {
    $ActualSha1 = (Get-FileHash -Algorithm SHA1 -LiteralPath $Rom).Hash
    if ($ActualSha1 -ne $ExpectedSha1) {
        throw "ROM SHA1 mismatch. Expected authentic Star Ocean (Japan) SHA1 $ExpectedSha1, got $ActualSha1. Pass -AllowPatchedRom for diagnostics only."
    }
}

if (-not $AllowPatchedRom -and $ExpectedSha256) {
    $ActualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Rom).Hash
    if ($ActualSha256 -ne $ExpectedSha256) {
        throw "ROM SHA256 mismatch. Expected $ExpectedSha256, got $ActualSha256."
    }
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

function Resolve-Python {
    if ($Python) {
        return @($Python)
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        return @($launcher.Source, "-3")
    }

    $candidate = Get-Command python -All |
        Where-Object {
            $_.Source -notmatch "\\(msys2|msys64|cygwin)\\" -and
            $_.Source -notmatch "\\devkitPro\\"
        } |
        Select-Object -First 1

    if (-not $candidate) {
        throw "No Windows Python found. Pass -Python with an absolute python.exe path."
    }

    return @($candidate.Source)
}

# Asegura el runner (submodulo) para que el build posterior encuentre runner.cmake
Invoke-Checked "git" @("-C", (Join-Path $Root "snesrecomp"), "submodule", "update", "--init", "--recursive")
Invoke-Checked "cargo" @("build", "--release", "--manifest-path", (Join-Path $AnalyzerProject "Cargo.toml"))

$env:SNESRECOMP_NATIVE_ANALYZER = $Analyzer
$EmitArgs = @(
    (Join-Path $Root "snesrecomp\tools\v2_emit.py"),
    "--rom", $Rom,
    "--cfg-dir", (Join-Path $Root "config"),
    "--out-dir", $Output,
    "--cfg-roots"
)

foreach ($manifest in $ProfileManifest) {
    $EmitArgs += @("--profile-manifest", $manifest)
}

$PythonCommand = Resolve-Python
$PythonExe = $PythonCommand[0]
$PythonArgs = @()
if ($PythonCommand.Length -gt 1) {
    $PythonArgs += $PythonCommand[1..($PythonCommand.Length - 1)]
}
$PythonArgs += $EmitArgs

Invoke-Checked $PythonExe $PythonArgs
