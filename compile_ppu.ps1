$env:MSVC = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207"
$env:SDK = "C:\Program Files (x86)\Windows Kits\10"
$env:SDKVER = "10.0.26100.0"
$env:PATH = "$env:MSVC\bin\Hostx64\x64;$env:SDK\bin\$env:SDKVER\x64;$env:PATH"
$env:INCLUDE = "$env:MSVC\include;$env:SDK\Include\$env:SDKVER\ucrt;$env:SDK\Include\$env:SDKVER\shared;$env:SDK\Include\$env:SDKVER\um;$env:SDK\Include\$env:SDKVER\winrt"
$env:LIB = "$env:MSVC\lib\x64;$env:SDK\Lib\$env:SDKVER\ucrt\x64;$env:SDK\Lib\$env:SDKVER\um\x64"

Set-Location "E:\Recompilador Super Nintendo\StarOceanTest2"

$outDir = "build_ninja\CMakeFiles\StarOcean.dir\snesrecomp\runner\src\snes"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Compiling ppu.c..."
& cl.exe /nologo /c /Od /Zi /RTC1 /std:c11 /MDd /W3 `
  /DWIN32 /D_WINDOWS /DNOMINMAX /DSNESRECOMP_SDL3=1 /DLNG_SDL3=1 `
  '/DSNESRECOMP_BUILD_VERSION="dev"' /DSNESRECOMP_ENABLE_MODS=0 `
  /DSNESRECOMP_POST_MORTEM_TIER2=1 /DSNESRECOMP_REVERSE_DEBUG=0 `
  /DSNESRECOMP_TRACE=0 /DSNESRECOMP_LAUNCHER=1 /DSO_DEBUG_PORT=13308 `
  /D_CRT_SECURE_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS `
  /I src /I snesrecomp/runner/src /I snesrecomp/runner/src/snes `
  /I snesrecomp/runner/src/desktop /I generated /I "E:\SDL3\include" `
  /Fo"$outDir\ppu.c.obj" `
  snesrecomp/runner/src/snes/ppu.c 2>&1

if ($LASTEXITCODE -eq 0) {
  Write-Host "COMPILE OK - Relinking..."
  & ninja -C build_ninja 2>&1
  if ($LASTEXITCODE -eq 0) {
    "BUILD_OK" | Out-File "E:\Recompilador Super Nintendo\ppu_build_ok.txt"
    Write-Host "BUILD OK"
  } else {
    "LINK_FAIL" | Out-File "E:\Recompilador Super Nintendo\ppu_build_ok.txt"
    Write-Host "LINK FAILED"
  }
} else {
  "COMPILE_FAIL" | Out-File "E:\Recompilador Super Nintendo\ppu_build_ok.txt"
  Write-Host "COMPILE FAILED"
}
