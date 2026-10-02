/* evlog.c — registro de fotogramas disparado por bajon de FPS. Ver evlog.h.
 *
 * Idea: se guarda UN REGISTRO por fotograma del bucle de host en un anillo
 * circular, siempre (es copiar una struct, no I/O). Cuando el HUD se pone rojo
 * se abre un fichero y se vuelca el historico que ya estaba en el anillo mas el
 * fotograma que disparo, y a partir de ahi se sigue escribiendo hasta que la
 * escena se recupera. Asi el "5 fotogramas antes" sale de un historico REAL y
 * no de haberanticipated que iba a haber un bajon.
 *
 * La condicion de disparo NO se recalcula aqui: la recibe `slow` desde el mismo
 * `ciclo > s_hot_ms` que decide el color del HUD. Un solo sitio decide.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#if defined(_WIN32)
#  include <direct.h>
#  define EV_MKDIR(d) _mkdir(d)
#else
#  include <sys/stat.h>
#  define EV_MKDIR(d) mkdir(d, 0777)
#endif

#include "evlog.h"

#ifdef SNESRECOMP_CLEAN_BUILD

/* Build limpio: el registro de bajones es un monitor de desarrollo, asi que
 * fuera. No es solo question de tamano: la llamada ocurre una vez por
 * fotograma del bucle de host, y el binario de produccion no debe pagar ni
 * esa llamada ni las cadenas de texto de las variables de entorno. La
 * convencion del proyecto (CMakeLists) es que SNESRECOMP_CLEAN_BUILD saque
 * fuera los monitores; este es uno mas. */

int EvLogEnabled(void) { return 0; }
void EvLogFrame(double cycle_ms, double emu_ms, double draw_ms,
                double sdd1_ms, int fps, int frame_invitado, int slow) {
    (void)cycle_ms; (void)emu_ms; (void)draw_ms; (void)sdd1_ms;
    (void)fps; (void)frame_invitado; (void)slow;
}

#else

#include "cpu_state.h"        /* g_cpu, CpuState.master_cycles */
#include "common_cpu_infra.h" /* g_snes */
#include "common_rtl.h"       /* snes_frame_counter */
#include "snes/snes.h"
#include "snes/apu.h"
#include "snes/spc.h"

/* Calibracion del reloj de la traza de Mesen, medida en la ventana de
 * referencia (ver ENCICLOPEDIA §22.25): el `Cycle:` de la traza por instruccion
 * corre sobre el reloj de CPU, y la columna `cyc` del TSV por fotograma corre
 * sobre el mismo maestro, con un desfase fijo de 48766.
 *
 * OJO, dos limites honestos de este numero, y por eso la columna se llama
 * `mesenCycEst` y no `mesenCyc`:
 *   1. La calibracion es de la ventana en la que se midio, no universal.
 *   2. El indice de fotograma NO es una coordenada compartida entre el motor
 *      (arranque HLE) y el hardware (reset de Mesen); el desfase global -27
 *      solo valia en la meseta. Por eso el log lleva `frame` Y `hostLoop` por
 *      separado, para que alinear sea una decision conscious y no una
 *      suposicion escondida. */
#define EV_MESEN_CYCLE_OFFSET 48766ull

typedef struct {
    int      frame;          /* snes_frame_counter: fotograma del INVITADO */
    unsigned hostLoop;       /* vuelta del bucle de host */
    double   cycle_ms, emu_ms, draw_ms, sdd1_ms;
    int      fps;
    uint64_t master;         /* g_cpu.master_cycles: la regla del invitado */
    uint32_t spcCycles;      /* apu->cycles: ciclos SPC desde el reset */
    uint64_t spcPortClock;   /* reloj del bus de puertos del SPC */
    uint16_t spcPC;
    struct { uint8_t target, divider, counter, enabled; } t[3];
    uint8_t  io_in[4];       /* $2140-$2143 tal y como los VE el SPC */
    uint8_t  io_out[4];      /* lo que el SPC ha escrito hacia la CPU */
    uint8_t  io_lastw[4];    /* ULTIMO byte entregado por el invitado */
    uint64_t io_wcount[4];   /* bytes entregados por puerto */
    uint32_t io_qdepth;      /* eventos de puerto aun en la cola */
    uint64_t io_qmax, io_writes, io_overwritten;
    uint64_t spcPortReads[4];
    uint64_t spcDspW;        /* escrituras SPC -> DSP */
    uint64_t apuSyncCalls;   /* sincronizaciones de APU del bucle principal */
    double   apuSyncMs;
} EvRec;

#define EV_CAP 64u
static EvRec     s_ring[EV_CAP];
static unsigned  s_head = 0, s_count = 0;   /* s_count <= EV_CAP */
static int       s_on = -1;
static FILE     *s_f = NULL;
static int       s_prev_slow = 0;
static int       s_tail = 0;
static int       s_pre = 5, s_tail_n = 2, s_csv = 0;
static int       s_mkdir_done = 0;
static int       s_csv_hdr = 0;      /* cabecera CSV ya escrita en este fichero */
static const char *s_dir = "evlogs";
static int       s_files = 0, s_max_files = 64;
static unsigned  s_written = 0;              /* fotogramas escritos en el evento */
static int       s_open_frame = -1;           /* fotograma que ABRIO el evento */
static char      s_open_path[1024] = {0};    /* ruta del evento en curso */

extern uint64_t g_apu_port_writes;
extern uint64_t g_apu_port_queue_max;
extern uint64_t g_inp_overwritten;
extern uint64_t g_spc_dsp_dat;
extern uint64_t g_spc_port_reads[4];
extern uint8_t  g_apu_last_port_w[4];
extern uint64_t g_apu_port_wcount[4];
extern void rtl_apu_perf_snapshot(uint64_t *ns, uint64_t *calls);

static void EvEnsureDir(void) {
    if (s_mkdir_done) return;
    s_mkdir_done = 1;
    EV_MKDIR(s_dir);
}

/* Una linea por fotograma. `prev` puede ser NULL (primera linea del fichero),
 * en cuyo caso los deltas se imprimen como -1 en vez de inventarse un origen. */
static void EvWrite(const EvRec *r, const EvRec *prev) {
    int dm = -1, ds = -1;
    uint64_t dmest = 0;
    if (prev) {
        dm = (int)(r->master - prev->master);
        ds = (int)(r->spcPortClock - prev->spcPortClock);
    }
    dmest = r->master + EV_MESEN_CYCLE_OFFSET;

    if (s_csv) {
        /* La cabecera se escribe UNA vez, al abrir el fichero. Antes estaba
         * dentro del `if (prev)`, que es justamente falso en el primer
         * registro del historico: el CSV salia sin cabecera y no se podia
         * leer por nombre de columna. */
        if (!s_csv_hdr) {
            s_csv_hdr = 1;
            fprintf(s_f,
                "frame,hostLoop,cycleMs,emuMs,drawMs,sdd1Ms,fps,master,mesenCycEst,"
                "dMaster,dSpcPortClock,spcCycles,spcPC,"
                "t0target,t0div,t0cnt,t0en,t1target,t1div,t1cnt,t1en,"
                "t2target,t2div,t2cnt,t2en,"
                "in0,in1,in2,in3,out0,out1,out2,out3,"
                "w0,w1,w2,w3,cnt0,cnt1,cnt2,cnt3,qdepth,"
                "spcReads0,spcReads1,spcReads2,spcReads3,spcDspW,apuSyncCalls\n");
        }
        if (prev) {
            fprintf(s_f,
                "%d,%u,%.3f,%.3f,%.3f,%.3f,%d,%llu,%llu,%d,%d,%u,%04X,"
                "%u,%u,%u,%d,%u,%u,%u,%d,%u,%u,%u,%d,"
                "%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%llu,%llu,%llu,%llu,%u,"
                "%llu,%llu,%llu,%llu,%llu,%llu\n",
                r->frame, r->hostLoop, r->cycle_ms, r->emu_ms, r->draw_ms,
                r->sdd1_ms, r->fps,
                (unsigned long long)r->master, (unsigned long long)dmest,
                dm, ds, r->spcCycles, (unsigned)r->spcPC,
                r->t[0].target, r->t[0].divider, r->t[0].counter, r->t[0].enabled,
                r->t[1].target, r->t[1].divider, r->t[1].counter, r->t[1].enabled,
                r->t[2].target, r->t[2].divider, r->t[2].counter, r->t[2].enabled,
                r->io_in[0], r->io_in[1], r->io_in[2], r->io_in[3],
                r->io_out[0], r->io_out[1], r->io_out[2], r->io_out[3],
                r->io_lastw[0], r->io_lastw[1], r->io_lastw[2], r->io_lastw[3],
                (unsigned long long)r->io_wcount[0],
                (unsigned long long)r->io_wcount[1],
                (unsigned long long)r->io_wcount[2],
                (unsigned long long)r->io_wcount[3],
                r->io_qdepth,
                (unsigned long long)r->spcPortReads[0],
                (unsigned long long)r->spcPortReads[1],
                (unsigned long long)r->spcPortReads[2],
                (unsigned long long)r->spcPortReads[3],
                (unsigned long long)r->spcDspW,
                (unsigned long long)r->apuSyncCalls);
        }
        return;
    }

    /* Columnas alineadas: se lee de un vistazo y se puede cortar con cut/grep. */
    fprintf(s_f,
        "f=%-6d loop=%-4u C=%7.2fms emu=%7.2f draw=%6.2f sdd1=%5.2f %3dFPS | "
        "master=%-10llu mesenCycEst=%-10llu dMaster=%-8d dSpc=%-7d spcCyc=%-8u "
        "PC=%04X | "
        "T0=%02X/%02X/%02X/%d T1=%02X/%02X/%02X/%d T2=%02X/%02X/%02X/%d | "
        "in=%02X%02X%02X%02X out=%02X%02X%02X%02X "
        "w=%02X%02X%02X%02X cnt=%llu/%llu/%llu/%llu q=%u | "
        "spcRd=%llu/%llu/%llu/%llu dspW=%llu apuSync=%llu\n",
        r->frame, r->hostLoop, r->cycle_ms, r->emu_ms, r->draw_ms, r->sdd1_ms,
        r->fps,
        (unsigned long long)r->master, (unsigned long long)dmest, dm, ds,
        r->spcCycles, (unsigned)r->spcPC,
        r->t[0].target, r->t[0].divider, r->t[0].counter, r->t[0].enabled,
        r->t[1].target, r->t[1].divider, r->t[1].counter, r->t[1].enabled,
        r->t[2].target, r->t[2].divider, r->t[2].counter, r->t[2].enabled,
        r->io_in[0], r->io_in[1], r->io_in[2], r->io_in[3],
        r->io_out[0], r->io_out[1], r->io_out[2], r->io_out[3],
        r->io_lastw[0], r->io_lastw[1], r->io_lastw[2], r->io_lastw[3],
        (unsigned long long)r->io_wcount[0], (unsigned long long)r->io_wcount[1],
        (unsigned long long)r->io_wcount[2], (unsigned long long)r->io_wcount[3],
        r->io_qdepth,
        (unsigned long long)r->spcPortReads[0], (unsigned long long)r->spcPortReads[1],
        (unsigned long long)r->spcPortReads[2], (unsigned long long)r->spcPortReads[3],
        (unsigned long long)r->spcDspW, (unsigned long long)r->apuSyncCalls);
}

static void EvHeader(const EvRec *first) {
    fprintf(s_f,
"# Registro por BAJON de FPS (evlog). Un fichero por evento.\n"
"# Se abre en el flanco de subida del mismo `ciclo > SNESRECOMP_HOT_MS` que\n"
"# pinta el HUD de rojo, y se cierra %d fotograma(s) despues de recuperarse.\n"
"# Empieza con el fotograma %d, que es el que disparo el color.\n"
"#\n"
"# RELOJES Y COMO ENFRENTARLO CON MESEN\n"
"#   master      : g_cpu.master_cycles, la regla del invitado. Un frame de\n"
"#                host son 357368 de estos (medido, identico frame a frame).\n"
"#   mesenCycEst : master + %llu, la conversion al `Cycle:` de la traza de\n"
"#                Mesen por instruccion. OJO: es una ESTIMACION calibrada en\n"
"#                una ventana concreta (§22.25), no un reloj universal.\n"
"#   dMaster     : master de este fotograma menos el del anterior. Es la\n"
"#                columna que mas util se enfrenta al avance por frame del\n"
"#                TSV de Mesen: un frame de hardware son 357368.\n"
"#   dSpc        : ciclos del bus de puertos del SPC700 en este fotograma.\n"
"#                El hardware son 17088/fotograma (1,024 MHz / 60 Hz).\n"
"#   frame vs loop: `frame` es el fotograma del INVITADO y `loop` la vuelta\n"
"#                del bucle de host. No son el mismo numero y su relacion\n"
"#                cambia con el turbo; el indice de fotograma NO es una\n"
"#                coordenada compartida con el hardware (ver §22.25).\n"
"#\n"
"# sdd1     : OJO, esta columna NO es tiempo de pared y no se puede comparar\n"
"#            con C. Viene de sdd1_prof_ms, que convierte un contador TSC\n"
"#            (__rdtsc) a milisegundos con el factor de\n"
"#            QueryPerformanceFrequency. En una maquina virtual esos dos\n"
"#            relojes no estan sincronizados y el factor no vale: medido en\n"
"#            este equipo, un fotograma de 84 ms de pared sale con\n"
"#            sdd1=275 ms. Sirve como indicador RELATIVO de cuando hay\n"
"#            descompresion, no como coste. Para el coste real hay que usar C\n"
"#            y emu, que si vienen de SDL_GetPerformanceCounter.\n"
"#\n"
"# sdd1     : OJO, esta columna NO es tiempo de pared y no se puede comparar\n"
"#            con C. Viene de sdd1_prof_ms, que convierte un contador TSC\n"
"#            (__rdtsc) a milisegundos con el factor de\n"
"#            QueryPerformanceFrequency. En una maquina virtual esos dos\n"
"#            relojes no estan sincronizados y el factor no vale: medido en\n"
"#            este equipo, un fotograma de 84 ms de pared sale con\n"
"#            sdd1=275 ms. Sirve como indicador RELATIVO de cuando hay\n"
"#            descompresion, no como coste. Para el coste real estan C y emu,\n"
"#            que si salen de SDL_GetPerformanceCounter.\n"
"#\n"
"# T0/T1/T2 : target/divider/counter/enabled del temporizador i del SPC700.\n"
"# in        : $2140-$2143 tal y como los VE el SPC (apu->inPorts).\n"
"# out       : lo que el SPC ha escrito hacia la CPU (apu->outPorts).\n"
"# w         : ULTIMO byte que el invitado entrego en cada $2140-$2143.\n"
"# cnt       : bytes acumulados entregados por puerto (no por fotograma).\n"
"# q         : profundidad de la cola de eventos de puerto pendientes.\n"
"# spcRd     : lecturas que ha hecho el SPC de $2140-$2143 (acumulado).\n"
"# dspW      : escrituras SPC->DSP (acumulado). Si se congela, el motor de\n"
"#             sonido ha dejado de hablar con el DSP (§22.28/§22.29).\n"
"# apuSync   : sincronizaciones de APU que ha pedido el bucle principal.\n"
"#\n"
"# Formato: %s\n\n",
        s_tail_n, first->frame,
        (unsigned long long)EV_MESEN_CYCLE_OFFSET,
        s_csv ? "CSV (primera linea = cabecera, una fila por fotograma)"
              : "columnas alineadas key=value, una linea por fotograma");
}

static void EvClose(void) {
    if (!s_f) return;
    /* Se informa del fotograma que ABRIO el evento, no del ultimo escrito: en
     * un tramo largo de fotogramas lentos esos son muy distintos y el nombre
     * del fichero es el del que abrio. */
    fprintf(stderr, "[evlog] cerrado %s (%u fotogramas, abierto en f%d)\n",
            s_open_path, s_written, s_open_frame);
    fclose(s_f);
    s_f = NULL;
    s_tail = 0;
    s_written = 0;
    s_open_frame = -1;
    s_open_path[0] = 0;
}

/* La inicializacion lee el entorno una sola vez. Se separa de EvLogFrame para
 * que EvLogEnabled() no tenga que duplicarla ni meterse por el camino rapido. */
static void EvLogInitOnce(void) {
    if (s_on >= 0) return;
    const char *e = getenv("SNESRECOMP_EVLOG");
    s_on = (e && e[0] && e[0] != '0') ? 1 : 0;
    const char *v;
    if ((v = getenv("SNESRECOMP_EVLOG_PRE"))  && v[0]) s_pre    = atoi(v);
    if ((v = getenv("SNESRECOMP_EVLOG_TAIL")) && v[0]) s_tail_n = atoi(v);
    if ((v = getenv("SNESRECOMP_EVLOG_MAX"))  && v[0]) s_max_files = atoi(v);
    if ((v = getenv("SNESRECOMP_EVLOG_DIR"))  && v[0]) s_dir    = v;
    if ((v = getenv("SNESRECOMP_EVLOG_CSV"))  && v[0]) s_csv    = (v[0] != '0');
    if (s_pre < 0) s_pre = 0;
    if (s_tail_n < 0) s_tail_n = 0;
}

int EvLogEnabled(void) {
    EvLogInitOnce();
    return s_on;
}

void EvLogFrame(double cycle_ms, double emu_ms, double draw_ms,
                double sdd1_ms, int fps, int frame_invitado, int slow) {
    static unsigned s_loop = 0;

    EvLogInitOnce();
    if (!s_on) return;

    EvRec r;
    memset(&r, 0, sizeof r);
    r.frame      = frame_invitado;
    r.hostLoop   = ++s_loop;
    r.cycle_ms   = cycle_ms;
    r.emu_ms     = emu_ms;
    r.draw_ms    = draw_ms;
    r.sdd1_ms    = sdd1_ms;
    r.fps        = fps;
    r.master     = g_cpu.master_cycles;

    r.io_writes      = g_apu_port_writes;
    r.io_qmax        = g_apu_port_queue_max;
    r.io_overwritten = g_inp_overwritten;
    r.spcDspW        = g_spc_dsp_dat;
    for (int i = 0; i < 4; i++) {
        r.spcPortReads[i] = g_spc_port_reads[i];
        r.io_lastw[i]     = g_apu_last_port_w[i];
        r.io_wcount[i]    = g_apu_port_wcount[i];
    }
    { uint64_t ns = 0, calls = 0;
      rtl_apu_perf_snapshot(&ns, &calls);
      r.apuSyncCalls = calls;
      r.apuSyncMs    = (double)ns / 1e6;
    }
    if (g_snes && g_snes->apu) {
        Apu *a = g_snes->apu;
        r.spcCycles    = a->cycles;
        r.spcPortClock = a->portClock;
        r.io_qdepth    = apu_portQueueDepth(a);
        for (int i = 0; i < 4; i++) {
            r.io_in[i]  = a->inPorts[i];
            r.io_out[i] = a->outPorts[i];
        }
        for (int i = 0; i < 3; i++) {
            r.t[i].target  = a->timer[i].target;
            r.t[i].divider = a->timer[i].divider;
            r.t[i].counter = a->timer[i].counter;
            r.t[i].enabled = a->timer[i].enabled ? 1 : 0;
        }
        if (a->spc) r.spcPC = a->spc->pc;
    }

    /* Anillo: siempre, para que el historico ya exista cuando salte el trigger.
     * El indice del registro ANTERIOR se calcula ANTES de sobrescribir la
     * ranura: si se calculara despues, s_head ya habria avanzado y compararia
     * el registro consigo mismo, dando dMaster=0 en todas las lineas. */
    const unsigned prev_idx = (s_head + EV_CAP - 1) % EV_CAP;
    s_ring[s_head] = r;
    s_head = (s_head + 1) % EV_CAP;
    if (s_count < EV_CAP) s_count++;

    if (slow && !s_prev_slow) {
        /* Flanco de subida: nuevo evento. */
        if (s_f) EvClose();                       /* un evento sin cerrar */
        if (s_files < s_max_files) {
            char path[1024];
            EvEnsureDir();
            snprintf(path, sizeof path, "%s/f%06d.log", s_dir, r.frame);
            s_f = fopen(path, "w");
            if (s_f) {
                s_files++;
                s_csv_hdr = 0;            /* cada fichero lleva su cabecera */
                s_open_frame = r.frame;
                snprintf(s_open_path, sizeof s_open_path, "%s", path);
                EvHeader(&r);
                /* Historico real: los ultimos s_pre fotogramas ANTES de este,
                 * mas el propio fotograma que dispara. */
                unsigned want = (unsigned)s_pre + 1;
                if (want > s_count) want = s_count;
                unsigned start = (s_head + EV_CAP - want) % EV_CAP;
                const EvRec *prev = NULL;
                for (unsigned i = 0; i < want; i++) {
                    const EvRec *h = &s_ring[(start + i) % EV_CAP];
                    EvWrite(h, prev);
                    prev = h;
                    s_written++;
                }
                fprintf(stderr,
                        "[evlog] ABIERTO %s (fotograma %d, C=%.2f ms)\n",
                        path, r.frame, r.cycle_ms);
            }
        }
        s_tail = 0;
    } else if (s_f) {
        EvWrite(&r, (s_count > 1) ? &s_ring[prev_idx] : NULL);
        s_written++;
        if (slow) {
            s_tail = 0;
        } else if (++s_tail >= s_tail_n) {
            EvClose();
        }
    }
    s_prev_slow = slow;
}

#endif /* SNESRECOMP_CLEAN_BUILD */
