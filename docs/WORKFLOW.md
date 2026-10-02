# Flujo de trabajo: el arbol canonico y como se publica

Este documento existe porque durante semanas el proyecto tuvo **varias copias del
mismo arbol** y eso costo tiempo real: se edito un arbol que no era el que se
compilaba, se leyo un README que describia otro estado, y en una sesion se
persiguio un "arbol de las 10:44" que no estaba en ninguna copia de seguridad.
Ahora hay **un solo arbol canonico** y este es el trato.

## 1. Cual es el arbol canonico

**Raiz del entorno: `E:\Experimento Hermes\`.** Todo lo que se toca vive
DENTRO de ella (regla del 2026-10-02).

El arbol canonico es `E:\Experimento Hermes\StarOceanRecomp`, un **clon de git**
de <https://github.com/SupraBT/StarOceanSNESRecomp> (rama `main`), con el motor
en el submodulo `snesrecomp` (<https://github.com/SupraBT/snesrecomp>), pinado a
un commit concreto. La documentacion y las trazas de apoyo tambien estan dentro
de la raiz:

- `E:\Experimento Hermes\Documentacion\` - layout de ROM, SDD-1, SPC700,
  `rg.exe` y `TracesMesen\` (trazas de Mesen).
- `E:\Experimento Hermes\Decompilacion\` - Ghidra, ROM, trazas de ejecucion,
  ServidorLUA, MesenCE.
- `E:\Experimento Hermes\Snesrecomp\` y `E:\Experimento Hermes\SDL3\` -
  motor de referencia y multimedia.

Todo lo demas es **historico y no se edita**:

- `StarOceanRecomp-legacy-<fecha>` - la carpeta de trabajo anterior a la
  conversion (se conserva como copia de seguridad).
- `StarOceanRecomp-win-1.0` - paquete distribuible.

**Fuera de la raiz** quedan copias antiguas (`E:\Recompilador Super Nintendo\...`,
`E:\Copia de Seguridad Recompilador\...`, `F:\...`). La documentacion antigua
las cita por su ruta historica, pero **no se abren ni se usan sin autorizacion
expresa del usuario**.

Si algo de esas copias parece mas nuevo, casi seguro **no lo es**: el 2026-09-29
el `README.md` y el `.gitignore` locales eran de semanas antes y publicarlos
habria borrado el texto de publicacion y el `generated/` con mas cobertura AOT.
Comparar antes de copiar: `git diff HEAD -- <fichero>`.

## 2. Que se versiona y que no

| versionado | ignorado (por `.gitignore`) |
| --- | --- |
| fuentes (`src/`), motor (submodulo), perfiles (`config/`), AOT (`generated/`), docs, `tools/` | builds (`build-*/`), ROMs (`*.sfc`), configs de ejecucion (`config.ini`, `keybinds.ini`, `rom.cfg`), logs, trazas, binarios |

Nada que viva dentro de un `build-*/` es fuente: se recrea con cmake. Las ROMs no
se publican nunca (el repo no contiene datos del cartucho).

## 3. Los builds y para que sirve cada uno

| directorio | que es | para que |
| --- | --- | --- |
| `build-dev` | build **instrumentado** (sin `SNESRECOMP_CLEAN_BUILD`) | la puerta A/B, `SNESRECOMP_EXIT_AT_FRAME`, `FRAME_STATE`, `PHASE_MS`, `PCM_DUMP`, `DSPREG_TRACE_FILE`... |
| `build-clean` | release `SNESRECOMP_CLEAN_BUILD=ON` | referencia congelada para comparar por oido |
| `build-clean-test` | release `CLEAN_BUILD=ON` | el que se juega |
| `build-prof` | instrumentado + `SNESRECOMP_INTERP_PROFILE` | reparto del coste por funcion (necesita `generated/` regenerado con el perfil) |

```bash
cmake -S . -B build-dev   -G "Visual Studio 17 2022" -DSNESRECOMP_SDL_BACKEND=SDL3 -DSDL3_DIR="E:/Experimento Hermes/SDL3/cmake"
cmake -S . -B build-clean -G "Visual Studio 17 2022" -DSNESRECOMP_SDL_BACKEND=SDL3 -DSNESRECOMP_CLEAN_BUILD=ON -DSDL3_DIR="E:/Experimento Hermes/SDL3/cmake"
cmake --build build-dev --config Release
```

Cada build tiene su `Star Ocean (Japan).sfc`, su `rom.cfg` y su `config.ini`
locales: por eso pueden coexistir sin pisarse.

## 4. Publicar un cambio (main directo)

1. **Editar** con `git status` a la vista: solo debe aparecer lo que estas
   tocando. Si aparece ruido, para y mira el punto 7.
2. **Pasar la puerta**: `python tools/verificar.py` (audio + fps + A/B
   byte-exacto + determinismo + turbo).
3. **Commit** pequeno, con el *por que* en el mensaje, no el *que*.
4. **Push**: el hook `tools/hooks/pre-push` recompila `build-dev` y vuelve a
   pasar la puerta (sin `fps`, que es la unica prueba sensible a la carga de la
   maquina). Si falla, el push no sube.
   Escape consciente para trabajo en curso: `SNESRECOMP_SKIP_GATE=1 git push`.
5. **Si el cambio toca el motor** (todo lo que este bajo `snesrecomp/`): commit y
   push **primero** en `snesrecomp`, y despues en el padre actualizando el pin:

   ```bash
   cd snesrecomp && git add -A && git commit -m "..." && git push origin main
   cd .. && git add snesrecomp && git commit -m "Bump the engine submodule"
   ```

   Nunca al reves: el padre no debe apuntar a un commit que el motor aun no
   tiene publicado.

## 5. Configuracion del clon

Local al clon (no global), ya aplicada:

```bash
git config user.name  "SupraBT"
git config user.email "eugeniocamilofernandez@gmail.com"
git config core.hooksPath tools/hooks
```

`user.*` esta puesto para que el autor de los commits coincida con el de GitHub;
si prefieres otro, cambialo aqui.

## 6. Trazas de hardware (Mesen) — el UNICO oraculo

**Decision 2026-10-02: bsnes queda retirado.** Solo se usa Mesen, que vive en
el proyecto: `E:\Experimento Hermes\Decompilacion\MesenCE-master\Mesen.exe`.
Nada de bsnes (libretro, bsnes-plus, `StarOceanTest2`) sin autorizacion expresa.

Las trazas de la maquina real viven fuera del repo pero DENTRO de la raiz, en
`E:\Experimento Hermes\Documentacion\TracesMesen`: el `.tsv` por frame, el de
eventos, el `.log` de estado y el `_replay.txt` con las pulsaciones. El script que las
genera es `tools/mesen_so_trace.lua` y el replay esta en el formato que come
`SNESRECOMP_REPLAY_FILE`, asi que se puede reproducir la partida exacta en el
recompilador y comparar frame a frame.

## 7. Cuando `git status` ensena cosas que no has tocado

Señal de que estas en el arbol equivocado o de que algo no esta ignorado:

- **Ruido de builds**: si aparece un `build-*` nuevo, anade la excepcion al
  `.gitignore` en el mismo commit que lo crea.
- **Ficheros del motor que no conoces**: el build compila
  `snesrecomp/runner/src/common_rtl.c`; la copia `runner/src/snes/common_rtl.c`
  es un **duplicado que no entra en el enlace** y ya no existe en el clon. Si
  vuelve a aparecer, no lo edites.
- **Diferencias de fin de linea**: el repo guarda LF y el checkout de Windows
  trabaja en CRLF (`core.autocrlf=true`). Un `git diff` de un fichero entero
  suele ser eso, no un cambio real.
