@echo off
:: Use the pre-configured VS batch environment  
set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
call "%VCVARS%" >nul 2>&1
if errorlevel 1 (
    echo VCVARS_FAILED
    exit /b 1
)
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
echo COMPILING ppu.c...
cl /nologo /c /Zi /Ob0 /Od /RTC1 -std:c11 /MDd /W0 ^
  -DLNG_SDL3=1 -DNOMINMAX -DSDL_MAIN_HANDLED -DSNESRECOMP_BUILD_VERSION=\"dev\" ^
  -DSNESRECOMP_ENABLE_MODS=0 -DSNESRECOMP_POST_MORTEM_TIER2=1 -DSNESRECOMP_REVERSE_DEBUG=0 ^
  -DSNESRECOMP_SDL3=1 -DSNESRECOMP_TRACE=0 -DSNES_LAUNCHER=1 -DSO_DEBUG_PORT=13308 ^
  -D_CRT_SECURE_NO_WARNINGS -D_WINSOCK_DEPRECATED_NO_WARNINGS ^
  -I"src" -I"snesrecomp\runner\src" -I"snesrecomp\runner\src\snes" ^
  -I"snesrecomp\runner\src\desktop" -I"generated" -IE:\SDL3\include ^
  /Fo"build_ninja\CMakeFiles\StarOcean.dir\snesrecomp\runner\src\snes\ppu.c.obj" ^
  "snesrecomp\runner\src\snes\ppu.c"
echo COMPILE_EXIT=%ERRORLEVEL%
if %ERRORLEVEL% EQU 0 (
    echo LINKING...
    cd /d "E:\Recompilador Super Nintendo\StarOceanTest2\build_ninja"
    ninja StarOcean.exe
    echo LINK_EXIT=%ERRORLEVEL%
) else (
    echo COMPILE_FAILED
)
