// MappingDocument → NestedText. Emits the small NT subset the mapping schema
// needs: string scalars, dicts, and lists of dicts, 4-space indented. The
// contract is enforced by golden tests: everything emitted here must be
// accepted by the generator's read_root/build_validated_model (see
// tests/test_ui_golden.py on the Python side).

import { printCoordExpr } from './coords'
import type {
  MappingDocument,
  Mapping,
  Mode,
  RangeMap,
  DeviceTarget
} from './document'

type NtValue = string | NtDict | NtValue[]
interface NtDict {
  [key: string]: NtValue
}

const INDENT = '    '

export function emitNt(value: NtValue, depth = 0): string {
  if (typeof value === 'string') throw new Error('top-level scalar not supported')
  const pad = INDENT.repeat(depth)
  const lines: string[] = []
  if (Array.isArray(value)) {
    for (const item of value) {
      lines.push(`${pad}-`)
      lines.push(emitNt(item, depth + 1))
    }
  } else {
    for (const [key, v] of Object.entries(value)) {
      if (typeof v === 'string') {
        lines.push(`${pad}${key}: ${v}`)
      } else {
        lines.push(`${pad}${key}:`)
        lines.push(emitNt(v, depth + 1))
      }
    }
  }
  return lines.join('\n')
}

function deviceTargetNt(target: DeviceTarget): string {
  return target === 'selected' ? 'selected' : target.name
}

function rangeMapNt(rm: RangeMap): NtDict {
  const out: NtDict = { range: printCoordExpr(rm.range) }
  if (rm.parameters !== undefined) out.parameters = rm.parameters
  if (rm.slots !== undefined) out.slots = rm.slots
  return out
}

function bindingsNt(bindings: Record<string, unknown>): NtDict {
  const out: NtDict = {}
  for (const [key, expr] of Object.entries(bindings)) {
    if (expr !== undefined) out[key] = printCoordExpr(expr as never)
  }
  return out
}

export function mappingToNt(mapping: Mapping): NtDict {
  switch (mapping.type) {
    case 'device': {
      const inner: NtDict = {}
      if (mapping.encoders) inner.encoders = rangeMapNt(mapping.encoders)
      if (mapping.encoderList?.length) inner['encoder-list'] = mapping.encoderList.map(rangeMapNt)
      if (mapping.onOff) inner['on-off'] = printCoordExpr(mapping.onOff)
      if (mapping.button) inner.button = rangeMapNt(mapping.button)
      if (mapping.buttonList?.length) inner['button-list'] = mapping.buttonList.map(rangeMapNt)
      return {
        type: 'device',
        track: mapping.track,
        device: deviceTargetNt(mapping.device),
        mappings: inner
      }
    }
    case 'mixer':
      return { type: 'mixer', track: mapping.track, mappings: bindingsNt(mapping.bindings) }
    case 'transport':
    case 'track-nav':
    case 'device-nav':
    case 'functions':
    case 'clip':
      return { type: mapping.type, mappings: bindingsNt(mapping.bindings) }
    case 'parameter-pager': {
      const out: NtDict = { type: 'parameter-pager' }
      if (mapping.encoders) {
        out.encoders = { inc: printCoordExpr(mapping.encoders.inc), dec: printCoordExpr(mapping.encoders.dec) }
      }
      if (mapping.buttons) {
        out.buttons = { inc: printCoordExpr(mapping.buttons.inc), dec: printCoordExpr(mapping.buttons.dec) }
      }
      return out
    }
  }
}

function modeToNt(mode: Mode): NtDict {
  const out: NtDict = { name: mode.name }
  if (mode.onColor !== undefined) out.on_color = mode.onColor
  out.mappings = mode.mappings.map(mappingToNt)
  return out
}

export function documentToNt(doc: MappingDocument): NtDict {
  const out: NtDict = {
    controller: doc.controllerPath,
    ableton_dir: doc.abletonDir
  }
  if (doc.parameterMappingsFile !== undefined) out.parameter_mappings_file = doc.parameterMappingsFile
  if (doc.remoteOn !== undefined) out.remote_on = doc.remoteOn ? 'true' : 'false'
  out.hud = doc.hud
  out['show-hud-on'] = doc.showHudOn
  if (doc.modeButton) {
    out['mode-button'] = {
      button: printCoordExpr(doc.modeButton.button),
      type: doc.modeButton.type
    }
  }
  if (doc.modeless) {
    out.mappings = doc.modes[0].mappings.map(mappingToNt)
  } else {
    out.modes = doc.modes.map(modeToNt)
  }
  return out
}

export function serializeDocument(doc: MappingDocument): string {
  return emitNt(documentToNt(doc)) + '\n'
}
