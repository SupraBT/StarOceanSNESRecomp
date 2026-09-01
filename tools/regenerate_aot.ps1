param(
    [string]$RomPath = "Star Ocean (Japan).sfc",
    [string]$OutDir = "out\aot-static",
    [switch]$InPlace,
    [string[]]$ProfileManifest = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
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

git -C (Join-Path $Root "snesrecomp") submodule update --init --recursive
cargo build --release --manifest-path (Join-Path $AnalyzerProject "Cargo.toml")

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

python @EmitArgs
