/* Game-specific RAM variable declarations for Star Ocean.
 *
 * Star Ocean (Japan) uses the S-DD1 compression chip on a LoROM mapper.
 * Most game state lives in WRAM ($7E:$0000-$1FFFF) and is accessed by
 * the interpreter bridge at runtime.  This header declares only the
 * framework-protocol symbols that the runner expects or that generated
 * recompiled code references.
 */

#ifndef VARIABLES_H
#define VARIABLES_H

#include "types.h"

/* g_ram is declared by snesrecomp/runner/src/common_rtl.h. */

/* Framework-protocol frame counter, incremented each run_frame().
 * Declared extern here; defined in so_cpu_infra.c.  Some generated
 * code and the Falcon presentation mod reference this symbol. */
extern uint16 counter_global_frames;

#endif /* VARIABLES_H */