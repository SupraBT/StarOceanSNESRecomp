@echo off
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2\cosim"
"E:\Recompilador Super Nintendo\StarOceanTest2\cosim\drive_bsnesplus.exe" "..\Star Ocean (Japan).sfc" --input 378:14:100 --input 506:10:100 --input 552:8:100 --input 610:8:100 --input 711:9:100 --input 12210:5:100 --input 12543:7:100 --input 13111:7:100 --input 13498:7:100 --input 14089:7:100 --input 14425:6:100 --input 14837:7:100 --input 15353:10:100 --input 15657:12:100 --input 16149:8:100 --input 16526:11:100 --input 17068:12:100 --input 17429:10:100 --input 18014:12:100 --input 18346:16:10 --frames 18942 --state-out oracle_full2_state.bin --video-out oracle_full2\f --video-window 14501 18942 > oracle_full2.log 2>&1
echo ERRORLEVEL=%ERRORLEVEL%
