cd "E:\Recompilador Super Nintendo\StarOceanTest2\build\Release"
Start-Process -FilePath ".\StarOcean.exe" -RedirectStandardError "E:\Recompilador Super Nintendo\StarOceanTest2\build\test_stderr.txt" -NoNewWindow
Start-Sleep -Seconds 6

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Threading;

[StructLayout(LayoutKind.Sequential)]
struct INPUT {
    public uint type;
    public INPUTUNION U;
}
[StructLayout(LayoutKind.Explicit)]
struct INPUTUNION {
    [FieldOffset(0)] public KEYBDINPUT ki;
}
[StructLayout(LayoutKind.Sequential)]
struct KEYBDINPUT {
    public ushort wVk;
    public ushort wScan;
    public uint dwFlags;
    public uint time;
    public IntPtr extraInfo;
}

public class SI {
    const uint INPUT_KEYBOARD = 1;
    const uint KEYEVENTF_KEYDOWN = 0;
    const uint KEYEVENTF_KEYUP = 2;
    const ushort VK_X = 0x58;

    [DllImport("user32.dll", SetLastError=true)]
    static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr hWnd);

    public static void PressX() {
        INPUT[] inputs = new INPUT[2];
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].U.ki.wVk = VK_X;
        inputs[0].U.ki.dwFlags = KEYEVENTF_KEYDOWN;
        inputs[1].type = INPUT_KEYBOARD;
        inputs[1].U.ki.wVk = VK_X;
        inputs[1].U.ki.dwFlags = KEYEVENTF_KEYUP;
        SendInput(2, inputs, Marshal.SizeOf(typeof(INPUT)));
    }
}
"@

# Bring SDL window to foreground
$procs = Get-Process -Name "StarOcean" -ErrorAction SilentlyContinue
if ($procs) {
    $hwnd = $procs[0].MainWindowHandle
    if ($hwnd -ne [IntPtr]::Zero) {
        [void][SI]::SetForegroundWindow($hwnd)
        Write-Host "Focused window: $hwnd"
    }
}
Start-Sleep -Seconds 2

for ($i = 1; $i -le 4; $i++) {
    Write-Host "Pressing X/SNES-A ($i/4)..."
    [SI]::PressX()
    Start-Sleep -Seconds 5
}
Start-Sleep -Seconds 5

Get-Process -Name "StarOcean" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

Write-Host "=== RELEVANT LOG ==="
Get-Content "E:\Recompilador Super Nintendo\StarOceanTest2\build\test_stderr.txt" | Select-String "SDD1_MODE0|BGMODE 1->0|VRAM_M0.*dump 1|frame 1[2-9]|frame 2" | Select-Object -First 20
