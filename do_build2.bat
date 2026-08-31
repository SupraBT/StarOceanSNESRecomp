@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
echo Starting cmake configure...
cmake -B build_ninja -G Ninja -DCMAKE_BUILD_TYPE=Release -DSDL3_DIR="E:\SDL3\cmake" 2>&1 > "E:\Recompilador Super Nintendo\cmake_out.txt"
echo CMAKE_DONE
ninja -C build_ninja -j4 2>&1 > "E:\Recompilador Super Nintendo\ninja_out.txt"
echo NINJA_DONE
echo ALL_DONE > "E:\Recompilador Super Nintendo\build_all_done.txt"
