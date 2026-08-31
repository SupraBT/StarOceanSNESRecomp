#!/usr/bin/env python3
"""Final FPS benchmark — measures without TCP to avoid debug server overhead.
Auto-kills the exe to prevent orphaned processes."""
import sys, time, subprocess, os, signal

EXE = os.path.join(os.path.dirname(__file__), "..", "build", "Release", "StarOcean.exe")
EXE = os.path.normpath(EXE)
DURATION = 20  # seconds

def main():
    if not os.path.exists(EXE):
        print(f"ERROR: {EXE} not found")
        sys.exit(1)
    
    env = os.environ.copy()
    env["SNESRECOMP_FPS"] = "1"
    
    print(f"Starting {EXE} (no TCP, FPS counter enabled)")
    proc = subprocess.Popen(
        [EXE],
        cwd=os.path.dirname(EXE),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
        text=True
    )
    
    fps_values = []
    start = time.time()
    try:
        for line in proc.stdout:
            line = line.strip()
            if "[fps]" in line:
                # Extract FPS value
                try:
                    fps = int(line.split("[fps]")[1].split("fps")[0].strip())
                    fps_values.append(fps)
                    elapsed = time.time() - start
                    sys.stderr.write(f"\r  [{elapsed:.1f}s] FPS={fps}  avg={sum(fps_values)/len(fps_values):.1f}  min={min(fps_values)}  max={max(fps_values)}  samples={len(fps_values)}")
                    sys.stderr.flush()
                except (ValueError, IndexError):
                    pass
            
            if time.time() - start > DURATION:
                break
    except KeyboardInterrupt:
        pass
    finally:
        # ALWAYS kill the process
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except:
                pass
        # Double-check
        os.system("taskkill /F /IM StarOcean.exe 2>nul")
    
    print()
    if fps_values:
        # Skip first 10 samples (boot), focus on steady-state
        steady = fps_values[10:] if len(fps_values) > 10 else fps_values
        print(f"\n=== RESULTS ({DURATION}s) ===")
        print(f"  All frames:  avg={sum(fps_values)/len(fps_values):.1f}  min={min(fps_values)}  max={max(fps_values)}")
        if steady:
            print(f"  Steady-state: avg={sum(steady)/len(steady):.1f}  min={min(steady)}  max={max(steady)}")
        print(f"  Samples: {len(fps_values)}")
    else:
        print("  No FPS data captured!")

if __name__ == "__main__":
    main()
