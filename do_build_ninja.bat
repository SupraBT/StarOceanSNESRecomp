@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
cmake -B build_ninja -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=cl.exe >nul 2>&1
ninja -C build_ninja StarOcean.exe
echo EXIT_CODE=%ERRORLEVEL%
