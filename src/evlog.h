/* evlog.h — registro de fotogramas DISPARADO POR BAJON DE FPS.
 *
 * Que es: cuando el HUD se pone rojo (el mismo `ciclo > s_hot_ms` que ya
 * decide el color y la captura [hot]), este modulo abre un fichero de texto
 * con el estado de los fotogramas de alrededor del bajon y lo cierra cuando la
 * escena se recupera. Fuera de un bajon no escribe NADA: el objetivo es no
 * tener un log gigante siempre activo.
 *
 * Que guarda por fotograma:
 *   - tiempos de host: ciclo, emulacion, dibujado, descompresion S-DD1, FPS
 *   - ciclos: maestro (invitado), reloj del SPC (portClock) y su total
 *   - los 3 temporizadores del SPC700: target, divider, counter, enabled
 *   - los buffers de E/S $2140-$2143: lo que VE el SPC (inPorts), lo que
 *     escribio el SPC (outPorts), el ULTIMO byte que entrego el invitado y
 *     cuantos bytes van por puerto, mas la profundidad de la cola
 *   - llamadas al bucle principal: sincronizaciones de APU y escrituras
 *     SPC->DSP
 *
 * Entorno:
 *   SNESRECOMP_EVLOG=1        activa (por defecto apagado)
 *   SNESRECOMP_EVLOG_DIR=<d>  destino (por defecto "evlogs")
 *   SNESRECOMP_EVLOG_PRE=<n>  fotogramas de historico ANTES del bajon
 *                             (por defecto 5, que es lo pedido)
 *   SNESRECOMP_EVLOG_TAIL=<n> fotogramas que se siguen escribiendo tras
 *                             recuperarse (por defecto 2)
 *   SNESRECOMP_EVLOG_CSV=1    formato CSV en vez de columnas
 *   SNESRECOMP_EVLOG_MAX=<n>  maximo de ficheros por sesion (por defecto 64;
 *                             al llegar al tope deja de abrir, no borra)
 */
#ifndef SNESRECOMP_EVLOG_H
#define SNESRECOMP_EVLOG_H

#ifdef __cplusplus
extern "C" {
#endif

/* `slow` es el MISMO booleano que enciende el rojo del HUD. Se pasa desde
 * ahi en vez de recalcularlo para que el log y el color no puedan discrepar:
 * si el HUD salio rojo, hay log. */
void EvLogFrame(double cycle_ms, double emu_ms, double draw_ms,
                double sdd1_ms, int fps, int frame_invitado, int slow);

/* 1 si SNESRECOMP_EVLOG esta puesto. Lo consulta el llamante para NO pedirle
 * datos caros (el perfil de S-DD1) cuando nadie los va a usar: sin esto, con
 * el log apagado se estaria llamando a sdd1_prof_get() en cada fotograma para
 * nada, cosa que antes solo pasaba con [perf] activo. */
int EvLogEnabled(void);

#ifdef __cplusplus
}
#endif

#endif /* SNESRECOMP_EVLOG_H */
