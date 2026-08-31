@echo off
cd /d "F:\Recompilador Super Nintendo\StarOceanTest2"
cmake --build build-beta --config Release --target StarOcean -- -m 2>&1 | findstr /i "error warning" | findstr /v "C4996"
