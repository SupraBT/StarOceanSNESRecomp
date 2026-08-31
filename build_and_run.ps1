$ErrorActionPreference = "Continue"
$vcvars = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
$projDir = "E:\Recompilador Super Nintendo\StarOceanTest2"
$logFile = "E:\Recompilador Super Nintendo\build_run_log.txt"

# Run vcvars and build
cmd /c "call `"$vcvars`" >nul 2>&1 && cd /d `"$projDir`" && cmake --build build 2>&1"
$buildExit = $LASTEXITCODE

# Log build result
"`nBUILD_EXIT_CODE=$buildExit" | Out-File -Append $logFile

# Run the exe
if ($buildExit -eq 0) {
    "`n=== RUNNING EXE ===" | Out-File -Append $logFile
    $exePath = "$projDir\build\starocean.exe"
    if (Test-Path $exePath) {
        & $exePath 2>&1 | Out-File -Append $logFile
        "`nEXE_EXIT=$LASTEXITCODE" | Out-File -Append $logFile
    } else {
        "`nEXE NOT FOUND at $exePath" | Out-File -Append $logFile
    }
} else {
    "`nBUILD FAILED - skipping exe" | Out-File -Append $logFile
}
"=== DONE ===" | Out-File -Append $logFile
