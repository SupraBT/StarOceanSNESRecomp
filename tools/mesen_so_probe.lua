-- mesen_so_probe.lua - Star Ocean (Japan) - SONDA COMPACTA DE REFERENCIA
-- ============================================================================
-- Que es y por que existe
-- ----------------------
-- `mesen_so_trace.lua` graba TODO: una linea por cada acceso. Para la intro
-- eso son 1,45 M de lineas y 56 MB, de los que el 95% es lo mismo repetido
-- (702.846 escrituras a $2140, una a una). Es imposible mirarlo y encima no
-- alcanza: faltaban las cosas que de verdad hacen falta para depurar.
--
-- Este script graba el RESUMEN, no la transcripcion. La idea es una sola:
--
--   Un flujo de alta densidad (las escrituras a $2140, las del SPC al DSP) se
--   resume POR FOTOGRAMA con dos numeros: cuantas y un DIGEST del contenido.
--   El digest no deja ver QUE bytes fueron, pero si deja PROBAR que dos
--   corridas son identicas byte a byte, que es la pregunta que se hace el 90%
--   de las veces al comparar hardware contra el motor. Y ocupa 30 bytes en
--   vez de 3.000.
--
--   Lo que si cambia de verdad (un fundido, un key-on, un reset) se escribe
--   como evento, pero solo cuando cambia: sin repeticiones.
--
--   Y se anade lo que faltaba y mas hizo falta: el estado del SPC700 fotograma
--   a fotograma, los contadores del timer, y una huella del WRAM para
--   localizar el PRIMER fotograma exacto en que el motor se separa de
--   hardware.
--
-- Tamano esperado: ~1 MB para 2.000 fotogramas (frente a 56 MB de antes), con
-- TODA la informacion que de verdad se consulta.
--
-- COMO SE USA (MesenCE / Mesen-S)
--   1. Depurar -> Ventana de script -> Abrir script -> este fichero -> Ejecutar.
--   2. Reiniciar el ROM DESDE EL ARRANQUE (nada de estados guardados).
--   3. Jugar. El script escribe su progreso en la ventana de script.
--   4. Para el script al llegar a END_FRAME, o antes a mano.
--
-- ENTRADAS EN ESTE SCRIPT (bloque de configuracion de mas abajo)
--   END_FRAME      fotogramas a grabar; 0 = sin limite. Ponlo siempre: una
--                  sesion larga sin tope produce ficheros que no se abren.
--   RANGOS         zonas de codigo cuyo recuento por fotograma se guarda. Es lo
--                  que dice "donde se fue el tiempo" y lo que hoy faltaba para
--                  el IPL del SPC700.
--   VERBOSE_DESDE / VERBOSE_HASTA
--                  ventana en la que los flujos de $2140 y del SPC al DSP se
--                  escriben byte a byte en vez de resumirse. Fuera de la
--                  ventana solo queda el digest.
--   HUELLAS        cada N fotogramas, empreinte del WRAM/RAM del SPC/BRAM del
--   R2140_DESDE / R2140_HASTA / R2140_MAX
--                  ventana en la que se graba UNA LINEA POR LECTURA de
--                  $2140-$2143 en <salida>_r2140.tsv, con el valor devuelto y
--                  el PC que la hace. Es el oraculo del handshake de
--                  $C0:859E (LDA $2140 / CMP $2140 / BNE): en hardware el
--                  bucle corre 0 veces, aqui no converge nunca, y sin el valor
--                  de lectura no se puede saber cual es la semantica correcta.
--                   DSP. Es lo que marca el primer fotograma de divergencia.
--
-- LO QUE ESTE SCRIPT NO PUEDE HACER (y por que no lo disimula)
--   * Los callbacks de ESCRITURA no siempre disparan en todas las builds. La
--     sonda anterior perdia el 98% de las escrituras a $2100 por eso. Aqui se
--     comprueba con un CANARIO (una pagina de pila que recibe escrituras
--     miles de veces por fotograma) y si el canario da 0, el log lo avisa y
--     las columnas afectadas se marcan como no creibles.
--   * Las escrituras del SPC llevan SIEMPRE cpuType explicito: sin el, el
--     hook cae en el bus de la CPU, donde $00F2/$00F3 son WRAM y no el DSP, y
--     salen key-on falsos.
--   * Si la build no expone emu.cpuType.spc no se adivina el numero: se
--     avisa y se sigue sin las columnas del SPC, que es lo correcto.
-- ============================================================================

local TAG = "so_probe"

-- ============================================================================
-- Configuracion
-- ============================================================================
local START_FRAME = 1
local END_FRAME   = 2000        -- 0 = sin limite (no recomendado)
local LOG_EVERY   = 100
local VERBOSE_DESDE = 1         -- ventana con detalle byte a byte
local VERBOSE_HASTA = 200
local HUELLAS_CADA = 20         -- huella cada N fotogramas; 0 = desactivar
local DIR_SALIDA  = nil         -- nil = carpeta del ROM / candidatos
-- ORACULO DEL HANDSHAKE DE $2140.
-- El invitado en $C0:859E hace LDA $2140 / CMP $2140 / BNE $859D: exige que
-- DOS lecturas seguidas, sin escritura en medio, devuelvan el MISMO byte. En
-- hardware ese bucle se ejecuta 0 veces (columna ipl de _frames.tsv), o sea
-- que las dos lecturas coinciden a la primera. En el motor no convergen nunca.
-- Aqui se graba CADA lectura con su valor y con el PC de quien la hace, que es
-- lo unico que permite emparejar $C0859E con $C085A2 y ver que devuelve el
-- hardware de verdad en cada una.
-- CONTENIDO INTEGRO del WRAM bajo ($0000-$00FF), fotograma a fotograma.
-- Es el instrumento mas barato y mas informativo para responder a la pregunta
-- que de verdad importa: en que fotograma exacto el motor se separa de
-- hardware. Un digest no sirve para eso (solo diria SI y CUANDO); 256 bytes
-- en hexadecimal si. El handshake de $2140 lee $4A de ahi, asi que cuando el
-- motor no pone $4A a $80 se vera aqui el primer fotograma en que esa pagina
-- deja de coincidir con hardware.
local WRAM0_DESDE = 1
local WRAM0_HASTA = 200

local R2140_DESDE = 1         -- ventana de captura
local R2140_HASTA = 1200
local R2140_MAX   = 400000     -- tope de lineas; en hardware no se llega
local PARAR = false             -- true = emu.stop() al terminar (CIERRA Mesen)

-- Ficheros. Se declaran ANTES de log(), que los usa: en Lua un local
-- declarado despues no existe para las funciones de arriba, y el
-- `if f_status` se comeria un global nil en silencio.
local f_frames, f_audio, f_events, f_replay, f_fp, f_status, f_r2140, f_wram0 = nil, nil, nil, nil, nil, nil, nil, nil
local base = nil

-- Zonas de codigo vigiladas. El recuento por fotograma de cuantas veces se
-- ejecuta cada una dice donde se va el tiempo y, sobre todo, EN QUE ZONA SE
-- QUEDA EL INVITADO, que es la pregunta que no tenia respuesta buena.
local RANGOS = {
  { 0xC0859D, 0xC085D0, "ipl"    },  -- spin del handshake con el IPL
  { 0xC084AE, 0xC084B4, "d9"     },  -- espera del latch $D9 (batalla)
  { 0xC00221, 0xC00260, "virq"   },  -- handler de V-IRQ
  { 0xC0032D, 0xC0032D, "sndtick"},  -- tick por fotograma del driver de sonido
  { 0xC08751, 0xC08751, "r8751"  },
  { 0xC08F94, 0xC08F94, "r8f94"  },
  { 0x00F400, 0x00F43F, "sndram" },  -- estado del motor de sonido en WRAM
}

-- Registros sueltos que interesa ver cambiar, no contar.
local REGISTROS = {
  { 0x002100, "2100" },   -- INIDISP (fundidos y logos)
  { 0x004200, "4200" },   -- NMITIMEN
  { 0x004212, "4212" },   -- HVBJOY
}

local APU_LO, APU_HI = 0x002140, 0x002143      -- puertos del CPU
local SPC_LO, SPC_HI = 0x0000F4, 0x0000F7      -- los mismos desde el SPC
local DSP_ADDR, DSP_DATA = 0x0000F2, 0x0000F3
local DSP_KON = 0x4C                          -- registro de key-on

local CANDIDATOS = {
  "F:\\Recompilador Super Nintendo\\Mesen\\",
  "F:\\SOR\\",
}

-- ============================================================================
-- API: takenos de la sonda anterior, que ya estan VERIFICADOS en esta
-- maquina. No se supone nada: cada enum se lee del runtime si existe y solo se
-- recurre al valor documentado como respaldo.
-- ============================================================================
local function enum_or(tbl, key, fallback)
  if tbl ~= nil and tbl[key] ~= nil then return tbl[key] end
  return fallback
end

local CB_TBL = (emu and (emu.callbackType or emu.memCallbackType)) or nil
local CB_READ  = enum_or(CB_TBL, "read",  0)
local CB_WRITE = enum_or(CB_TBL, "write", 1)
local CB_EXEC  = enum_or(CB_TBL, "exec",  2)

local CT_CPU = enum_or(emu and emu.cpuType, "snes",
                       enum_or(emu and emu.cpuType, "cpu", 0))
local CT_SPC = enum_or(emu and emu.cpuType, "spc", nil)

local MT_CPU = enum_or(emu and emu.memType, "snesMemory",
                       enum_or(emu and emu.memType, "cpu", 0))
local MT_SPC = enum_or(emu and emu.memType, "spcMemory",
                       enum_or(emu and emu.memType, "spc", 1))

local function ev(name, fallback)
  local t = emu and emu.eventType
  if t ~= nil and t[name] ~= nil then return t[name] end
  return fallback
end
local EV_ENDFRAME    = ev("endFrame", 3)
local EV_NMI         = ev("nmi", 0)
local EV_IRQ         = ev("irq", 1)
local EV_RESET       = ev("reset", 4)
local EV_INPUTPOLLED = ev("inputPolled", 6)

-- ============================================================================
-- Utilidades
-- ============================================================================
local MOD = 4294967296

-- Digest de un flujo de bytes. Multiplicador 65599 y no el 16777619 del FNV-1a
-- a proposito: asi el producto cabe en las 53 bits de un double de Lua y no se
-- pierde precision, que es justo lo que pasaria con el FNV canonico aqui.
-- No es criptografico: solo tiene que responder "igual o distinto".
local function d_reset() return 2166136261 % MOD end

local function d_byte(h, b)
  return (h * 65599 + (b % 256)) % MOD
end

local function d_addr_val(h, a, v)
  return d_byte(d_byte(d_byte(h, a % 256), (a // 256) % 256), v)
end

-- Un valor negativo es "el campo no existe en esta build", no un numero. Si se
-- imprimiera como hex, -1 saldria "F...F" y seria indistinguible de un valor
-- real, que es justo el tipo de dato creible y falso que no se quiere.
local function hex(v, n)
  if v == nil then return "-" end
  if type(v) ~= "number" then return "-" end
  if v < 0 then return "-" end
  return string.format("%0" .. n .. "X", v % (16 ^ n))
end

local function try(fn, ...)
  local ok, r = pcall(fn, ...)
  if ok then return r end
  return nil
end

local function log(msg)
  msg = tostring(msg)
  if emu and emu.log then pcall(emu.log, TAG .. ": " .. msg) end
  if f_status then f_status:write(string.format("%s %s\n", os.date("%H:%M:%S"), msg)) end
end

local function g(t, ...)
  if type(t) ~= "table" then return nil end
  for _, k in ipairs({ ... }) do
    if t[k] ~= nil then return t[k] end
  end
  return nil
end

local function nz(v, d) if v == nil then return d or 0 end return v end

local function dump_keys(t)
  if type(t) ~= "table" then return "-" end
  local b = {}
  for k in pairs(t) do b[#b + 1] = tostring(k) end
  table.sort(b)
  return table.concat(b, ",")
end

-- ============================================================================
-- Ficheros
-- ============================================================================
local function abrir()
  local lista = {}
  if DIR_SALIDA then lista = { DIR_SALIDA .. "/" .. TAG } else
    for _, d in ipairs(CANDIDATOS) do lista[#lista + 1] = d .. TAG end
    lista[#lista + 1] = TAG .. "_probe"
  end
  for _, dir in ipairs(lista) do
    local ok = pcall(function()
      f_frames = assert(io.open(dir .. "_frames.tsv", "w"))
      f_audio  = assert(io.open(dir .. "_audio.tsv", "w"))
      f_events = assert(io.open(dir .. "_events.tsv", "w"))
      f_replay = assert(io.open(dir .. "_replay.txt", "w"))
      f_fp     = assert(io.open(dir .. "_fp.tsv", "w"))
      f_r2140  = assert(io.open(dir .. "_r2140.tsv", "w"))
      f_wram0 = assert(io.open(dir .. "_wram0.tsv", "w"))
    end)
    if ok and f_frames then base = dir; break end
f_frames, f_audio, f_events, f_replay, f_fp, f_r2140, f_wram0 = nil, nil, nil, nil, nil, nil, nil
  end
  if not base then
    log("ERROR: no he podido escribir en ninguna ruta")
    return false
  end
  f_status = io.open(base .. "_status.log", "a")
  log("salida = " .. base)

  f_frames:write("# " .. TAG .. " frames: una fila por fotograma.\n")
  f_frames:write(string.format("# fotogramas %d..%d, verbose %d..%d\n",
            START_FRAME, END_FRAME, VERBOSE_DESDE, VERBOSE_HASTA))
  f_frames:write("fr\tmaster\tcyc\tpc\ta\tx\tsp\td\tdb\tp\tbright\tbgmode\tscan" ..
                 "\tpad\tpoll\tnmi\tirq\tini\tr2140\tr4212\tw4200")
  for _, r in ipairs(RANGOS) do f_frames:write("\t" .. r[3]) end
  f_frames:write("\tcanario\n")

  f_audio:write("# " .. TAG .. " audio: la cadena de sonido fotograma a fotograma.\n")
  f_audio:write("fr\tmaster\tcpu_w2140\tspc_w214x\tdsp_adr\tdsp_dat\tkeyon" ..
                "\tptr_digest\tdsp_digest\tspcPC\tspcA\tspcX\tspcY\tspcSP" ..
                "\tt0\tt1\tt2\tring_avail\tspcRAM_fp\n")

  f_events:write("# " .. TAG .. " eventos: SOLO cambios. fr\tmaster\tsrc\tkind" ..
                 "\taddr\tval\tnote\n")

  f_r2140:write("# " .. TAG .. " lecturas de $2140-$2143, una linea por lectura, con el PC. fr	master	addr	val	pc	n\n")
  if f_r2140 then f_r2140:flush() end
  f_wram0:write("# " .. TAG .. " WRAM $0000-$00FF integro, un fotograma por fila. fr	master	wram0hex\n")
  if f_wram0 then f_wram0:flush() end

  f_fp:write("# " .. TAG .. " huellas para localizar el primer fotograma de " ..
             "divergencia. fr\tmaster\twram\tspcRam\tdspRam\n")
  return true
end

local function cerrar()
  for _, f in ipairs({ f_frames, f_audio, f_events, f_replay, f_fp, f_r2140, f_wram0 }) do
    if f then pcall(function() f:close() end) end
  end
  if f_status then pcall(function() f_status:close() end) end
  f_frames, f_audio, f_events, f_replay, f_fp, f_status, f_r2140, f_wram0 = nil, nil, nil, nil, nil, nil, nil, nil
end

-- ============================================================================
-- Estado del frame
-- ============================================================================
local frame = 0
local cnt = {}                       -- contadores del frame
local dig = {}                       -- digests del frame
local ini_vals, w4200_vals = {}, {}
local ev_nmi, ev_irq = 0, 0
local dsp_latch = 0
local canario = 0                    -- escrituras en la pagina de pila
local kon_total, kon_frame = 0, 0
local pad_prev = 0
local r2140_n    = 0          -- lineas escritas en _r2140.tsv
local r2140_tot  = 0          -- lecturas de $2140 en toda la corrida
local r2140_cero = 0          -- ... de las cuales salieron con valor 0
local r2140_pcs  = 0          -- PCs distintos seen: si sigue a 0, el hook
                              -- de lectura no entrega valor ni PC
local poll_mask = nil
local ultima = {}                    -- ultimo valor escrito por registro (transiciones)
local api = {}
local getinput_form = nil

local function reset_frame()
  cnt, dig = {}, {}
  ini_vals, w4200_vals = {}, {}
  ev_nmi, ev_irq = 0, 0
  kon_frame, canario = 0, 0
  poll_mask = nil
  for _, r in ipairs(RANGOS) do dig[r[3]] = d_reset() end
end

-- bump(nombre[, direccion, valor]): cuenta una ocurrencia y, si se le pasan
-- direccion y valor, mezcla ambos en el digest del flujo. Sin tabla intermedia:
-- esta funcion se llama cientos de miles de veces por corrida.
local function bump(n, addr, val)
  cnt[n] = (cnt[n] or 0) + 1
  if addr ~= nil then dig[n] = d_addr_val(dig[n] or d_reset(), addr, val or 0) end
end

-- PC de la CPU ahora mismo. Se llama DENTRO del callback de lectura, asi que
-- solo puede usar getters: leer memoria ahi reentraria en el propio hook.
local function pc_actual()
  local cs = try(emu.getCpuState, CT_CPU)
  if type(cs) == "table" then
    return nz(g(cs, "k", "K"), 0) * 65536 + nz(g(cs, "pc", "PC"), 0)
  end
  return 0
end

local function verbose()
  return VERBOSE_HASTA >= VERBOSE_DESDE and frame >= VERBOSE_DESDE and frame <= VERBOSE_HASTA
end

local function evento(kind, addr, val, src, note)
  if not f_events then return end
  local st = api.cache or {}
  f_events:write(string.format("%d\t%d\t%s\t%s\t%04X\t%02X\t%s\n",
    frame, st.masterClock or 0, src or "cpu", kind,
    addr or 0, (val or 0) % 256, note or ""))
end

-- Solo se escribe si el valor CAMBIA respecto al anterior. Un registro que se
-- reescribe 40 veces con el mismo valor ocupa una linea, no cuarenta.
local function transicion(nombre, addr, val, src)
  if ultima[nombre] == val then return end
  ultima[nombre] = val
  evento("set", addr, val, src, nombre)
end

-- ============================================================================
-- Callbacks de memoria (formas probadas en la sonda anterior)
-- ============================================================================
local forms_ok = {}

local function add_mem_cb(cb, ctype, s, e, cpu_type, mem_type, solo_explicita)
  cpu_type = cpu_type or CT_CPU
  if mem_type == false then mem_type = nil
  elseif mem_type == nil then mem_type = MT_CPU end
  local formas = {}
  if mem_type ~= nil then
    formas[#formas + 1] = function()
      return emu.addMemoryCallback(cb, ctype, s, e, cpu_type, mem_type) end
  end
  formas[#formas + 1] = function()
    return emu.addMemoryCallback(cb, ctype, s, e, cpu_type) end
  if not solo_explicita then
    formas[#formas + 1] = function()
      return emu.addMemoryCallback(cb, ctype, s, e) end
  end
  for i, f in ipairs(formas) do
    if pcall(f) then forms_ok[i] = (forms_ok[i] or 0) + 1; return i end
  end
  return nil
end

local function registrar()
  local n = 0

  -- CANARIO: la pagina de pila recibe escrituras miles de veces por fotograma.
  -- Si esto da 0, los callbacks de escritura no disparan y TODO lo que dependa
  -- de ellos es mentira. Es la unica defensa contra el fallo que hizo perder
  -- una sesion entera a la sonda anterior.
  n = n + (add_mem_cb(function() canario = canario + 1 end,
                      CB_WRITE, 0x000100, 0x0001FF, CT_CPU) and 1 or 0)

  -- Registros que interesan por TRANSICION.
  for _, r in ipairs(REGISTROS) do
    local nombre = r[2]
    n = n + (add_mem_cb(function(_, v)
      transicion(nombre, r[1], v, "cpu")
      if nombre == "2100" then ini_vals[#ini_vals + 1] = v
      elseif nombre == "4200" then w4200_vals[#w4200_vals + 1] = v end
    end, CB_WRITE, r[1], r[1], CT_CPU) and 1 or 0)
  end

  -- Puertos del APU vistos por la CPU: fuera de la ventana verbose solo cuenta
  -- y resume. Es el flujo mas voluminoso (700 mil escrituras en la traza vieja).
  n = n + (add_mem_cb(function(addr, v)
    bump("cpu_w2140", addr, v)
    if verbose() then evento("cpu_w2140", addr, v, "cpu", "") end
  end, CB_WRITE, APU_LO, APU_HI, CT_CPU) and 1 or 0)

  -- ORACULO DEL HANDSHAKE: una linea por LECTURA de $2140, con el valor que
  -- devuelve y el PC que la hace. Antes solo se contaba; ahora ademas se
  -- mezcla (direccion, valor) en el digest del fotograma, de modo que el
  -- flujo de lecturas se puede comparar hardware contra motor sin abrir el
  -- fichero, y en el fichero se ve una a una que es lo que hace falta para
  -- emparejar $C0859E con $C085A2.
  n = n + (add_mem_cb(function(addr, v)
    bump("r2140", addr, v)
    r2140_tot = r2140_tot + 1
    local val = tonumber(v) or 0
    if val == 0 then r2140_cero = r2140_cero + 1 end
    if f_r2140 and frame >= R2140_DESDE and frame <= R2140_HASTA and r2140_n < R2140_MAX then
      local pc = pc_actual()
      if pc ~= 0 then r2140_pcs = r2140_pcs + 1 end
      r2140_n = r2140_n + 1
      local mc = nz((api.cache or {}).masterClock, 0)
      if mc == 0 then mc = try(emu.getMasterClock) or 0 end
      f_r2140:write(string.format("%d	%d	%04X	%02X	%06X	%d\n",
                                frame, mc, addr or 0, val, pc, r2140_n))
    end
  end,
                      CB_READ, APU_LO, APU_HI, CT_CPU) and 1 or 0)
  n = n + (add_mem_cb(function() bump("r4212") end,
                      CB_READ, 0x004212, 0x004212, CT_CPU) and 1 or 0)

  -- Zonas de codigo vigiladas.
  for _, r in ipairs(RANGOS) do
    local nombre = r[3]
    n = n + (add_mem_cb(function() bump(nombre) end,
                        CB_EXEC, r[1], r[2], CT_CPU) and 1 or 0)
  end

  -- Lado del SPC. cpuType SIEMPRE explicito (ver cabecera).
  if CT_SPC ~= nil then
    n = n + (add_mem_cb(function(addr, v)
      bump("spc_w214x", addr, v)
      transicion("spc_p" .. (addr - SPC_LO), 0x2140 + (addr - SPC_LO), v, "spc")
    end, CB_WRITE, SPC_LO, SPC_HI, CT_SPC, MT_SPC, true) and 1 or 0)

    n = n + (add_mem_cb(function(_, v)
      dsp_latch = v
      bump("dsp_adr", DSP_ADDR, v)
      if verbose() then evento("dsp_adr", DSP_ADDR, v, "spc", "") end
    end, CB_WRITE, DSP_ADDR, DSP_ADDR, CT_SPC, MT_SPC, true) and 1 or 0)

    n = n + (add_mem_cb(function(_, v)
      -- Se digesta el REGISTRO del DSP (dsp_latch), no el puerto: asi el digest
      -- compara el efecto real sobre el DSP y no un puerto que siempre es $F3.
      bump("dsp_dat", dsp_latch, v)
      if dsp_latch == DSP_KON then
        kon_total, kon_frame = kon_total + 1, kon_frame + 1
        -- key-on SIEMPRE como evento: es la marca de que una nota empieza, y
        -- son pocas. Aqui el volumen no estorba.
        evento("keyon", DSP_DATA, v, "spc", string.format("reg=%02X", dsp_latch))
      elseif verbose() then
        evento("dsp_dat", DSP_DATA, v, "spc", string.format("reg=%02X", dsp_latch))
      end
    end, CB_WRITE, DSP_DATA, DSP_DATA, CT_SPC, MT_SPC, true) and 1 or 0)
  else
    log("AVISO: esta build no expone emu.cpuType.spc. Sin puertos del SPC, " ..
        "sin escrituras al DSP y sin key-on. El resto de la sonda es valido.")
  end

  log("hooks=" .. n .. " formas=" .. table.concat(
        (function() local b = {}
          for k, v in pairs(forms_ok) do b[#b + 1] = k .. "x" .. v end
          table.sort(b) return b end)(), ","))
  return n
end

-- ============================================================================
-- Huellas: el primer fotograma exacto de divergencia
-- ============================================================================
-- Una huella de 64 bits del estado completo. Si el motor y Mesen producen la
-- misma, el fotograma es identico bit a bit; en cuanto dejan de coincidir, el
-- numero de esa fila ES el primer fotograma de la divergencia. Es la forma
-- barata y exacta de saber donde se separan dos maquinas.
--
-- El orden de los argumentos de readMemory no esta verificado en esta maquina
-- (puede ser (cpuType, addr) o al reves), asi que se prueban los dos y se
-- recuerda el que funciona. Adivinarlo daria lecturas del bus equivocado y
-- huellas que no significan nada.
-- Leer memoria. OJO: en ESTA build emu.readMemory NO EXISTE (comprobado con un
-- script de humo el 2026-10-01: attempt to call a nil value). La sonda llevaba
-- tiempo intentando leer con el, y como fallo devolvia nil en silencio, la
-- huella de WRAM salia '-' y parecia un dato. Por eso ahora se usa emu.read,
-- que si existe, y se pasa el memType: snesWorkRam para el WRAM de la CPU y
-- spcRam para la RAM del SPC700.
local function leer_mem(mem_type, a)
  if mem_type == nil then return nil end
  local rd = emu.read
  if not rd then return nil end
  local ok, v = pcall(rd, a, mem_type)
  if ok and type(v) == "number" then return v end
  return nil
end

local MT_WRAM = emu.memType and emu.memType.snesWorkRam or nil
local MT_SPC_RAM = emu.memType and emu.memType.spcRam or nil


-- Los 256 bytes del WRAM bajo en hexadecimal. Sin digest: aqui se quiere ver
-- QUE byte se diferencia, no solo que se ha differed.
local function volcar_wram0()
  local t = {}
  for a = 0x0000, 0x00FF do
    local v = leer_mem(MT_WRAM, a)
    if v == nil then return nil end
    t[#t + 1] = string.format("%02X", v)
  end
  return table.concat(t)
end

local function huella_mem(desde, hasta)
  local h = d_reset()
  for a = desde, hasta do
    local v = leer_mem(MT_WRAM, a)
    if v == nil then return nil end
    h = d_byte(h, v)
  end
  return h
end

local function huella_spc()
  if CT_SPC == nil then return nil end
  local h = d_reset()
  for a = 0x0000, 0x00FF do
    local v = leer_mem(MT_SPC_RAM, a)
    if v == nil then return nil end
    h = d_byte(h, v)
  end
  return h
end

-- ============================================================================
-- Pad
-- ============================================================================
local function mask_de(t)
  if type(t) ~= "table" then return nil end
  local m = 0
  local b = {
    { "b", 0x0001 }, { "y", 0x0002 }, { "select", 0x0004 }, { "start", 0x0008 },
    { "up", 0x0010 }, { "down", 0x0020 }, { "left", 0x0040 }, { "right", 0x0080 },
    { "a", 0x0100 }, { "x", 0x0200 }, { "l", 0x0400 }, { "r", 0x0800 },
  }
  for _, k in ipairs(b) do if t[k[1]] then m = m + k[2] end end
  return m
end

local function leer_pad()
  if getinput_form == 1 then return mask_de(try(emu.getInput, 0)) end
  if getinput_form == 2 then return mask_de(try(emu.getInput, 0, 0)) end
  return nil
end

local function on_input_polled()
  if getinput_form == nil then
    getinput_form = (try(emu.getInput, 0) ~= nil) and 1
                   or ((try(emu.getInput, 0, 0) ~= nil) and 2 or 0)
    log("getInput forma=" .. tostring(getinput_form))
  end
  poll_mask = leer_pad()
end

-- ============================================================================
-- Fotograma
-- ============================================================================
local function estado()
  local st = try(emu.getState)
  if type(st) == "table" then
    api.cache = st
    if not api.claves then
      api.claves = true
      log("claves getState(): " .. dump_keys(st))
      log("  cpu=" .. dump_keys(st.cpu))
      log("  ppu=" .. dump_keys(st.ppu))
      log("  spc=" .. dump_keys(st.spc))
    end
    return st
  end
  api.cache = {}
  return {}
end

local function cpu_de(tipo, clave)
  if tipo ~= nil then
    local cs = try(emu.getCpuState, tipo)
    if type(cs) == "table" then return cs end
  end
  local st = api.cache or {}
  if type(st[clave]) == "table" then return st[clave] end
  return {}
end

local function on_end_frame()
  frame = frame + 1
  if frame < START_FRAME then reset_frame(); return end

  local st  = estado()
  local cpu = cpu_de(CT_CPU, "cpu")
  local ppu = (type(st.ppu) == "table") and st.ppu or {}
  local spc = (CT_SPC ~= nil) and cpu_de(CT_SPC, "spc")
              or ((type(st.spc) == "table") and st.spc or {})

  local mc  = try(emu.getMasterClock) or nz(st.masterClock, 0)
  local cyc = try(emu.getCpuCycleCount, CT_CPU) or nz(g(cpu, "cycleCount"), 0)
  local pc24 = nz(g(cpu, "k", "K"), 0) * 65536 + nz(g(cpu, "pc", "PC"), 0)

  -- Replay: solo cuando la mascara cambia, y en tiempo de INVITADO, que es lo
  -- unico que hace falta para reproducir (SNESRECOMP_REPLAY_FILE con
  -- clock: master). Es lo que permite alinear motor y hardware por reloj.
  local mask = leer_pad()
  if mask and mask ~= pad_prev then
    if f_replay then f_replay:write(string.format("%d\t%04X\n", mc, mask)) end
    pad_prev = mask
  end

  -- Fila de frames.
  local cols = {
    frame, mc, cyc, pc24,
    nz(g(cpu, "a", "A"), 0), nz(g(cpu, "x", "X"), 0), nz(g(cpu, "sp", "SP"), 0),
    nz(g(cpu, "d", "D"), 0), nz(g(cpu, "db", "DB"), 0), nz(g(cpu, "p", "P"), 0),
    nz(g(ppu, "screenBrightness"), 0), nz(g(ppu, "bgMode"), 0),
    nz(g(ppu, "scanline"), -1),
    mask or 0, poll_mask or -1, ev_nmi, ev_irq,
  }
  local ini = {}
  for i = 1, math.min(#ini_vals, 16) do ini[i] = hex(ini_vals[i], 2) end
  local w42 = {}
  for i = 1, math.min(#w4200_vals, 8) do w42[i] = hex(w4200_vals[i], 2) end
  cols[#cols + 1] = #ini_vals > 0 and table.concat(ini, "+") or "-"

  cols[#cols + 1] = nz(cnt["r2140"], 0)
  cols[#cols + 1] = nz(cnt["r4212"], 0)
  cols[#cols + 1] = #w4200_vals > 0 and table.concat(w42, "+") or "-"
  for _, r in ipairs(RANGOS) do cols[#cols + 1] = nz(cnt[r[3]], 0) end
  cols[#cols + 1] = canario

  local out = {}
  for i, v in ipairs(cols) do out[i] = tostring(v) end
  if f_frames then f_frames:write(table.concat(out, "\t") .. "\n") end

  -- La huella del SPC se calcula UNA vez por fotograma y se reutiliza en las dos
  -- filas: leerla dos veces son 512 lecturas de mas, y ya es lo mas caro que
  -- hace este script.
  local quiere_fp = (HUELLAS_CADA > 0) and (f_fp ~= nil) and
                   ((frame % HUELLAS_CADA) == 0)
  local spc_fp = quiere_fp and huella_spc() or nil

  -- Fila de audio.
  if f_audio then
    f_audio:write(string.format("%d\t%d\t%d\t%d\t%d\t%d\t%d\t%08X\t%08X\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",
      frame, mc,
      nz(cnt["cpu_w2140"], 0), nz(cnt["spc_w214x"], 0),
      nz(cnt["dsp_adr"], 0), nz(cnt["dsp_dat"], 0), kon_frame,
      dig["cpu_w2140"] or d_reset(), dig["dsp_dat"] or d_reset(),
      hex(g(spc, "pc", "PC"), 4), hex(g(spc, "a", "A"), 2),
      hex(g(spc, "x", "X"), 2), hex(g(spc, "y", "Y"), 2),
      hex(g(spc, "sp", "SP"), 2),
      nz(g(spc, "timer0", "t0"), -1), nz(g(spc, "timer1", "t1"), -1),
      nz(g(spc, "timer2", "t2"), -1),
      nz(g(spc, "ringAvailable", "available"), -1),
      hex(spc_fp, 8)))
  end

  -- Huellas. Son 8.192 lecturas por toma, asi que van espaciadas por
  -- HUELLAS_CADA: subirlas a 1 cuela el coste dentro de la emulacion y falsea
  -- las medidas de tiempo, que es justo lo que no hay que hacer.
  if quiere_fp then

    f_fp:write(string.format("%d\t%d\t%s\t%s\t-\n", frame, mc,
      hex(huella_mem(0x0000, 0x1FFF), 8), hex(spc_fp, 8)))
  end
  if f_fp then f_fp:flush() end

  -- Contenido integro del WRAM bajo. Solo en la ventana configurada: 256
  -- lecturas de memoria por fotograma se notan si se dejan fuera de ella.
  if f_wram0 and frame >= WRAM0_DESDE and frame <= WRAM0_HASTA then
    local w0 = volcar_wram0()
    if w0 then f_wram0:write(string.format("%d	%d	%s\n", frame, mc, w0)) end
  end
  -- flush a proposito: Lua bufferiza, y si Mesen se cierra a lo bruto (o se
  -- mata desde fuera) un fichero pequeno se queda en el bucle y sale de 0
  -- bytes. Ya ha pasado dos veces y parece un fallo de la sonda.
  if f_wram0 then f_wram0:flush() end

  if LOG_EVERY > 0 and (frame % LOG_EVERY) == 0 then
    log(string.format("fr=%d master=%d pc=%06X r2140=%d cpu_w2140=%d " ..
      "spc_w214x=%d dsp=%d/%d keyon=%d(+%d) canario=%d",
      frame, mc, pc24, nz(cnt["r2140"], 0), nz(cnt["cpu_w2140"], 0),
      nz(cnt["spc_w214x"], 0), nz(cnt["dsp_adr"], 0), nz(cnt["dsp_dat"], 0),
      kon_frame, kon_total, canario))
    if canario == 0 and frame > LOG_EVERY * 2 then
      log("AVISO: el canario de escritura da 0. Los callbacks de escritura NO " ..
          "disparan en esta build: las columnas de escrituras no son creibles.")
    end
  end

  reset_frame()

  if END_FRAME > 0 and frame >= END_FRAME then
    -- SALVEDAD del oraculo de $2140. Un hook de LECTURA puede no entregar el
    -- valor leido segun la build de Mesen; si fuera asi, el fichero seria una
    -- columna de ceros y pareceria un hallazgo. Se dice explicitamente.
    log(string.format("FIN fr=%d kon_total=%d | $2140: %d lecturas, %d lineas, " ..
                      "%d con valor 0, %d con PC != 0",
                      frame, kon_total, r2140_tot, r2140_n,
                      r2140_cero, r2140_pcs))
    if r2140_tot > 0 and r2140_cero == r2140_tot then
      log("AVISO: TODAS las lecturas de $2140 salieron 0. El callback de " ..
           "lectura de esta build seguramente NO entrega el valor: _r2140.tsv " ..
           "NO sirve como oraculo y hay que leer el puerto por otra via.")
    end
    if r2140_n >= R2140_MAX then
      log("AVISO: se ha tocado el tope de R2140_MAX (" .. R2140_MAX .. "); " ..
           "las ultimas lecturas no estan grabadas.")
    end
    cerrar()
    if PARAR then pcall(emu.stop) end
  end
end

local PARAR = false   -- false = no cerrar Mesen al terminar (uso normal)
-- ============================================================================
-- Arranque
-- ============================================================================
local function on_reset()
  if frame > 0 then
    log("AVISO: reset del invitado en fr=" .. frame ..
        ". A partir de aqui es otra sesion y el replay ya no es reproducible " ..
        "desde el arranque.")
  end
  evento("reset", 0, 0, "sys", "reset")
  frame, pad_prev, kon_total = 0, 0, 0
  ultima = {}
  reset_frame()
end

local function avisar_api()
  if emu.read == nil then log("AVISO: emu.read no existe en esta build") end
  if not MT_WRAM then log("AVISO: emu.memType.snesWorkRam no existe") end
end

local function arrancar()
  if not abrir() then return end
  f_replay:write("# replay para el motor recomp, en tiempo de INVITADO\n")
  f_replay:write("# <master> <mascara hex $4218>\n")

  avisar_api()
  registrar()

  if try(emu.addEventCallback, on_reset, EV_RESET) then
    log("reset: ok") else log("reset: NO registrado") end
  if try(emu.addEventCallback, function() ev_nmi = ev_nmi + 1 end, EV_NMI) then
    log("nmi: ok") else log("nmi: NO registrado") end
  if try(emu.addEventCallback, function() ev_irq = ev_irq + 1 end, EV_IRQ) then
    log("irq: ok") else log("irq: NO registrado") end
  if try(emu.addEventCallback, on_input_polled, EV_INPUTPOLLED) then
    log("inputPolled: ok") else log("inputPolled: NO registrado (el pad se " ..
    "lee al final del frame, una pulsacion puede quedar un fotograma tarde)") end
  if try(emu.addEventCallback, on_end_frame, EV_ENDFRAME) then
    log("endFrame: ok") else log("endFrame: NO registrado") end

  reset_frame()
  log(string.format("LISTO: fotogramas %d..%d, verbose %d..%d, huellas cada %d",
    START_FRAME, END_FRAME, VERBOSE_DESDE, VERBOSE_HASTA, HUELLAS_CADA))
end

arrancar()