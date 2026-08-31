import subprocess, time, socket, os, sys
sys.stdout.reconfigure(encoding='utf-8')

os.system("taskkill /F /IM StarOcean.exe 2>nul")
time.sleep(2)

exe = os.path.abspath(r"build\Release\StarOcean.exe")
cwd = os.path.dirname(exe)
env = os.environ.copy()
env["SNESRECOMP_FPS"] = "1"
env["SNESRECOMP_NO_DEBUG_WINDOW"] = "1"

print(f"Launching: {exe}")
print(f"CWD: {cwd}")
proc = subprocess.Popen([exe], cwd=cwd, env=env, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"PID: {proc.pid}")

# Poll for debug server
for i in range(30):
    time.sleep(1)
    if proc.poll() is not None:
        print(f"Process exited with code {proc.returncode}")
        break
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 13308))
        s.settimeout(2)
        try:
            banner = s.recv(4096)
            print(f"Connected at attempt {i+1}! Banner: {banner[:100]}")
        except socket.timeout:
            print(f"Connected at attempt {i+1}! (no banner)")
        s.sendall(b'get_status\n')
        time.sleep(0.5)
        resp = s.recv(4096)
        print(f"Response: {resp.decode(errors='replace').strip()[:300]}")
        s.close()
        break
    except (ConnectionRefusedError, OSError) as e:
        print(f"  Attempt {i+1}: {e}")

os.system("taskkill /F /IM StarOcean.exe 2>nul")
