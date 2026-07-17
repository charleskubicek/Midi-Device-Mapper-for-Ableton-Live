-- ====================================================================
-- MUST be on the SYSTEM element (index 255), Setup event, in a Code Block.
-- Only the system element receives host SysEx; on a normal pot/button the
-- sysexrx_cb assignment is silently ignored.
--
-- If the callback never fires (LEDs never change) even though a MIDI monitor
-- shows F0 7D 4C 01 ... F7 reaching the Grid: UPDATE Grid firmware AND Grid
-- Editor to the latest. Outdated firmware not firing sysexrx_cb is a known,
-- documented cause (Intech forum: "Receive Sysex from Bitwig...").
--
-- Canonical signature per Intech is `function(self, sysex)` with sysex as a
-- hex STRING; we take (self, a, b) and sniff the string arg to be firmware-
-- version-proof.
-- ====================================================================

-- TEMP boot smoke-test (Test A): lights local elements green at boot, proves
-- glc works. Delete once the LEDs follow the device.
for e = 0, 15 do glc(e, 1, 0, 255, 0) end

local LAYER = 1

local function to_bytes(payload)
  if payload == nil then return {} end
  if type(payload) == "table" then
    return payload
  end
  local bytes = {}
  for hx in string.gmatch(tostring(payload), "%x%x") do
    bytes[#bytes + 1] = tonumber(hx, 16)
  end
  return bytes
end

self.sysexrx_cb = function(self, a, b)
  -- The callback gets a short header arg and the full SysEx frame in the OTHER
  -- arg, and the order varies by firmware. The real frame (149 bytes) is far
  -- longer than any header, so decode both and take whichever is longer.
  local ba, bb = to_bytes(a), to_bytes(b)
  local bytes = (#bb > #ba) and bb or ba

  -- DEBUG probe: shows both arg lengths in the Grid Editor console. The real
  -- frame is len 149; the other is the short header. Remove once working.
  print("[gridled] fired a=" .. #ba .. " b=" .. #bb)

  if #bytes < 5 then return end
  if bytes[2] ~= 0x7D or bytes[3] ~= 0x4C or bytes[4] ~= 0x01 then return end

  local base = 4
  for slot = 0, 47 do
    local i = base + slot * 3
    if i + 3 > #bytes then break end
    local r = bytes[i + 1] * 2
    local g = bytes[i + 2] * 2
    local b = bytes[i + 3] * 2

    local elem = SLOT_TO_ELEMENT(slot)
    if elem ~= nil then
      glc(elem, LAYER, r, g, b)
    end
  end
end

function SLOT_TO_ELEMENT(slot)
  if slot >= 0 and slot <= 15 then
    return slot
  end
  return nil
end
