-- mesen_so_trace.lua - Star Ocean (Japan) - GRABADORA DE PARTIDA + TRAZA POR FRAME
-- ============================================================================
-- QUE HACE
--   Mientras juegas en Mesen graba, frame a frame:
--     * las PULSACIONES del pad 1 (en el mismo formato de mascara que usa el
--       motor recomp, de modo que el fichero de replay se puede meter tal cual
--       en SNESRECOMP_REPLAY_FILE y reproducir tu partida);
--     * el estado del invitado (CPU, SPC700) y del PPU;
--     * el handshake con el APU: escrituras y lecturas de $2140-$2143 desde los
--       DOS lados (CPU y SPC), y las escrituras del SPC al DSP ($F2/$F3), de
--       donde sale el contador de KEY-ON (registro $4C) -que es la metrica con
--       la que se detecto que el secuenciador se para con la deadline-;
--     * los valores escritos a $2100 (INIDISP: fundidos y logos; es el marcador
--       de fidelidad del modelo de frame) y a las sombras $DA/$E4/$0AF9/$0AFB/$0AFD;
--     * cuantas veces se ejecuta el bucle caliente $C0859D-$C085D0 (el
--       handshake con el IPL: 11 PCs que se comen el 79% de las instrucciones
--       de la intro y el hueco de fps del logo).
--
-- COMO SE USA (MesenCE / Mesen-S)
--   1. Depurar -> Ventana de script -> Abrir script -> este fichero -> Ejecutar.
--      (Si tu build no tiene esa ruta, busca "Script window"/"Lua".)
--   2. Cargar o reiniciar "Star Ocean (Japan).sfc" DESDE EL ARRANQUE.
--   3. Jugar normalmente. El script escribe su progreso en la ventana de script
--      cada LOG_EVERY frames.
--   4. Al terminar: para el script (o llega a END_FRAME). Los ficheros se
--      cierran solos, queda un resumen en el log de estado y Mesen SIGUE
--      funcionando (emu.stop() solo se llama si pones PARAR_AL_TERMINAR=true).
--
-- SALIDAS (en la carpeta del ROM, o en las rutas de CANDIDATOS)
--   <rom>_trace.tsv    : una fila por frame (34 columnas, ver cabecera del fichero)
--   <rom>_events.tsv   : un evento por linea (escrituras de $2100, handshake APU,
--                        escrituras al DSP, key-on, sombras, NMI/IRQ)
--   <rom>_replay.txt   : SOLO pulsaciones, formato del motor: "<frame> <mascara>"
--                        (listo para SNESRECOMP_REPLAY_FILE)
--   <rom>_trace_status.log : lo mismo que la ventana de script, en disco
--
-- API: NO supuesta.  Verificada en dos fuentes:
--   (a) el fuente de Mesen-S (Core/LuaApi.cpp), y
--   (b) la referencia de API JSON que va incrustada en el propio Mesen.exe
--       (busca "addMemoryCallback" en el binario), que es la de TU build.
--   De ahi salen estos hechos:
--     emu.getInput(port, subPort=0) -> {a,b,x,y,l,r,start,select,up,down,left,right}
--     emu.addMemoryCallback(callback, callbackType, start, end, cpuType, memType)
--     emu.addEventCallback(callback, eventType)
--     eventType (orden del enum): nmi=0 irq=1 startFrame=2 endFrame=3 reset=4
--       scriptEnded=5 inputPolled=6 stateLoaded=7 stateSaved=8
--     cpuType: snes=0 spc=1 necDsp=2 ...   memType: snesMemory=0 spcMemory=1 ...
--     existen emu.getState, emu.getCpuState(cpuType), emu.getMasterClock,
--     emu.getCpuCycleCount(cpuType), emu.stop(exitCode)
--   Los enums se leen de las tablas de runtime; los numeros de arriba son solo
--   respaldo si esa tabla no existiera.  Los hooks del SPC llevan cpuType
--   SIEMPRE explicito: sin el, $00F2/$00F3 se engancharian en el bus de la CPU
--   (que en banco 0 es WRAM) y saldrian key-on falsos.
--
-- SI ALGO NO CUADRA (que mirar en el log de estado)
--   * "LISTO: ... hooks_mem=N formas=a/b/c getInput=1 spc_hooks=si" -> el
--     script arranco.  formas: que variante de addMemoryCallback acepto la
--     build (1 = sin cpuType, 2 = con cpuType, 3 = con cpuType+memType).
--   * "claves getState()" -> volcado UNO a uno de los campos que existen de
--     verdad en tu build (asi no hay que adivinar nombres de campos).
--   * "spcw=N/M" -> N es la variante de DATOS y M la de diagnostico.  Si N=0
--     mientras M>0, los hooks del SPC no disparan: pon SPC_SIN_MEMTYPE=true y
--     vuelve a grabar (el propio log lo avisa).
--   * "AVISO: la grabacion NO empezo en el arranque" -> lanzaste el script con
--     el juego ya en marcha: el replay no se alinea con el motor recomp.
--   * "<< DESALINEADO" -> los frames del script se han separado de los del PPU:
--     la traza de ese tramo no es fiable, no la uses.
-- ============================================================================

-- --------------------------------------------------------------------------
-- Configuracion
-- --------------------------------------------------------------------------
local TAG         = "so_trace"   -- prefijo de los ficheros de salida
local START_FRAME = 1            -- 1 = desde el arranque
local END_FRAME   = 0            -- 0 = sin limite (parar a mano)
local LOG_EVERY   = 60           -- resumen en la ventana de script
local LOG_READS   = false        -- volcar CADA lectura de $2140-$2143 (muy
                                 -- abundante: ~8.600/frame en el handshake).
                                 -- Con false se cuenta por frame (columna r2140).
local OUT_DIR     = nil          -- nil = carpeta del ROM / candidatos; ruta = forzar
local PARAR_AL_TERMINAR = false  -- true = llamar a emu.stop() al terminar (CIERRA
                                 -- Mesen: existe para el modo --testRunner).
                                 -- Por defecto NO: al acabar se cierran los
                                 -- ficheros y el juego sigue corriendo.
local SPC_SIN_MEMTYPE = false    -- false = registrar los hooks del SPC pasando
                                 -- memType explicito (spcMemory): es la forma
                                 -- canonica en MesenCE.  true = solo cpuType.
                                 -- Si en tu build la canonica no dispara, el log
                                 -- lo dice y basta ponerlo a true.

-- Bucle caliente del handshake con el IPL (desensamblado de la version actual).
local HOT_LO, HOT_HI = 0xC0859D, 0xC085D0
-- Rangos vigilados en escritura (sombras que gobiernan fundidos/motor).
local SHADOW = {
  { 0x0000DA, 0x0000DA, "DA"   },
  { 0x0000E4, 0x0000E5, "E4"   },
  { 0x000AF9, 0x000AFA, "AF9"  },
  { 0x000AFB, 0x000AFC, "AFB"  },
  { 0x000AFD, 0x000AFE, "AFD"  },
}
local REGS = {                   -- registros sueltos que interesan
  { 0x002100, 0x002100, "2100" },   -- INIDISP (fundidos)
  { 0x004200, 0x004200, "4200" },   -- NMITIMEN (fuente del tick por frame)
  { 0x004212, 0x004212, "4212" },   -- HVBJOY (la espera de vblank)
}
local APU_LO, APU_HI = 0x002140, 0x002143        -- puertos del CPU
local SPC_APU_LO, SPC_APU_HI = 0x0000F4, 0x0000F7  -- los mismos desde el SPC
local DSP_ADDR, DSP_DATA = 0x0000F2, 0x0000F3    -- puertos del DSP desde el SPC
local DSP_KON = 0x4C                              -- registro de key-on

local CANDIDATOS = {
  "E:\\Experimento Hermes\\Documentacion\\TracesMesen\\",
  "F:\\Recompilador Super Nintendo\\Mesen\\",
  "F:\\SOR\\",
}

-- --------------------------------------------------------------------------
-- Enums (runtime primero, valor documentado despues)
-- --------------------------------------------------------------------------
local function enum_or(tbl, key, fallback)
  if tbl ~= nil and tbl[key] ~= nil then return tbl[key] end
  return fallback
end

-- callbackType / memCallbackType: read=0, write=1, exec=2 en las dos APIs.
local CB_TBL = (emu and (emu.callbackType or emu.memCallbackType)) or nil
local CB_READ  = enum_or(CB_TBL, "read",  0)
local CB_WRITE = enum_or(CB_TBL, "write", 1)
local CB_EXEC  = enum_or(CB_TBL, "exec",  2)

-- cpuType: cpu/snes = 0 en las dos APIs; spc = 1 en Mesen-S.
local CT_CPU = enum_or(emu and emu.cpuType, "snes", enum_or(emu and emu.cpuType, "cpu", 0))
local CT_SPC = enum_or(emu and emu.cpuType, "spc", nil)   -- nil = no arriesgar

-- memType del bus de la CPU: snesMemory (MesenCE) o cpu (Mesen-S); los dos = 0.
local MT_CPU = enum_or(emu and emu.memType, "snesMemory", enum_or(emu and emu.memType, "cpu", 0))
-- memType del SPC: spcMemory (MesenCE) o spc (Mesen-S).
local MT_SPC = enum_or(emu and emu.memType, "spcMemory", enum_or(emu and emu.memType, "spc", 1))

-- eventType: solo se usa el valor de RUNTIME, salvo endFrame, que esta
-- comprobado en esta maquina (la sonda mesen_intro_probe.lua contaba frames
-- correctamente con 3).  Para el resto NO se adivina: si la tabla no existe,
-- el evento se deja sin registrar y se avisa en el log.  Un enum mal resuelto
-- produciria datos creibles y falsos, que es el peor caso posible.
local function ev(name, fallback)
  local t = emu and emu.eventType
  if t ~= nil and t[name] ~= nil then return t[name] end
  return fallback
end
-- Respaldo documentado (orden del enum en la referencia de API incrustada en
-- Mesen.exe: nmi, irq, startFrame, endFrame, reset, scriptEnded, inputPolled...).
-- En el uso normal se toma el valor de runtime, esto solo actua si falta la tabla.
local EV_ENDFRAME    = ev("endFrame", 3)
local EV_NMI         = ev("nmi", 0)
local EV_IRQ         = ev("irq", 1)
local EV_RESET       = ev("reset", 4)
local EV_SCRIPTENDED = ev("scriptEnded", 5)
local EV_INPUTPOLLED = ev("inputPolled", 6)

-- --------------------------------------------------------------------------
-- Estado
-- --------------------------------------------------------------------------
local frame = 0                 -- frame de host en curso (1-based; se reinicia en reset)
local out_tsv, out_ev, out_rep, out_status = nil, nil, nil, nil
local path_tsv, path_ev, path_rep, path_status = nil, nil, nil, nil
local forms_ok = {}             -- formas de addMemoryCallback que han funcionado
local api = {}                  -- diagnostico de la API para volcar al log

-- contadores por frame
local cnt = {}
local ini_vals = {}             -- valores escritos a $2100 este frame
local w4200_vals = {}           -- valores escritos a $4200 este frame
local ev_nmi, ev_irq = 0, 0     -- eventos NMI/IRQ del frame
local kon_total = 0             -- key-on acumulados (registro $4C bit0)
local kon_frame = 0
local dsp_addr = 0              -- latch del registro del DSP ($F2)
local pad_prev = 0              -- ultima mascara escrita en el replay
local poll_mask = nil           -- mascara capturada en el evento inputPolled
local poll_hook_ok = false
local getinput_form = nil       -- que forma de getInput ha funcionado

local function reset_frame_counters()
  cnt = {}
  ini_vals = {}
  w4200_vals = {}
  ev_nmi, ev_irq = 0, 0
  kon_frame = 0
  poll_mask = nil
end

local function try(fn, ...)
  local ok, res = pcall(fn, ...)
  if ok then return res end
  return nil
end

local function log(msg)
  msg = tostring(msg)
  if emu and emu.log then pcall(emu.log, msg) end
  if out_status then
    out_status:write(string.format("%s %s\n", os.date("%H:%M:%S"), msg))
  end
end

-- --------------------------------------------------------------------------
-- Salidas
-- --------------------------------------------------------------------------
local function basename_noext(p)
  if not p then return TAG end
  local b = p:match("[^/\\]+$") or p
  b = b:gsub("%.[^%.]*$", "")          -- quita la extension
  return (b:gsub("[(%)%s]+", "_"))     -- comodo para la consola
end

local COLUMNAS = {
  "fr", "in", "pin", "btn",                 -- frame, mascara (fin de frame), mascara en el poll, botones
  "master", "cyc", "pc", "a", "x", "y", "sp", "d", "db", "p",  -- CPU
  "bright", "bg", "scan", "ppufr",          -- PPU
  "hc", "r2140", "w2140", "spcw", "ini", "kon", "konf",        -- handshake/sonido
  "spcpc", "spca", "spcx", "spcy", "spcsp", "spcps",           -- SPC700
  "r4212", "sdnmi", "sw4200",               -- varios
}

local CABECERA_TXT = table.concat({
  "# Traza de partida de Star Ocean (Japan) grabada desde Mesen.",
  "# Cada fila es un frame. Columnas (separadas por TAB):",
  "#   1  fr       frame de host (1 = arranque; se reinicia en cada reset)",
  "#   2  in       mascara del pad al FINAL del frame (hex, orden $4218:",
  "#               b0=B b1=Y b2=Sel b3=Start b4=Up b5=Down b6=Left b7=Right",
  "#               b8=A b9=X b10=L b11=R). Es el MISMO formato que usa el",
  "#               motor recomp en SNESRECOMP_REPLAY_FILE.",
  "#   3  pin      mascara en el momento exacto del poll de input (vacio si",
  "#               el emulador no expone el evento inputPolled)",
  "#   4  btn      botones pulsados, tokens unidos por '+' (vacio = ninguno)",
  "#   5  master   masterClock absoluto del invitado",
  "#   6  cyc      ciclos de CPU absolutos",
  "#   7  pc       PC de la CPU, 24 bits (K:PC)",
  "#   8-13 a x y sp d db p   registros de la CPU",
  "#   14 bright   brillo de pantalla del PPU (INIDISP)",
  "#   15 bg       modo de fondo (BGMODE)",
  "#   16 scan     scanline del PPU al cerrar el frame",
  "#   17 ppufr    contador de frames del PPU (para alinear con el nuestro)",
  "#   18 hc       instrucciones ejecutadas en el bucle caliente $C0859D-$C085D0",
  "#   19 r2140    lecturas del CPU a $2140-$2143 (handshake)",
  "#   20 w2140    escrituras del CPU a $2140-$2143",
  "#   21 spcw     escrituras del SPC a $2140-$2143 (los puertos vistos desde el SPC)",
  "#   22 ini      valores escritos a $2100 este frame ('80' o '80+0F'), vacio si ninguno",
  "#   23 kon      key-on ($4C bit0) acumulados desde el arranque",
  "#   24 konf     key-on de este frame",
  "#   25-30 spcpc spca spcx spcy spcsp spcps   estado del SPC700",
  "#   32 r4212    lecturas del CPU a $4212 (espera de vblank)",
  "#   33 sdnmi    NMIs entregadas este frame",
  "#   34 sw4200   valores escritos a $4200 (NMITIMEN) este frame",
  "#",
  "# Ficheros hermanos de este TSV:",
  "#   *_events.tsv : cada escritura/lectura vigilada, con frame y reloj",
  "#   *_replay.txt : solo pulsaciones, '<frame> <mascara>', formato del motor",
  nil,
}, "\n")

local function abrir_salidas()
  local intentos = {}
  local lista = {}

  -- 1) carpeta del ROM  2) carpeta de datos del script  3) candidatos fijos
  local ri = try(emu.getRomInfo)
  local dir_rom = nil
  if type(ri) == "table" then
    dir_rom = ri.path or ri.filePath
    if dir_rom then dir_rom = dir_rom:match("^(.*)[/\\][^/\\]*$") end
  end
  if dir_rom then
    lista[#lista + 1] = dir_rom .. "/" .. basename_noext(ri.name) .. "_" .. TAG
  end
  local sd = try(emu.getScriptDataFolder)
  if type(sd) == "string" and sd ~= "" then
    lista[#lista + 1] = sd:gsub("\\", "/") .. "/" .. TAG
  end
  if OUT_DIR then lista = { OUT_DIR:gsub("\\", "/") .. "/" .. TAG } end
  for _, p in ipairs(CANDIDATOS) do
    lista[#lista + 1] = (p:gsub("\\", "/")) .. TAG
  end
  lista[#lista + 1] = TAG

  for _, base in ipairs(lista) do
    local t = io.open(base .. "_trace.tsv", "w")
    if t then
      out_tsv = t
      path_tsv = base .. "_trace.tsv"
      out_ev  = io.open(base .. "_events.tsv", "w")
      path_ev = base .. "_events.tsv"
      out_rep = io.open(base .. "_replay.txt", "w")
      path_rep = base .. "_replay.txt"
      -- El log de estado se ABRE EN MODO APPEND: cada corrida deja su sesion,
      -- asi se pueden comparar dos grabaciones sin perder la anterior.
      out_status = io.open(base .. "_trace_status.log", "a")
      path_status = base .. "_trace_status.log"
      if out_status then
        out_status:write(string.format("\n=== sesion %s ===\n", os.date("%Y-%m-%d %H:%M:%S")))
      end
      local nota = ""
      if #intentos > 0 then nota = "  (tras fallar: " .. table.concat(intentos, " | ") .. ")" end
      pcall(emu.log, TAG .. ": salida = " .. base .. nota)
      return true
    end
    intentos[#intentos + 1] = tostring(base)
  end
  pcall(emu.log, TAG .. " ERROR: no puedo escribir en ninguna ruta: " .. table.concat(intentos, " | "))
  return false
end

-- --------------------------------------------------------------------------
-- Formato de filas / eventos
-- --------------------------------------------------------------------------
local TOKENS = {
  { 0x0001, "B" },  { 0x0002, "Y" },  { 0x0004, "Sel" }, { 0x0008, "Sta" },
  { 0x0010, "Up" }, { 0x0020, "Dn" }, { 0x0040, "Lt" },  { 0x0080, "Rt" },
  { 0x0100, "A" },  { 0x0200, "X" },  { 0x0400, "L" },   { 0x0800, "R" },
}

local function btn_str(mask)
  local b = {}
  for _, t in ipairs(TOKENS) do
    if mask % (t[1] * 2) >= t[1] then b[#b + 1] = t[2] end
  end
  return table.concat(b, "+")
end

local function fmt_ini()
  if #ini_vals == 0 then return "" end
  local b = {}
  for i = 1, math.min(#ini_vals, 32) do b[i] = string.format("%02X", ini_vals[i]) end
  return table.concat(b, "+")
end

local function fmt_w4200()
  if #w4200_vals == 0 then return "" end
  local b = {}
  for i = 1, math.min(#w4200_vals, 16) do b[i] = string.format("%02X", w4200_vals[i]) end
  return table.concat(b, "+")
end

local function evento(kind, addr, val, src, nota)
  if not out_ev then return end
  local st = api.estado_cache or {}
  local mc = st.masterClock or 0
  out_ev:write(string.format("%d\t%d\t%s\t%s\t%04X\t%02X\t%s\n",
    frame, mc, src or "cpu", kind, addr or 0, (val or 0) % 256, nota or ""))
end

-- --------------------------------------------------------------------------
-- Registro de callbacks de memoria (varias formas: Mesen-S y MesenCE)
-- --------------------------------------------------------------------------
-- Formas probadas en orden:
--   1) (cb, ctype, start, end)                          -> cpu/memType por defecto
--   2) (cb, ctype, start, end, cpuType)
--   3) (cb, ctype, start, end, cpuType, memType)        -> canonica de MesenCE
-- OJO: para hooks del SPC NUNCA vale la forma sin cpuType (form 1): engancharia
-- el bus de la CPU en $00F2/$00F3, que en banco 0 es WRAM, y produciria
-- "key-on" falsos.  Con solo_explicita=true la forma 1 no se intenta.
-- mem_type: numero = usarlo; false = no pasarlo; nil = MT_CPU.
local function add_mem_cb(cb, ctype, start_addr, end_addr, cpu_type, mem_type, solo_explicita)
  cpu_type = cpu_type or CT_CPU
  if mem_type == false then mem_type = nil
  elseif mem_type == nil then mem_type = MT_CPU end
  local formas = {}
  if mem_type ~= nil then
    formas[#formas + 1] = { 3, function()
      return emu.addMemoryCallback(cb, ctype, start_addr, end_addr, cpu_type, mem_type) end }
  end
  formas[#formas + 1] = { 2, function()
    return emu.addMemoryCallback(cb, ctype, start_addr, end_addr, cpu_type) end }
  if not solo_explicita then
    formas[#formas + 1] = { 1, function()
      return emu.addMemoryCallback(cb, ctype, start_addr, end_addr) end }
  end
  for _, f in ipairs(formas) do
    if pcall(f[2]) then
      forms_ok[f[1]] = (forms_ok[f[1]] or 0) + 1
      return f[1]
    end
  end
  return nil
end

-- --------------------------------------------------------------------------
-- Sondas
-- --------------------------------------------------------------------------
local function on_reset()
  -- A partir del primer frame grabado, un reset mezcla DOS sesiones: el
  -- contador de frames vuelve a 1 y el replay dejaria de ser reproducible.
  -- Se avisa en el log y NO se escribe nada raro en el fichero de replay
  -- (que debe contener solo lineas "<frame> <mascara>" validas).
  if frame > 0 then
    log(string.format("%s AVISO: reset del invitado en fr=%d. El replay grabado " ..
      "YA NO es reproducible desde el arranque: para una partida limpia, " ..
      "deten el script, borra los TSV y reinicia el script antes del ROM.", TAG, frame))
  end
  if out_tsv then out_tsv:write("# --- reset del invitado (aqui empieza otra sesion) ---\n") end
  evento("reset", 0, 0, "sys", "reset del invitado")
  frame = 0
  pad_prev = 0
  kon_total = 0
  reset_frame_counters()
end

local function on_nmi() ev_nmi = ev_nmi + 1 end
local function on_irq() ev_irq = ev_irq + 1 end

local function on_input_polled()
  -- Mejor sitio para leer el pad: es el instante en que el juego lo lee.
  if getinput_form == 1 then poll_mask = try(emu.getInput, 0)
  elseif getinput_form == 2 then poll_mask = try(emu.getInput, 0, 0)
  else poll_mask = nil end
  if type(poll_mask) == "table" then
    local m = 0
    if poll_mask.b then m = m + 0x0001 end
    if poll_mask.y then m = m + 0x0002 end
    if poll_mask.select then m = m + 0x0004 end
    if poll_mask.start then m = m + 0x0008 end
    if poll_mask.up then m = m + 0x0010 end
    if poll_mask.down then m = m + 0x0020 end
    if poll_mask.left then m = m + 0x0040 end
    if poll_mask.right then m = m + 0x0080 end
    if poll_mask.a then m = m + 0x0100 end
    if poll_mask.x then m = m + 0x0200 end
    if poll_mask.l then m = m + 0x0400 end
    if poll_mask.r then m = m + 0x0800 end
    poll_mask = m
  else
    poll_mask = nil
  end
end

local function leer_pad()
  if getinput_form == 1 then return try(emu.getInput, 0)
  elseif getinput_form == 2 then return try(emu.getInput, 0, 0) end
  return nil
end

local function pad_mask()
  local t = leer_pad()
  if type(t) ~= "table" then return nil end
  local m = 0
  if t.b then m = m + 0x0001 end
  if t.y then m = m + 0x0002 end
  if t.select then m = m + 0x0004 end
  if t.start then m = m + 0x0008 end
  if t.up then m = m + 0x0010 end
  if t.down then m = m + 0x0020 end
  if t.left then m = m + 0x0040 end
  if t.right then m = m + 0x0080 end
  if t.a then m = m + 0x0100 end
  if t.x then m = m + 0x0200 end
  if t.l then m = m + 0x0400 end
  if t.r then m = m + 0x0800 end
  return m
end

local function bump(nombre, n)
  cnt[nombre] = (cnt[nombre] or 0) + (n or 1)
end

-- --------------------------------------------------------------------------
-- Escritura de la fila de frame
-- --------------------------------------------------------------------------
local function dump_claves(t)
  if type(t) ~= "table" then return "-" end
  local b = {}
  for k in pairs(t) do b[#b + 1] = tostring(k) end
  table.sort(b)
  return table.concat(b, ",")
end

local function estado()
  local st = try(emu.getState)
  if type(st) == "table" then
    api.estado_cache = st
    -- Autodiagnostico: se vuelca UNA vez la forma real de las tablas de estado
    -- de esta build, para no tener que suponer nombres de campos.
    if not api.claves then
      api.claves = true
      log(string.format("%s claves getState(): raiz=[%s]", TAG, dump_claves(st)))
      log(string.format("%s   cpu=[%s]", TAG, dump_claves(st.cpu)))
      log(string.format("%s   ppu=[%s]", TAG, dump_claves(st.ppu)))
      log(string.format("%s   spc=[%s]", TAG, dump_claves(st.spc)))
    end
    return st
  end
  api.estado_cache = {}
  return {}
end

-- Estado de un procesador: emu.getCpuState(cpuType) es el camino directo (existe
-- en MesenCE); la sub-tabla de getState() es el respaldo.
local function cpu_state(cpu_type, clave)
  if cpu_type ~= nil then
    local cs = try(emu.getCpuState, cpu_type)
    if type(cs) == "table" then return cs end
  end
  local st = api.estado_cache or {}
  if type(st[clave]) == "table" then return st[clave] end
  return {}
end

local function g(t, ...)
  if type(t) ~= "table" then return nil end
  for _, k in ipairs({ ... }) do
    if t[k] ~= nil then return t[k] end
  end
  return nil
end

local function nz(v, f)
  if v == nil then return f or 0 end
  return v
end

local function on_end_frame()
  frame = frame + 1
  if frame < START_FRAME then reset_frame_counters(); return end

  local st = estado()
  local cpu = cpu_state(CT_CPU, "cpu")
  local ppu = (type(st.ppu) == "table") and st.ppu or {}
  local spc = (CT_SPC ~= nil) and cpu_state(CT_SPC, "spc") or ((type(st.spc) == "table") and st.spc or {})
  local pc24 = (nz(g(cpu, "k", "K"), 0) * 65536) + nz(g(cpu, "pc", "PC"), 0)

  -- Reloj: emu.getMasterClock()/getCpuCycleCount() son nativos de esta build y
  -- mas baratos que rebuscar en las tablas de estado.
  local mc = try(emu.getMasterClock)
  if mc == nil then mc = st.masterClock end
  local cyc = try(emu.getCpuCycleCount, CT_CPU)
  if cyc == nil then cyc = g(cpu, "cycleCount") end

  -- Alineacion: si el script se lanzo con el juego ya en marcha, el frame 1 de
  -- esta grabacion NO es el arranque de la ROM, y ese replay no se alineara con
  -- el motor recomp (que cuenta desde el frame 1 tras cargar la ROM).  Se fija
  -- el desfase en el primer frame y se vigila que no cambie.
  local ppu_fr = nz(g(ppu, "frameCount"), -1)
  if api.off0 == nil then
    api.off0 = (ppu_fr >= 0) and (ppu_fr - frame) or 0
    if api.off0 ~= 0 then
      log(string.format("%s AVISO: la grabacion NO empezo en el arranque: desfase " ..
        "de %d frames respecto al contador del PPU. Este replay no se alinea con " ..
        "el motor recomp tal cual; hay que restarlo al aplicarlo.", TAG, api.off0))
    end
  end

  local mask = pad_mask()
  if mask == nil then mask = -1 end          -- -1 = el emulador no da el pad

  -- Replay: solo cuando cambia la mascara (mismo formato que el motor).
  if mask >= 0 and out_rep and mask ~= pad_prev then
    out_rep:write(string.format("%d %04X\n", frame, mask))
    pad_prev = mask
    bump("rep_lin")
  end

  local pin = ""
  if type(poll_mask) == "number" then pin = string.format("%04X", poll_mask) end
  local pin_n = poll_mask
  if pin_n == nil then pin_n = mask end

  if out_tsv then
    out_tsv:write(string.format(
      "%d\t%04X\t%s\t%s\t%d\t%d\t%06X\t%02X\t%02X\t%02X\t%02X\t%04X\t%02X\t%02X\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%06X\t%02X\t%02X\t%02X\t%02X\t%02X\t%d\t%d\t%s\n",
      frame,
      mask >= 0 and mask or 0, pin, btn_str(mask >= 0 and mask or 0),
      nz(mc, 0), nz(cyc, 0), pc24,
      nz(g(cpu, "a", "A"), 0), nz(g(cpu, "x", "X"), 0), nz(g(cpu, "y", "Y"), 0),
      nz(g(cpu, "sp", "SP"), 0), nz(g(cpu, "d", "D"), 0),
      nz(g(cpu, "db", "DB"), 0), nz(g(cpu, "status", "p", "PS"), 0),
      nz(g(ppu, "screenBrightness"), 0), nz(g(ppu, "bgMode"), 0),
      nz(g(ppu, "scanline"), 0), nz(g(ppu, "frameCount"), 0),
      nz(cnt["hc"], 0), nz(cnt["r2140"], 0), nz(cnt["w2140"], 0), nz(cnt["spcw"], 0),
      fmt_ini(), kon_total, kon_frame,
      nz(g(spc, "pc", "PC"), 0), nz(g(spc, "a", "A"), 0), nz(g(spc, "x", "X"), 0),      nz(g(spc, "y", "Y"), 0), nz(g(spc, "sp", "SP"), 0), nz(g(spc, "status", "ps", "PS"), 0),
      nz(cnt["r4212"], 0), ev_nmi, fmt_w4200()))
  end

  if frame % LOG_EVERY == 0 then
    -- Autocomprobacion: los frames del script deben seguir a los del PPU.  Si
    -- se separan, el enum de eventos o el contador no son lo que creemos, y
    -- toda la traza seria dudosa.
    local ppufr = nz(g(ppu, "frameCount"), -1)
    local off0 = nz(api.off0, 0)
    local aviso = ""
    local desfase = ppufr - off0 - frame
    if ppufr >= 0 and math.abs(desfase) > 2 then
      aviso = string.format("  << DESALINEADO: ppufr=%d, desfase=%d (esperado %d)",
        ppufr, desfase, off0)
    end
    -- Los dos sensores del SPC: spcw (variante de DATOS) y alt_spcw (variante de
    -- diagnostico).  Si el primero esta muerto y el segundo vivo, hay que
    -- cambiar SPC_SIN_MEMTYPE: se avisa aqui en vez de dar datos falsos.
    if frame > 300 and nz(cnt["spcw"], 0) == 0 and nz(cnt["alt_spcw"], 0) > 0 then
      aviso = aviso .. " << HOOKS SPC MUERTOS: los datos del SPC no valen;" ..
        " pon SPC_SIN_MEMTYPE=true y vuelve a grabar"
    end
    log(string.format(
      "%s fr=%d pin=%s in=%04X pc=%06X bright=%02X hc=%d r2140=%d spcw=%d/%d " ..
      "kon=%d(+%d) ini=%s dsp_w=%d/%d rep_lin=%d%s",
      TAG, frame, string.format("%04X", pin_n or 0), mask >= 0 and mask or 0, pc24,
      nz(g(ppu, "screenBrightness"), 0), nz(cnt["hc"], 0), nz(cnt["r2140"], 0),
      nz(cnt["spcw"], 0), nz(cnt["alt_spcw"], 0), kon_total, kon_frame,
      fmt_ini(), nz(cnt["dspw"], 0), nz(cnt["alt_dspw"], 0),
      nz(cnt["rep_lin"], 0), aviso))
  end

  reset_frame_counters()

  if END_FRAME > 0 and frame >= END_FRAME then
    log(string.format("%s FIN fr=%d", TAG, frame))
    terminar()
  end
end

-- --------------------------------------------------------------------------
-- Sondas de memoria
-- --------------------------------------------------------------------------
local function registrar()
  local n = 0

  -- $2100 (INIDISP): valor exacto escrito, via callback de escritura.
  n = n + (add_mem_cb(function(_, v)
    if #ini_vals < 32 then ini_vals[#ini_vals + 1] = v end
    evento("w2100", 0x2100, v, "cpu", "")
  end, CB_WRITE, 0x002100, 0x002100, CT_CPU) and 1 or 0)

  -- $4200 (NMITIMEN).
  n = n + (add_mem_cb(function(_, v)
    if #w4200_vals < 16 then w4200_vals[#w4200_vals + 1] = v end
    evento("w4200", 0x4200, v, "cpu", "")
  end, CB_WRITE, 0x004200, 0x004200, CT_CPU) and 1 or 0)

  -- Puertos del APU vistos por la CPU.
  n = n + (add_mem_cb(function(addr, v)
    bump("w2140")
    evento("w214x", addr, v, "cpu", "")
  end, CB_WRITE, APU_LO, APU_HI, CT_CPU) and 1 or 0)
  n = n + (add_mem_cb(function(addr, v)
    bump("r2140")
    if LOG_READS then evento("r214x", addr, v, "cpu", "") end
  end, CB_READ, APU_LO, APU_HI, CT_CPU) and 1 or 0)

  -- $4212 (espera de vblank).
  n = n + (add_mem_cb(function() bump("r4212") end, CB_READ, 0x004212, 0x004212, CT_CPU) and 1 or 0)

  -- Bucle caliente del handshake con el IPL.
  n = n + (add_mem_cb(function() bump("hc") end, CB_EXEC, HOT_LO, HOT_HI, CT_CPU) and 1 or 0)

  -- Sombras de WRAM.
  for _, s in ipairs(SHADOW) do
    local nombre = s[3]
    n = n + (add_mem_cb(function(addr, v)
      evento("wshadow", addr, v, "cpu", nombre)
    end, CB_WRITE, s[1], s[2], CT_CPU) and 1 or 0)
  end

  -- Lado del SPC.  Dos cosas que no pueden fallar en silencio:
  --   * si la API no expone cpuType.spc, NO se adivina el numero (un valor
  --     equivocado engancharia otra memoria y daria datos falsos);
  --   * los hooks llevan cpuType EXPLICITO: la forma sin cpuType los pondria en
  --     el bus de la CPU, y $00F2/$00F3 en banco 0 son WRAM, no el DSP.
  -- Se registran DOS variantes sobre los mismos rangos: la de DATOS (memType
  -- explicito, salvo SPC_SIN_MEMTYPE) y una de DIAGNOSTICO que solo cuenta
  -- (alt_*).  Si la de datos esta muerta y la otra viva, el log lo dice.
  if CT_SPC ~= nil then
    local mem = SPC_SIN_MEMTYPE and false or MT_SPC

    n = n + (add_mem_cb(function(addr, v)
      bump("spcw")
      evento("w214x", 0x2140 + (addr - SPC_APU_LO), v, "spc", "spc")
    end, CB_WRITE, SPC_APU_LO, SPC_APU_HI, CT_SPC, mem, true) and 1 or 0)

    n = n + (add_mem_cb(function(_, v)
      dsp_addr = v
      evento("sdsp_addr", DSP_ADDR, v, "spc", "")
    end, CB_WRITE, DSP_ADDR, DSP_ADDR, CT_SPC, mem, true) and 1 or 0)

    n = n + (add_mem_cb(function(_, v)
      bump("dspw")
      local reg = dsp_addr % 256
      if reg == DSP_KON then
        kon_total = kon_total + 1
        kon_frame = kon_frame + 1
        evento("keyon", 0x00F3, v, "spc", string.format("reg=%02X", reg))
      else
        evento("sdsp_data", 0x00F3, v, "spc", string.format("reg=%02X", reg))
      end
    end, CB_WRITE, DSP_DATA, DSP_DATA, CT_SPC, mem, true) and 1 or 0)

    add_mem_cb(function() bump("alt_spcw") end, CB_WRITE, SPC_APU_LO, SPC_APU_HI,
               CT_SPC, false, true)
    add_mem_cb(function() bump("alt_dspw") end, CB_WRITE, DSP_DATA, DSP_DATA,
               CT_SPC, false, true)
  else
    api.sin_spc = true
    log(TAG .. " AVISO: esta build no expone emu.cpuType.spc: sin key-on ni" ..
      " puertos del SPC (el resto de la traza es valido)")
  end

  return n
end

-- --------------------------------------------------------------------------
-- Arranque y cierre
-- --------------------------------------------------------------------------
function terminar()
  if out_tsv then out_tsv:flush(); out_tsv:close(); out_tsv = nil end
  if out_ev then out_ev:flush(); out_ev:close(); out_ev = nil end
  if out_rep then out_rep:flush(); out_rep:close(); out_rep = nil end
  if out_status then
    out_status:write(string.format("=== fin: fr=%d kon=%d ===\n", frame, kon_total))
    out_status:flush(); out_status:close(); out_status = nil
  end
  -- emu.stop() CIERRA el emulador: solo si se ha pedido explicitamente.
  if PARAR_AL_TERMINAR then pcall(emu.stop, 0) end
end

local function sonda_api()
  api.emu             = tostring(emu ~= nil)
  api.getInput        = tostring(emu ~= nil and emu.getInput ~= nil)
  api.getState        = tostring(emu ~= nil and emu.getState ~= nil)
  api.getCpuState     = tostring(emu ~= nil and emu.getCpuState ~= nil)
  api.getMasterClock  = tostring(emu ~= nil and emu.getMasterClock ~= nil)
  api.addEventCallback   = tostring(emu ~= nil and emu.addEventCallback ~= nil)
  api.addMemoryCallback  = tostring(emu ~= nil and emu.addMemoryCallback ~= nil)
  api.cpuType_spc_exists = tostring(emu ~= nil and emu.cpuType ~= nil and emu.cpuType.spc ~= nil)
  api.CT_SPC = tostring(CT_SPC)
  api.CB = string.format("read=%s write=%s exec=%s", CB_READ, CB_WRITE, CB_EXEC)
  api.MT_CPU = tostring(MT_CPU)
end

local function main()
  -- getInput: se prueba que forma acepta esta build.
  local t1 = try(emu.getInput, 0)
  if type(t1) == "table" then getinput_form = 1
  else
    local t2 = try(emu.getInput, 0, 0)
    if type(t2) == "table" then getinput_form = 2 end
  end

  local ok_sal = abrir_salidas()
  sonda_api()

  local ri = try(emu.getRomInfo)
  local sha = (type(ri) == "table" and (ri.fileSha1Hash or "?")) or "?"
  local romname = (type(ri) == "table" and ri.name) or "?"

  if out_tsv then
    out_tsv:write(CABECERA_TXT)
    out_tsv:write("# ROM: " .. tostring(romname) .. "  sha1=" .. tostring(sha) .. "\n")
    out_tsv:write("# API: " .. table.concat({ "getInput=" .. api.getInput,
      "getState=" .. api.getState, "getCpuState=" .. api.getCpuState,
      "cpuType.spc=" .. api.cpuType_spc_exists, "cb=" .. api.CB,
      "form_getInput=" .. tostring(getinput_form) }, " ") .. "\n")
    out_tsv:write("#\n")
    out_tsv:write("#" .. table.concat(COLUMNAS, "\t") .. "\n")
  end
  if out_ev then
    out_ev:write("# eventos: fr\tmaster\tsrc\tkind\taddr\tval\tnota\n")
  end
  if out_rep then
    out_rep:write("# replay para el motor recomp: '<frame> <mascara hex>' (orden $4218)\n")
    out_rep:write("# ROM sha1=" .. tostring(sha) .. "\n")
  end

  if not ok_sal then
    pcall(emu.log, TAG .. ": NO se pudo abrir ningun fichero de salida")
    return
  end

  local nhooks = registrar()

  -- Eventos.  Solo se registran los que existen de verdad en esta build.
  local ev_reg = {}
  local function reg_evento(nombre, fn, tipo)
    if not tipo then ev_reg[#ev_reg + 1] = nombre .. "=NO-EXISTE"; return false end
    local ok = pcall(emu.addEventCallback, fn, tipo)
    ev_reg[#ev_reg + 1] = string.format("%s=%s(%d)", nombre, tostring(ok), tipo)
    return ok
  end
  local ok_ef = reg_evento("endFrame", on_end_frame, EV_ENDFRAME)
  reg_evento("reset", on_reset, EV_RESET)
  reg_evento("nmi", on_nmi, EV_NMI)
  reg_evento("irq", on_irq, EV_IRQ)
  poll_hook_ok = reg_evento("inputPolled", on_input_polled, EV_INPUTPOLLED)
  if not ok_ef then
    log(TAG .. " ERROR: no he podido registrar endFrame; sin eso no hay traza")
    return
  end
  log(TAG .. " eventos: " .. table.concat(ev_reg, " "))  log(string.format("%s LISTO: out=%s hooks_mem=%d formas=%s getInput=%s spc_hooks=%s",
    TAG, tostring(path_tsv), nhooks,
    table.concat({ tostring(forms_ok[1] or "-"), tostring(forms_ok[2] or "-"),
                   tostring(forms_ok[3] or "-") }, "/"),
    tostring(getinput_form), CT_SPC ~= nil and "si" or "NO"))
  log(string.format("%s API: %s | masterClockFn=%s | poll=%s",
    TAG, api.CB, api.getMasterClock, tostring(poll_hook_ok)))
  log(string.format("%s ficheros: %s | %s | %s | %s", TAG,
    tostring(path_tsv), tostring(path_ev), tostring(path_rep), tostring(path_status)))

  -- Cierre limpio si el usuario para el script.
  if EV_SCRIPTENDED then
    pcall(emu.addEventCallback, function()
      if out_tsv or out_ev or out_rep then
        log(string.format("%s cierre (script detenido) fr=%d kon=%d", TAG, frame, kon_total))
        terminar()
      end
    end, EV_SCRIPTENDED)
  end
end

main()
