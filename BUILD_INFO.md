# Estructura de Builds — StarOceanTest2

> ⚠️ **Regla de oro:** `1.Release` NO se modifica sin autorización explícita del usuario.

## `1.Release/` — Versión Estable ✅
- **Exe:** `StarOcean.exe` (449KB) — ccc523c + FPS counter + generated minimalista
- **md5:** `4b27b861c14a13c2801efb4b9300bd3e`
- **Base:** commit `ccc523c` (Track B cosim)
- **Features:** Imagen ✅, Música ✅, FPS counter en título ✅
- **generated/:** Minimalista (6 archivos: bank00, bankC0, bankC1, dispatch)
- **NO MODIFICAR** hasta nuevo aviso del usuario

## `2.Beta/` — Versión de Pruebas 🧪
- **Exe:** `StarOcean.exe` (778KB) — build beta con fix APU sync post-loadstate
- **md5:** `3dfdc01ca017e9b5d64086256dc11c99`
- **Base:** mismo ccc523c + `RtlResetApuSyncState()` en common_rtl.c y state_file.c
- **NOTA:** Este exe puede tener problema de pantalla negra (generated/ con 284 AOT extenso)
- **Usar** para testear cambios sin afectar la versión estable

## Cómo compilar una nueva versión Beta

```bash
cd "$PROJECT_ROOT\StarOceanTest2"
# Asegurar que source está en ccc523c
git checkout ccc523c

# Usar generated/ minimalista (el que funciona)
# generated/ debe contener: bank00_v2.c, bankc0_v2.c, bankc1_v2.c, dispatch_v2.c

# Compilar
cmake -S . -B build-beta -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release -DSDL3_DIR="E:/SDL3/cmake" -DSNESRECOMP_TRACE=OFF
cmake --build build-beta --config Release

# Copiar a 2.Beta
cp build-beta/Release/StarOcean.exe 2.Beta/
```

## Archivos necesarios en cada build
- `StarOcean.exe`
- `SDL3.dll`
- `Star Ocean (Japan).sfc` (ROM)
- `config.ini`
- `keybinds.ini`
- `rom.cfg`

## Generated mínimo que funciona
Ubicación de referencia: `<alt-worktree>\generated\`
- `bank00_v2.c` — 571KB (10787 líneas)
- `bankc0_v2.c` — 27KB (694 líneas)
- `bankc1_v2.c` — 446 bytes (17 líneas, stub)
- `dispatch_v2.c` — 9.6KB (154 líneas)
- `program_manifest.json` — 50KB
- `unresolved_stubs_v2.c` — 68 bytes

## Reglas de oro
1. **Nunca verificar con CopyFromScreen** — siempre PrintWindow(hwnd, hdc, 2)
2. **Nunca editar `end:` en las configs** para forzar variantes — causa código AOT corrupto
3. **Siempre verificar audio** tras cada cambio de rendimiento
4. **Si algo se rompe** → revertir a 1.Release y diagnosticar
5. **El generated/ de 284 AOT extenso causa pantalla negra** — usar solo el minimalista
