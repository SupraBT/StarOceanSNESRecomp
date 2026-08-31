@echo off
set "MSVC=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207"
set "SDK=C:\Program Files (x86)\Windows Kits\10"
set "SDKVER=10.0.26100.0"
set "PATH=%MSVC%\bin\Hostx64\x64;%SDK%\bin\%SDKVER%\x64;%PATH%"
set "INCLUDE=%MSVC%\include;%SDK%\Include\%SDKVER%\ucrt;%SDK%\Include\%SDKVER%\shared;%SDK%\Include\%SDKVER%\um;%SDK%\Include\%SDKVER%\winrt"
set "LIB=%MSVC%\lib\x64;%SDK%\Lib\%SDKVER%\ucrt\x64;%SDK%\Lib\%SDKVER%\um\x64"

cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"

echo [1] Testing cl.exe...
cl.exe 2>nul | head -1
echo [2] Compiling ppu.c...
cl.exe /nologo /c /Od /Zi /RTC1 /std:c11 /MDd /W3 ^
  /DWIN32 /D_WINDOWS /DNOMINMAX /DSNESRECOMP_SDL3=1 /DLNG_SDL3=1 ^
  /DSNESRECOMP_BUILD_VERSION=\"dev\" /DSNESRECOMP_ENABLE_MODS=0 ^
  /DSNESRECOMP_POST_MORTEM_TIER2=1 /DSNESRECOMP_REVERSE_DEBUG=0 ^
  /DSNESRECOMP_TRACE=0 /DSNESRECOMP_LAUNCHER=1 /DSO_DEBUG_PORT=13308 ^
  /D_CRT_SECURE_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS ^
  /I src /I snesrecomp\runner\src /I snesrecomp\runner\src\snes ^
  /I snesrecomp\runner\src\desktop /I generated /I "E:\SDL3\include" ^
  /showIncludes ^
  /Fo"build\CMakeFiles\StarOcean.dir\snesrecomp\runner\src\snes\ppu.c.obj" ^
  snesrecomp\runner\src\snes\ppu.c > "E:\Recompilador Super Nintendo\ppu_compile_log.txt" 2>&1

echo [3] Result: %ERRORLEVEL%
echo RESULT_%ERRORLEVEL% > "E:\Recompilador Super Nintendo\ppu_build_ok.txt"
