@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d "F:\Recompilador Super Nintendo\StarOceanTest2\build-cosim"
ninja so_cosim
