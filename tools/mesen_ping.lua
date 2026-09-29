-- mesen_ping.lua - prueba minima de que la ventana de script de MesenCE ejecuta
-- de verdad y puede escribir a disco.
--
-- Para que: cuando el probe grande (mesen_intro_probe.lua) no deja ninguna
-- huella, no se sabe si (a) el script no se ejecuto, (b) se ejecuto y no pudo
-- escribir, o (c) tiene un error de sintaxis/API.  Este fichero distingue los
-- tres casos en 20 segundos:
--   * no aparece ninguna linea en la ventana de script -> el script no se lanzo
--     (o el fichero tiene un error de sintaxis, que Mesen si reporta ahi);
--   * aparece "ping: ..." pero no se crea el .log -> el script corre y el
--     problema es de escritura/permisos en las rutas;
--   * aparece el .log con las lineas "ping frame N" -> todo correcto y el probe
--     grande funcionara igual.
--
-- Uso: MesenCE -> Depurar -> Ventana de script -> Abrir script -> este fichero ->
-- Ejecutar (F5).  Luego cargar/reiniciar el ROM.

local CAND = {
  "F:\\Recompilador Super Nintendo\\Mesen\\mesen_ping.log",
  "F:\\SOR\\mesen_ping.log",
}

local path = nil
for _, p in ipairs(CAND) do
  local f = io.open(p, "a")
  if f then f:close(); path = p; break end
end

local function w(msg)
  msg = tostring(msg)
  if emu ~= nil and emu.log ~= nil then pcall(emu.log, msg) end
  if path == nil then return end
  local f = io.open(path, "a")
  if f then f:write(os.date("%H:%M:%S") .. " " .. msg .. "\n"); f:close() end
end

w("ping: el script se esta ejecutando (rutas probadas, escritura=" ..
  tostring(path ~= nil) .. ")  api: emu=" .. tostring(emu ~= nil) ..
  " addEventCallback=" .. tostring(emu ~= nil and emu.addEventCallback ~= nil) ..
  " addMemoryCallback=" .. tostring(emu ~= nil and emu.addMemoryCallback ~= nil))

local n = 0
if emu ~= nil and emu.addEventCallback ~= nil then
  local ok = pcall(emu.addEventCallback, function()
    n = n + 1
    if n % 60 == 0 then w("ping frame " .. n) end
  end, (emu.eventType ~= nil and emu.eventType.endFrame) or 3)
  w("ping: callback de fin de frame registrado=" .. tostring(ok))
else
  w("ping ERROR: emu.addEventCallback no existe en esta build de Mesen")
end
