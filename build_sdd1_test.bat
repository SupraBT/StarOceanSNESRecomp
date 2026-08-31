@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
cl /nologo /O2 /I snesrecomp\runner\src\snes sdd1_engine_test.c snesrecomp\runner\src\snes\sdd1.c /Fe:sdd1_engine_test.exe
