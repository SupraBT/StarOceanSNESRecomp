# Submódulo `snesrecomp` — guía de subida a GitHub

`snesrecomp/` (el framework de recompilación, obtenido de `mstan/snesrecomp` y customizado para
Star Ocean) ya está convertido en **submódulo de git** en este repo. Estado verificado:

- `snesrecomp/` es un repo git propio (rama `main`, commit `c759806b`) con el framework
  customizado: D9FF (wait $00D9 de batalla), tier LLE (interp816), debug_server extendido
  (TCP savestate/loadstate), gateo de trazas DMA/S-DD1, y la atribución de origen actualizada.
- El repo principal lo referencia como gitlink (`160000 c759806b...`) + `.gitmodules` apuntando a
  `https://github.com/SupraBT/snesrecomp.git` (el fork de mstan).
- Solo código fuente en el submódulo (runner + toolchain v2 + recompiler-rs — sin binarios ni logs).

## Pasos (recomendado: fork de mstan/snesrecomp)

### 1. Fork en GitHub

En https://github.com/mstan/snesrecomp → botón **Fork** → crea tu fork (quedará en
`https://github.com/SupraBT/snesrecomp.git`). El enlace "forked from mstan/snesrecomp" deja
constancia del origen automáticamente.

### 2. Subir el framework customizado al fork

Nuestro repo local es una fotografía completa del framework (un commit raíz), no comparte
historia con mstan → el push a `main` del fork necesita `--force` (sobrescribe el main del fork
con nuestra versión; la relación de fork con mstan se conserva):

```bash
git -C snesrecomp remote add origin https://github.com/SupraBT/snesrecomp.git
git -C snesrecomp push -u origin main --force
```

> Alternativa sin `--force`: crear un repo VACÍO en GitHub (p. ej. `SNESRecomp-SO`) y hacer un
> push normal, actualizando la URL en `.gitmodules`:
> `sed -i 's|SupraBT/snesrecomp.git|SupraBT/SNESRecomp-SO.git|' .gitmodules && git add .gitmodules`

### 3. Commit y push del repo principal

En la raíz del proyecto (gitlink + `.gitmodules` ya staged):

```bash
git add -A
git commit -m "Proyecto con snesrecomp como submódulo"
git push
```

> El push del repo principal sube el gitlink (hash `c759806b`) y `.gitmodules`; quien clone hará
> `git submodule update --init --recursive` y obtendrá el framework.

## Verificación tras subir

```bash
git submodule status          # debe mostrar c759806b... (sin "-" delante tras init)
git submodule update --init   # en un clon nuevo
```

## Notas

- **Licencia**: PolyForm Noncommercial 1.0.0 (heredada de SNESRecomp) — incluida en el commit
  del submódulo (`LICENSE`).
- **Origen**: el framework se descargó de `mstan/snesrecomp` (comunidad R.A.I.D.); la atribución
  está documentada en `snesrecomp/THIRD_PARTY_ATTRIBUTION.md`. Otras piezas citadas ahí:
  recompiler-rs de `perplexes/snesrecomp`, ares (Cx4), libretro (headers), SDL2.
- El toolchain v2 (v2_emit.py, recompiler-rs, analyzer) ahora vive dentro del submódulo
  en lugar de en una carpeta vendorizada separada.
