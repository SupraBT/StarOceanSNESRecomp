@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
ninja -C build -t clean so_rtl.c.o 2>nul
ninja -C build build/runners/starOceanTest2/CMakeFiles/StarOcean.dir/src/so_rtl.c.obj 2>&1
echo BUILD_EXIT=%ERRORLEVEL%
