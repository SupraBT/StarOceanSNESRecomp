-- mesen_intro_probe.lua - Star Ocean (Japan) - sonda de fundidos de la intro
-- ============================================================================
-- MesenCE -> Depurar -> Ventana de script -> Abrir script -> este fichero -> Ejecutar.
-- Despues cargar/reiniciar "Star Ocean (Japan).sfc" DESDE EL ARRANQUE.
--
-- REGLAS DE LA CORRIDA (importantes):
--   * UNA sola sonda a la vez.  Si hay otro script cargado, sus callbacks siguen
--     vivos y contaminan los contadores.
--   * NO TOCAR EL PAD en toda la corrida.  Es la corrida "sin input": el pad
--     aborta las esperas temporizadas (C8:F41D devuelve SEC) y cambia el guion.
--   * Arrancar desde reset (no cargar un save state).
--   * Frames: START_FRAME=1 .. END_FRAME=900 (el tramo gf66-415, que es el hueco
--     que dejo el oraculo viejo -empieza en fr411-, y el primer fundido).
--
-- POR QUE ESTA VERSION (29/09 noche, correccion):
--   La traza anterior (mesen_intro_probe.tsv, fr1..2000) capturo los callbacks de
--   LECTURA bien (1973/2000 frames) y los de ESCRITURA casi nunca (2 frames en
--   2000: fr86 y fr841), pese a que el oraculo viejo ve 16.090 escrituras a
--   $2100 en hardware.  La sonda informo "writes=8/8 registradas" con la forma 1
--   de addMemoryCallback en AMBOS casos, asi que el problema no es de forma
--   evidente: hay que MEDIRLO dentro de la propia sonda en vez de suponerlo.
--   Esta version hace tres cosas:
--     1) Registra la MISMA captura de $2100 por tres vias (forma de 4 argumentos,
--        forma de 6 argumentos explicitos, y memType en 3a posicion) con
--        contadores separados: una corrida dice cual funciona de verdad.
--     2) Anade un CANARIO: callback de escritura sobre la pagina de pila
--        ($00:0100-$01FF), que recibe escrituras miles de veces por frame.  Si el
--        canario da 0, los callbacks de escritura NO disparan y ningun $2100 por
--        esa via es creible.
--     3) Captura $2100 por EXEC CALLBACKS en los 95 sitios de ROM que almacenan
--        en $2100 (STA/STX $2100 y STA long), leyendo el valor a almacenar del
--        acumulador.  Los exec callbacks SI estan demostrados en esta config
--        (columna 12 del TSV: C8F407=1 en 69 frames).  Esta via no depende de la
--        semantica de los callbacks de memoria.
--
-- Salida: TSV, una linea por frame, en OUT_NAME.  ORDEN REAL DE COLUMNAS:
--   1 fr  2 master  3 pc  4 D  5 DB  6 E4  7 E5  8 DA  9 AFB  10 AFD
--   11 ini      = valores escritos a $2100 en ese frame, "80" / "80+0F+80".
--                 Fuente (v4): exec (preferida) > m6 (forma 3, byte exacto) >
--                 m1 (forma 1).  La via mMT de la v3 SE ELIMINO: no era una
--                 variante valida de la API y disparaba sobre $0000..$2100.
--   12 x        = exec por rutina vigilada, contadas en el frame
--   13 rdcnt    = r4800=<n>/<v>,r2140=<n>/<v>,r4212=<n>/<v>  (LECTURAS)
--   14 wshadow  = "DA=.. E4=.. AF9=.. AFB=.. AFD=.."  (escrituras a sombras WRAM;
--                 vacio si no hubo, pero el campo SIEMPRE existe)
--   15 src      = diagnostico: x=<n> pc=<sitio> db=<vals> m1=<n> m6=<n>
--                 mA1=<n> mA4=<n> can1=<n> can6=<n>
--   TODAS las filas tienen 15 campos: 13/14/15 se emiten siempre (aunque esten
--   vacios) para que las posiciones sean fijas.  La version anterior omitia las
--   columnas vacias y desplazaba las de la derecha, que es justo el tipo de
--   ambiguedad que ya hizo leer mal esta traza.
--   OJO (heredado): las trazas viejas llevan la cabecera con 11=writes 12=reads;
--   la realidad es 11=ini 12=exec 13=lecturas 14=sombras.
-- ============================================================================

-- Empezar en el frame 1: el oraculo viejo solo tiene datos desde el frame 411
-- (su script calibraba ~400 frames antes de registrar las sondas), asi que el
-- boot y el primer fundido estaban sin cubrir.
-- v4 (29/09 tarde): cambia el NOMBRE de salida a proposito, para que nadie
-- mezcle esta corrida con la v3 (cuyo `ini` era un volcado de la via mMT).
local OUT_NAME    = "mesen_fades900b.tsv"
local STATUS_NAME = "mesen_fades900b_status.log"
local CANDIDATOS = {
  "E:\\Experimento Hermes\\Documentacion\\TracesMesen\\" .. OUT_NAME,
  "F:\\Recompilador Super Nintendo\\Mesen\\" .. OUT_NAME,
  "F:\\SOR\\" .. OUT_NAME,
}
local STATUS_CANDIDATOS_FIJOS = {
  "E:\\Experimento Hermes\\Documentacion\\TracesMesen\\" .. STATUS_NAME,
  "F:\\Recompilador Super Nintendo\\Mesen\\" .. STATUS_NAME,
  "F:\\SOR\\" .. STATUS_NAME,
}
local OUT_PATH = nil       -- nil = probar candidatos en orden; ruta = forzar
local START_FRAME = 1      -- 1 = desde el arranque/reset
local END_FRAME   = 900    -- se detiene aqui; cubre gf66-415 y el 1er fundido
local LOG_EVERY   = 60     -- resumen en la ventana de registro

-- Enums: se toman de las tablas de runtime y, si no existen, del valor
-- documentado en la propia API incrustada en Mesen.exe:
--   callbackType: read=0, write=1, exec=2
--   eventType:    nmi=0, irq=1, startFrame=2, endFrame=3, reset=4, scriptEnded=5
--   memType:      snesMemory=0     cpuType: snes=0
--   addMemoryCallback(callback, callbackType, startAddress, endAddress = start,
--                     cpuType = main CPU, memoryType = main CPU memory)
--   El callback de memoria recibe (address, value).
local function enum_or(tbl, key, fallback)
  if tbl ~= nil and tbl[key] ~= nil then return tbl[key] end
  return fallback
end
local CB_READ  = enum_or(emu and emu.callbackType, "read",  0)
local CB_WRITE = enum_or(emu and emu.callbackType, "write", 1)
local CB_EXEC  = enum_or(emu and emu.callbackType, "exec",  2)
local CPU_SNES = enum_or(emu and emu.cpuType, "snes", 0)
local MT_SNES  = enum_or(emu and emu.memType, "snesMemory", 0)
local EV_STARTFRAME  = enum_or(emu and emu.eventType, "startFrame",  2)
local EV_ENDFRAME    = enum_or(emu and emu.eventType, "endFrame",    3)
local EV_SCRIPTENDED = enum_or(emu and emu.eventType, "scriptEnded", 5)

-- PC vigilados (24 bits).  n = nombre corto para el log.
local EXEC = {
  { 0xC8F407, "C8F407" },  -- espera vblank pura (LDA $4212/BMI/LDA $4212/BPL)
  { 0xC8F41D, "C8F41D" },  -- espera vblank que ademas lee el pad ($4218)
  { 0xC8F497, "C8F497" },  -- bucle fade-in ($F407)
  { 0xC8F4AB, "C8F4AB" },  -- blank N frames
  { 0xC8F4B7, "C8F4B7" },  -- entrada fade-out
  { 0xC8F4C5, "C8F4C5" },  -- STA $2100 del fade-out
  { 0xC8F4D0, "C8F4D0" },  -- entrada fade-in con pad
  { 0xC8F4D4, "C8F4D4" },  -- cuerpo del bucle
  { 0xC8F4DE, "C8F4DE" },  -- STA $2100 del fade-in
  { 0xCC088B, "CC088B" },  -- motor: LDA $DA / STA $2100 (aplicador por frame)
  { 0xCC08B4, "CC08B4" },  -- motor: INC $E4 (contador de frames)
  { 0xCC0924, "CC0924" },  -- motor: despachador de $0AFB
  { 0xCC0B44, "CC0B44" },  -- modo 6: INC $DA (1 frame/nivel)
  { 0xCC0B57, "CC0B57" },  -- modo 7: DEC $DA (1 frame/nivel)
  { 0xCC1033, "CC1033" },  -- modo 8: mascara $E4&3 (4 frames/nivel) + CGRAM
  { 0xCC104B, "CC104B" },  -- modo 8: cuerpo del bucle CGRAM
  { 0xC0212B, "C0212B" },  -- fades de banco $C0 (sombra $DA)
  { 0xC02141, "C02141" },
  { 0xC02AE0, "C02AE0" },
  -- Rutina de la bomba por frame y handler de V-IRQ (localizadas el 29/09):
  { 0xC00230, "C00230" },  -- entrada del handler de V-IRQ
  { 0xC00251, "C00251" },  -- handler: JSR $032D (bomba por frame)
  { 0xC0032D, "C0032D" },  -- bomba: entrada
  { 0xC00387, "C00387" },  -- bomba: LDA $4806 / LDA $4807 (MMC de la S-DD1)
}
local EXEC_NAMES = {}
for _, e in ipairs(EXEC) do EXEC_NAMES[e[1]] = e[2] end

-- ---------------------------------------------------------------------------
-- Sitios de ROM que almacenan en $2100 (generados por escaneo del ROM).
-- { pc24, bytes }  - 8D0021 = STA $2100, 8E0021 = STX $2100,
--                    8F0021xx = STA long a $xx2100 (solo si xx apunta a I/O).
-- ---------------------------------------------------------------------------
local STORE2100 = {
   { 0xC0018F, "8D0021" }, { 0xC002BE, "8D0021" }, { 0xC002E4, "8D0021" },
   { 0xC0213A, "8D0021" }, { 0xC021C0, "8D0021" }, { 0xC065E2, "8D0021" },
   { 0xC0671B, "8D0021" }, { 0xC07026, "8D0021" }, { 0xC071A5, "8D0021" },
   { 0xC071BB, "8D0021" }, { 0xC0770E, "8D0021" }, { 0xC07717, "8D0021" },
   { 0xC07EB3, "8F002100" }, { 0xC07ED6, "8D0021" }, { 0xC08088, "8D0021" },
   { 0xC080D5, "8D0021" }, { 0xC081B4, "8D0021" }, { 0xC081B9, "8D0021" },
   { 0xC08374, "8D0021" }, { 0xC083E8, "8D0021" }, { 0xC08484, "8D0021" },
   { 0xC0C2AF, "8D0021" }, { 0xC0C33C, "8D0021" }, { 0xC0C495, "8D0021" },
   { 0xC0C4F6, "8D0021" }, { 0xC0C500, "8D0021" }, { 0xC101D7, "8D0021" },
   { 0xC10206, "8D0021" }, { 0xC20B8E, "8D0021" }, { 0xC21056, "8D0021" },
   { 0xC26CFB, "8F002100" }, { 0xC26D5D, "8D0021" }, { 0xC27E03, "8D0021" },
   { 0xC27E34, "8D0021" }, { 0xC27E4D, "8D0021" }, { 0xC27EAC, "8D0021" },
   { 0xC27EE2, "8F002100" }, { 0xC27F1F, "8F002100" }, { 0xC27FEC, "8F002100" },
   { 0xC28014, "8F002100" }, { 0xC2A409, "8D0021" }, { 0xC2A421, "8D0021" },
   { 0xC2DB45, "8D0021" }, { 0xC2E03E, "8D0021" }, { 0xC5014B, "8D0021" },
   { 0xC502E9, "8D0021" }, { 0xC60964, "8F002100" }, { 0xC60987, "8D0021" },
   { 0xC809CB, "8F002100" }, { 0xC8F4A3, "8D0021" }, { 0xC8F4C5, "8D0021" },
   { 0xC8F4CC, "8D0021" }, { 0xC8F4DE, "8D0021" }, { 0xC8F50A, "8D0021" },
   { 0xC8F511, "8D0021" }, { 0xC8F518, "8D0021" }, { 0xCA5B5C, "8F002100" },
   { 0xCA5B63, "8F002100" }, { 0xCA5B6A, "8F002100" }, { 0xCA6939, "8D0021" },
   { 0xCA6C70, "8D0021" }, { 0xCA6D31, "8D0021" }, { 0xCB00E2, "8D0021" },
   { 0xCB013B, "8F002100" }, { 0xCB0176, "8F002100" }, { 0xCB01AC, "8D0021" },
   { 0xCB0445, "8F002100" }, { 0xCC0593, "8D0021" }, { 0xCC05A4, "8D0021" },
   { 0xCC05C3, "8D0021" }, { 0xCC088D, "8D0021" }, { 0xCC0C76, "8D0021" },
   { 0xCC0D3C, "8D0021" }, { 0xCC0E35, "8D0021" }, { 0xCC0FAC, "8D0021" },
   { 0xCC0FCE, "8D0021" }, { 0xCC0FD5, "8D0021" }, { 0xCC0FE7, "8D0021" },
   { 0xCC1013, "8D0021" }, { 0xCC101A, "8D0021" }, { 0xCC1021, "8D0021" },
   { 0xCC14BB, "8D0021" }, { 0xCC151D, "8D0021" }, { 0xCC1970, "8D0021" },
   { 0xCC19F5, "8D0021" }, { 0xCC1C2A, "8D0021" }, { 0xCC1CC7, "8D0021" },
   { 0xCC2040, "8D0021" }, { 0xCC20C5, "8D0021" }, { 0xCC280E, "8D0021" },
   { 0xCC2883, "8D0021" }, { 0xCC28BD, "8D0021" }, { 0xD2EA53, "8E0021" },
   { 0xE31079, "8D0021" }, { 0xF4301A, "8E0021" },
}

-- Rangos vigilados en escritura (direcciones de bus de 24 bits).
-- $2100 NO va aqui: se registra aparte por tres vias (ver main()).
local WRANGE = {
  { 0x0000DA, 0x0000DA, "DA"   },
  { 0x0000E4, 0x0000E5, "E4"   },
  { 0x000AFB, 0x000AFC, "AFB"  },
  { 0x000AFD, 0x000AFE, "AFD"  },
  { 0x000AF9, 0x000AFA, "AF9"  },
  { 0x004800, 0x004807, "S4800" },  -- SDD1 (MMC): la descompresion de graficos
  { 0x002140, 0x002143, "APU"   },  -- canal con el motor de sonido
}

-- Canario: la pagina de pila recibe escrituras constantemente.  Si esto no
-- dispara, los callbacks de ESCRITURA no funcionan en esta build y ninguna
-- captura de $2100 por esa via es creible.
local CANARY = { 0x000100, 0x0001FF, "stack" }

-- Sondas de LECTURA (contadores por frame; los sondeos de "estoy listo" son
-- lecturas, no escrituras: sin esto no se ve esperar al invitado).
local RRANGE = {
  { 0x004800, 0x004807, "r4800" },  -- SDD1 status/data
  { 0x002140, 0x002143, "r2140" },  -- handshake con el SPC
  { 0x002138, 0x00213F, "r2138" },  -- RDNMI/HVBJOY/...
  { 0x004212, 0x004213, "r4212" },  -- $4212: la espera de vblank
}

-- -- estado ----------------------------------------------------------------
local frame = 0
local xcount = {}          -- nombre de rutina -> n ejecuciones este frame
local xseen  = {}          -- nombre -> true si al menos una vez en toda la corrida
local store_hits = {}      -- pc24 -> n ejecuciones acumuladas (toda la corrida)
local store_frame_first = nil  -- primer sitio de $2100 ejecutado este frame
local store_frame_db = {}  -- DB observado en cada almacenamiento de este frame
local mem_hits = {}        -- fuente ("m1"/"m6") -> n acumulado (toda la corrida)
local mem_all  = {}        -- "mA1"/"mA4" -> n acumulado de escrituras en $0000..$2100
local can_hits = {}        -- "can1"/"can6" -> n acumulado
local wrl    = {}          -- nombre de rango -> lista de valores este frame (sombras)
local ini_src = {}         -- "x"/"m6"/"m1" -> lista de valores $2100 este frame
local rrc    = {}          -- nombre de rango -> lecturas este frame
local rlast  = {}          -- nombre de rango -> ultimo valor leido
local out    = nil
local out_path_used = nil

local function log(msg) emu.log(tostring(msg)) end

-- -- Diagnostico de arranque en fichero -----------------------------------
-- Si la ventana de script no muestra nada, este registro deja constancia en
-- disco de que el script SI se ejecuto (y de por que fallo el TSV si fallo).
local status_path = nil
local function status(msg)
  if not status_path then
    local lista = {}
    -- OJO: no usar try() aqui (se declara mas abajo; una funcion no ve un local
    -- declarado despues de ella, lo resolveria como global nil).
    local okri, ri = pcall(emu.getRomInfo)
    if not okri then ri = nil end
    if type(ri) == "table" then
      local dir = ri.filePath or ri.path
      if dir then
        dir = dir:match("^(.*)[/\\][^/\\]*$")
        if dir then lista[#lista + 1] = dir .. "/" .. STATUS_NAME end
      end
    end
    for _, p in ipairs(STATUS_CANDIDATOS_FIJOS) do lista[#lista + 1] = p end
    lista[#lista + 1] = STATUS_NAME
    for _, p in ipairs(lista) do
      local f = io.open(p, "a")
      if f then f:close(); status_path = p; break end
    end
    if status_path then
      local f = io.open(status_path, "a")
      if f then
        f:write("=== sesion " .. os.date("%Y-%m-%d %H:%M:%S") .. " ===\n")
        f:write("api: emu.log=" .. tostring(emu and emu.log ~= nil) ..
                " addMemoryCallback=" .. tostring(emu and emu.addMemoryCallback ~= nil) ..
                " addEventCallback=" .. tostring(emu and emu.addEventCallback ~= nil) .. "\n")
        f:write(string.format("enums: cb(read=%s write=%s exec=%s) ev(start=%s end=%s) memType=%s cpu=%s\n",
                tostring(CB_READ), tostring(CB_WRITE), tostring(CB_EXEC),
                tostring(EV_STARTFRAME), tostring(EV_ENDFRAME),
                tostring(MT_SNES), tostring(CPU_SNES)))
        f:close()
      end
    end
  end
  if not status_path then return end
  local f = io.open(status_path, "a")
  if f then f:write(msg .. "\n"); f:close() end
  if emu and emu.log then pcall(emu.log, tostring(msg)) end
end

local function try(fn, ...)
  local ok, res = pcall(fn, ...)
  if ok then return res end
  return nil
end

status("script EJECUTANDOSE (probe v4: byte exacto de $2100 + exec en los 95 sitios + canario)")

-- -- registro de callbacks de memoria -------------------------------------
-- form 1: (cb, ctype, start, end)                      -> cpu/memType por defecto
-- form 2: (cb, ctype, start, end, cpu)
-- form 3: (cb, ctype, start, end, cpu, mem)            -> explicito (canonico)
-- form 4: (cb, ctype, mem, start, end)                 -> variante historica
local FORM_FNS = {
  function(cb, ctype, start, end_) return emu.addMemoryCallback(cb, ctype, start, end_) end,
  function(cb, ctype, start, end_) return emu.addMemoryCallback(cb, ctype, start, end_, CPU_SNES) end,
  function(cb, ctype, start, end_) return emu.addMemoryCallback(cb, ctype, start, end_, CPU_SNES, MT_SNES) end,
  function(cb, ctype, start, end_) return emu.addMemoryCallback(cb, ctype, MT_SNES, start, end_) end,
}

-- Intenta UNA forma concreta.  Devuelve true si el registro no lanzo error.
local function add_mem_cb_form(fidx, cb, ctype, start, end_)
  local ok = pcall(FORM_FNS[fidx], cb, ctype, start, end_)
  return ok
end

-- Registro con cadena de formas (comportamiento historico: la 1 tiene prioridad).
local registered_forms = {}
local function add_mem_cb(cb, ctype, start, end_)
  for i = 1, #FORM_FNS do
    if add_mem_cb_form(i, cb, ctype, start, end_) then
      registered_forms[#registered_forms + 1] = string.format("%d(%.4X-%.4X)", i, start, end_)
      return i
    end
  end
  return nil
end

local function reset_frame_counters()
  xcount = {}
  wrl = {}
  rrc = {}
  ini_src = {}
  store_frame_first = nil
  store_frame_db = {}
end

-- OJO (defecto de la v3, corregido): NO se resetea en EV_STARTFRAME.
-- En Mesen, para la SNES, `endFrame` se dispara al ENTRAR en vblank y
-- `startFrame` al SALIR.  El juego escribe $2100 precisamente durante vblank,
-- asi que resetear en startFrame borraba del registro justo las escrituras que
-- se quieren medir: en la v3 los contadores `x`/`m6` del frame solo contenian
-- el trozo visible y `ini` acababa mostrando la via `mMT`.  El unico reset
-- valido es el que se hace DESPUES de escribir la fila, dentro de on_end_frame.

local function fmt_rd()
  local b = {}
  for _, r in ipairs(RRANGE) do
    local n = rrc[r[3]]
    if n and n > 0 then
      b[#b + 1] = string.format("%s=%d/%02X", r[3], n, (rlast[r[3]] or 0) % 256)
    end
  end
  return table.concat(b, ",")
end

local function bump(addr)
  local n = EXEC_NAMES[addr]
  if n then
    xcount[n] = (xcount[n] or 0) + 1
    xseen[n] = true
  end
end

local function note_write(name, val)
  local t = wrl[name]
  if not t then t = {}; wrl[name] = t end
  if #t < 64 then t[#t + 1] = (val or 0) % 256 end
end

local function note_ini(src, val)
  local t = ini_src[src]
  if not t then t = {}; ini_src[src] = t end
  if #t < 64 then t[#t + 1] = (val or 0) % 256 end
end

local function fmt_list(t)
  if not t or #t == 0 then return "" end
  local b = {}
  for i, v in ipairs(t) do b[i] = string.format("%02X", v % 256) end
  return table.concat(b, "+")
end

local function fmt_x()
  local b = {}
  for _, e in ipairs(EXEC) do
    local n = xcount[e[2]]
    if n and n > 0 then b[#b + 1] = string.format("%s=%d", e[2], n) end
  end
  return table.concat(b, ",")
end

-- Valor de $2100 escrito este frame: primera fuente no vacia, en orden de
-- fiabilidad (exec > forma explicita > forma de 4 argumentos).
local function fmt_ini()
  for _, k in ipairs({ "x", "m6", "m1" }) do
    if ini_src[k] and #ini_src[k] > 0 then return fmt_list(ini_src[k]) end
  end
  return ""
end

local function ini_source()
  for _, k in ipairs({ "x", "m6", "m1" }) do
    if ini_src[k] and #ini_src[k] > 0 then return k end
  end
  return "-"
end

local function fmt_src()
  local b = {}
  b[#b + 1] = "x=" .. (#(ini_src["x"] or {}))
  if store_frame_first then b[#b + 1] = string.format("pc=%06X", store_frame_first) end
  if #store_frame_db > 0 then
    local d = {}
    for i = 1, math.min(#store_frame_db, 8) do
      d[i] = string.format("%02X", store_frame_db[i])
    end
    b[#b + 1] = "db=" .. table.concat(d, "")
  end    b[#b + 1] = "m1=" .. (#(ini_src["m1"] or {}))
  b[#b + 1] = "m6=" .. (#(ini_src["m6"] or {}))
  b[#b + 1] = "mA1=" .. tostring(mem_all["mA1"] or 0)
  b[#b + 1] = "mA4=" .. tostring(mem_all["mA4"] or 0)
  b[#b + 1] = "can1=" .. tostring(can_hits["can1"] or 0)
  b[#b + 1] = "can6=" .. tostring(can_hits["can6"] or 0)
  return table.concat(b, " ")
end

local function snap(addr)
  local v = try(emu.read, addr, MT_SNES)
  if v == nil then v = try(emu.read, addr) end
  return v
end

-- Exec callback de un sitio que almacena en $2100: en el momento del callback
-- la instruccion aun NO se ha ejecutado, asi que el valor a almacenar esta en A
-- (o en X para STX) y DB es el banco de datos vigente.  Un STA absoluto con
-- DB!=0 NO llega al registro (cae en WRAM/ROM): por eso se registra DB.
local function make_store_cb(pc24, bytes)
  local is_x = (bytes == "8E0021")
  return function()
    local st = try(emu.getCpuState) or {}
    local v = is_x and (st.X or st.x or 0) or (st.A or st.a or 0)
    local db = st.DB or st.db or 0
    store_hits[pc24] = (store_hits[pc24] or 0) + 1
    if not store_frame_first then store_frame_first = pc24 end
    if #store_frame_db < 16 then store_frame_db[#store_frame_db + 1] = db end
    note_ini("x", v)
  end
end

local function on_end_frame()
  frame = frame + 1
  if frame < START_FRAME then reset_frame_counters(); return end

  local st = try(emu.getCpuState) or {}
  local pc = st.PC or st.pc or 0
  local d  = st.D  or st.d  or 0
  local db = st.DB or st.db or 0
  local mc = try(emu.getMasterClock) or 0

  local row = string.format("%d\t%d\t%06X\t%04X\t%02X\t%02X\t%02X\t%02X\t%02X\t%04X\t%s\t%s",
    frame, mc, pc, d, db,
    snap(0x0000E4) or -1, snap(0x0000E5) or -1,
    snap(0x0000DA) or -1, snap(0x000AFB) or -1,
    (snap(0x000AFD) or -1) + (snap(0x000AFE) or 0) * 256,
    fmt_ini(), fmt_x()) .. "\t" .. fmt_rd()

  -- escrituras a sombras: solo cuando ocurren (para no inflar el TSV)
  local parts = {}
  for _, nm in ipairs({ "DA", "E4", "AF9", "AFB", "AFD" }) do
    local t = wrl[nm]
    if t and #t > 0 then parts[#parts + 1] = nm .. "=" .. fmt_list(t) end
  end
  -- Columnas 14 y 15: SIEMPRE presentes (aunque vayan vacias) para que las
  -- posiciones sean fijas y nadie tenga que adivinar donde esta cada cosa.
  row = row .. "\t" .. table.concat(parts, " ") .. "\t" .. fmt_src()

  if out then out:write(row .. "\n") end

  if frame % LOG_EVERY == 0 then
    local msg = string.format(
      "probe fr=%d pc=%06X E4=%02X DA=%02X AFB=%02X AFD=%04X ini=%s(%s) src[%s] can1=%s can6=%s",
      frame, pc, snap(0x0000E4) or -1, snap(0x0000DA) or -1,
      snap(0x000AFB) or -1, snap(0x000AFD) or -1,
      fmt_ini(), ini_source(), fmt_src(),
      tostring(can_hits["can1"] or 0), tostring(can_hits["can6"] or 0))
    log(msg)
    status(msg)
  end

  reset_frame_counters()

  if END_FRAME > 0 and frame >= END_FRAME then
    local funcionan = {}
    for _, e in ipairs(EXEC) do if xseen[e[2]] then funcionan[#funcionan + 1] = e[2] end end
    log(string.format("probe END fr=%d -> %s", frame, tostring(out_path_used)))
    status(string.format("FIN fr=%d -> %s", frame, tostring(out_path_used)))
    status("rutinas vistas: " .. table.concat(funcionan, " "))
    local sitios = {}
    for pc, n in pairs(store_hits) do sitios[#sitios + 1] = { pc, n } end
    table.sort(sitios, function(a, b) return a[2] > b[2] end)
    local sb = {}
    for i = 1, math.min(#sitios, 24) do
      sb[i] = string.format("%06X=%d", sitios[i][1], sitios[i][2])
    end
    status("sitios de $2100 ejecutados: " .. table.concat(sb, " "))
    status(string.format("fuentes de $2100: m6(byte exacto)=%d  contraste mA1(escrituras en 0000..2100)=%d",
      mem_hits["m6"] or 0, mem_all["mA1"] or 0))
    status(string.format("canario de pila: can1=%d can6=%d",
      can_hits["can1"] or 0, can_hits["can6"] or 0))
    if out then out:flush(); out:close(); out = nil end
    try(emu.stop, 1)
  end
end

-- -- arranque del script --------------------------------------------------
local function rutas_candidatas()
  local lista = {}
  if OUT_PATH then return { OUT_PATH } end
  local dir = nil
  local ri = try(emu.getRomInfo)
  if type(ri) == "table" then dir = ri.filePath or ri.path end
  if dir then dir = dir:match("^(.*)[/\\][^/\\]*$") end
  if not dir then dir = try(emu.getScriptDataFolder) end
  if dir then lista[#lista + 1] = dir .. "/" .. OUT_NAME end
  for _, p in ipairs(CANDIDATOS) do lista[#lista + 1] = p end
  lista[#lista + 1] = OUT_NAME
  return lista
end

local function abrir_salida()
  local intentos = {}
  for _, p in ipairs(rutas_candidatas()) do
    local f = io.open(p, "w")
    if f then
      log("probe SALIDA OK: " .. p .. (#intentos > 0 and ("  (tras fallar: " .. table.concat(intentos, " | ") .. ")") or ""))
      return f, p
    end
    intentos[#intentos + 1] = tostring(p)
  end
  log("probe ERROR: no puedo abrir ninguna ruta: " .. table.concat(intentos, " | "))
  return nil, nil
end

local function main()
  status("main(): buscando ruta de salida")
  out, out_path_used = abrir_salida()
  status("main(): ruta de salida = " .. tostring(out_path_used))
  if out then
    out:write("# fr\tmaster\tpc\tD\tDB\tE4\tE5\tDA\tAFB\tAFD\tini\tx\trdcnt\twshadow\tsrc\n")
    out:flush()
  end

  -- 1) Sitios de ROM que almacenan en $2100 (via exec: la que esta demostrada).
  local ns = 0
  for _, s in ipairs(STORE2100) do
    local a = s[1]
    local cb = make_store_cb(a, s[2])
    if add_mem_cb(cb, CB_EXEC, a, a) then ns = ns + 1 end
  end

  -- 2) $2100 por callback de ESCRITURA del byte unico.
  --
  --    La forma 3 (con cpuType y memoryType EXPLICITOS) es la buena y la unica
  --    que actua de fuente de valor (`m6`).  La forma 1 se registra solo como
  --    contador de contraste (`mem_hits["m1"]`), sin usar su valor.
  --
  --    La forma 4 se ELIMINO: `addMemoryCallback(cb, ctype, mem, start, end)`
  --    NO es una variante valida de la API -Mesen la interpreta como
  --    (start=mem=0, end=$2100), o sea un callback sobre TODO el rango bajo
  --    ($0000..$2100).  Eso es lo que en la v3 daba `mMT=251348` y hacia que la
  --    columna `ini` fuese un volcado de escrituras de toda la RAM baja en vez
  --    del valor escrito a $2100.  Si hace falta contrastar el rango, se mira
  --    `mA1/mA4` (cuantas escrituras cayeron en $0000..$2100), pero nunca como
  --    valor de $2100.
  local nm1 = add_mem_cb_form(1, function() mem_all["mA1"] = (mem_all["mA1"] or 0) + 1 end,
                             CB_WRITE, 0x000000, 0x002100)
  local nm6 = add_mem_cb_form(3, function(_, v) note_ini("m6", v) ; mem_hits["m6"] = (mem_hits["m6"] or 0) + 1 end,
                             CB_WRITE, 0x002100, 0x002100)

  -- 3) Canario de pila: prueba si los callbacks de ESCRITURA disparan.
  local nc1 = add_mem_cb_form(1, function() can_hits["can1"] = (can_hits["can1"] or 0) + 1 end,
                             CB_WRITE, CANARY[1], CANARY[2])
  local nc6 = add_mem_cb_form(3, function() can_hits["can6"] = (can_hits["can6"] or 0) + 1 end,
                             CB_WRITE, CANARY[1], CANARY[2])

  -- 4) Rutinas vigiladas (contexto: quien gobierna cada tramo).
  local nx = 0
  for _, e in ipairs(EXEC) do
    local a = e[1]
    local cb = function() bump(a) end
    if add_mem_cb(cb, CB_EXEC, a, a) then nx = nx + 1 end
  end

  -- 5) Sombras WRAM en escritura.
  local nw = 0
  for _, r in ipairs(WRANGE) do
    local name = r[3]
    local cb = function(_, value) note_write(name, value) end
    if add_mem_cb(cb, CB_WRITE, r[1], r[2]) then nw = nw + 1 end
  end

  -- 6) Lecturas (contadores por frame: mide las esperas del invitado).
  local nr = 0
  for _, r in ipairs(RRANGE) do
    local name = r[3]
    local cb = function(_, value)
      rrc[name] = (rrc[name] or 0) + 1
      rlast[name] = value or 0
    end
    if add_mem_cb(cb, CB_READ, r[1], r[2]) then nr = nr + 1 end
  end

  -- NO registrar reset en EV_STARTFRAME: borraria la ventana de vblank, que es
  -- donde el juego escribe $2100 (ver nota junto a reset_frame_counters).
  pcall(emu.addEventCallback, on_end_frame, EV_ENDFRAME)

  log(string.format("probe LISTO: stores=%d/%d rutinas=%d/%d sombras=%d/%d lecturas=%d/%d out=%s frames %d..%d",
    ns, #STORE2100, nx, #EXEC, nw, #WRANGE, nr, #RRANGE,
    tostring(out_path_used), START_FRAME, END_FRAME))
  log("probe formas aceptadas: " .. table.concat(registered_forms, " "))
  status(string.format("LISTO: stores=%d/%d rutinas=%d/%d sombras=%d/%d lecturas=%d/%d out=%s frames %d..%d",
    ns, #STORE2100, nx, #EXEC, nw, #WRANGE, nr, #RRANGE,
    tostring(out_path_used), START_FRAME, END_FRAME))
  status(string.format("$2100 por memoria: forma3(explicita,fuente)=%s  forma1(rango 0000..2100,contraste)=%s",
    tostring(nm6), tostring(nm1)))
  status(string.format("canario de pila registrado: forma1=%s forma3=%s", tostring(nc1), tostring(nc6)))
  status("formas aceptadas (indice(rango)): " .. table.concat(registered_forms, " | "))
end

main()
