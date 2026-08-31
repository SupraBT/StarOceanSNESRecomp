@echo off
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
set SNES_COSIM_OFF=1
set SNES_COSIM_AUDIO=1
set SNESRECOMP_PPU_DEBUG=1
"build-cosim\so_cosim.exe" "Star Ocean (Japan).sfc" --input 301:14:100 --input 429:10:100 --input 475:8:100 --input 533:8:100 --input 634:9:100 --input 12133:5:100 --input 12466:7:100 --input 13034:7:100 --input 13421:7:100 --input 14012:7:100 --input 14348:6:100 --input 14760:7:100 --frames 14800 > cosim\ppudbg_run.log 2>&1
echo EXIT=%ERRORLEVEL%
