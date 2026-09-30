""" hm_parche_hot.py — inserta el disparador de captura automática en los
fotogramas lentos (los que el HUD pinta de rojo) dentro de src/main.c.

Se ejecuta sobre la COPIA del proyecto (E:/Experimento Hermes), nunca sobre el
proyecto original. Idempotente: si el bloque ya esta, no hace nada.
"""
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "src", "main.c")

INC_OLD = "#include <assert.h>\n"
INC_NEW = ("#include <assert.h>\n"
           "#if defined(_WIN32)\n"
           "#  include <direct.h>\n"
           "#  include <sys/stat.h>\n"
           "#else\n"
           "#  include <sys/stat.h>\n"
           "#endif\n")

HELPERS = r'''
/* ── Disparador automático de captura en fotogramas lentos ──────────────────
 * El HUD se pinta de ROJO cuando el fotograma tardó más de SNESRECOMP_HOT_MS
 * (18 ms por defecto ≈ 55 fps): ese es exactamente el "bajón" que ve el
 * jugador. Con SNESRECOMP_HOT=1 cada transición a rojo guarda el fotograma ya
 * dibujado (HUD incluido) en SNESRECOMP_HOT_DIR/f%06d.bmp y escribe una línea
 * [hot] a stderr con frame / ms de ciclo / ms de dibujo / fps, para poder
 * localizar la zona caliente sin tener que mirar la pantalla.
 *
 * El color se decide aquí mismo, así que el trigger y el HUD no pueden
 * discrepar: si sale rojo, hay captura. Se dispara por flanco (no mientras el
 * juego sigue lento) para no llenar el disco con el mismo bajón. */
static int   s_hot_on   = -1;
static int   s_hot_edge = 0;
static int   s_hot_n    = 0;
static double s_hot_ms  = 18.0;
static const char *s_hot_dir = "hotshots";
static int   s_hot_mkdir = 0;

static void HmEnsureDir(const char *dir) {
    if (s_hot_mkdir) return;
    s_hot_mkdir = 1;
#if defined(_WIN32)
    (void)_mkdir(dir);
#else
    (void)mkdir(dir, 0777);
#endif
}

static void HmSaveBmp(const uint8_t *px, int pitch, int w, int h,
                      const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) return;
    const int row = (w * 3 + 3) & ~3;          /* BMP: filas alineadas a 4 */
    const uint32_t data = (uint32_t)row * (uint32_t)h;
    uint8_t hdr[54];
    memset(hdr, 0, sizeof hdr);
    hdr[0] = 'B'; hdr[1] = 'M';
    const uint32_t fsize = 54u + data;
    const uint32_t off   = 54u;
    const uint32_t dib   = 40u;
    const int32_t  iw    = w;
    const int32_t  ih    = -h;                 /* negativo = de abajo arriba */
    const uint16_t planes = 1, bits = 24;
    memcpy(hdr +  2, &fsize,  4);
    memcpy(hdr + 10, &off,    4);
    memcpy(hdr + 14, &dib,    4);
    memcpy(hdr + 18, &iw,     4);
    memcpy(hdr + 22, &ih,     4);
    memcpy(hdr + 26, &planes, 2);
    memcpy(hdr + 28, &bits,   2);
    memcpy(hdr + 34, &data,   4);
    fwrite(hdr, 1, sizeof hdr, f);
    uint8_t *line = (uint8_t *)malloc((size_t)row);
    if (!line) { fclose(f); return; }
    memset(line, 0, (size_t)row);
    for (int x = 0; x < w; x++) {              /* relleno una sola vez */
        for (int b = w * 3; b < row; b++) line[b] = 0;
    }
    for (int y = h - 1; y >= 0; y--) {
        const uint8_t *s = px + (size_t)y * (size_t)pitch;
        for (int x = 0; x < w; x++) {
            line[x * 3 + 0] = s[x * 4 + 2];    /* B */
            line[x * 3 + 1] = s[x * 4 + 1];    /* G */
            line[x * 3 + 2] = s[x * 4 + 0];    /* R */
        }
        fwrite(line, 1, (size_t)row, f);
    }
    free(line);
    fclose(f);
}
'''

DRAW_OLD = """    HmText(px, width * 4, 4, 4, buf, ciclo > 18.0 ? 0xFF0000u : 0xFFFFFFu);
}
"""
DRAW_NEW = """    HmText(px, width * 4, 4, 4, buf, ciclo > 18.0 ? 0xFF0000u : 0xFFFFFFu);

    if (s_hot_on < 0) {
        const char *e = getenv("SNESRECOMP_HOT");
        s_hot_on = (e && e[0] && e[0] != '0') ? 1 : 0;
        const char *m = getenv("SNESRECOMP_HOT_MS");
        if (m && m[0]) { double v = atof(m); if (v > 0.0) s_hot_ms = v; }
        const char *d = getenv("SNESRECOMP_HOT_DIR");
        if (d && d[0]) s_hot_dir = d;
    }
    const int lento = (ciclo > s_hot_ms);
    if (s_hot_on) {
        if (lento && !s_hot_edge) {
            char path[1024];
            snprintf(path, sizeof path, "%s/f%06d.bmp", s_hot_dir,
                     frame_invitado);
            HmEnsureDir(s_hot_dir);
            HmSaveBmp(px, width * 4, width, 224, path);
            s_hot_n++;
            fprintf(stderr,
                    "[hot] f=%d ciclo=%.2fms (umbral %.1f) draw=%.2fms "
                    "fps=%d -> %s  #%d\\n",
                    frame_invitado, ciclo, s_hot_ms, draw, fps, path, s_hot_n);
        } else if (!lento && s_hot_n &&
                   (frame_invitado % 600) == 0) {
            fprintf(stderr, "[hot] f=%d acumulado=%d\\n", frame_invitado,
                    s_hot_n);
        }
    }
    s_hot_edge = lento;
}
"""


def main():
    with io.open(MAIN, "r", encoding="utf-8", errors="surrogateescape") as f:
        src = f.read()
    if "SNESRECOMP_HOT" in src:
        print("ya esta parcheado; no toco nada")
        return
    for old, new, tag in ((INC_OLD, INC_NEW, "includes"),
                          ("static int   s_hud_on = -1;", HELPERS +
                           "\nstatic int   s_hud_on = -1;", "helpers"),
                          (DRAW_OLD, DRAW_NEW, "trigger")):
        if src.count(old) != 1:
            print("FALLO ancla %s (%d coincidencias)" % (tag, src.count(old)))
            return 1
        src = src.replace(old, new)
    with io.open(MAIN, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(src)
    print("OK: trigger de captura en rojo anadido a", MAIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
