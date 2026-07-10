// Create a pre-filled Mapping from an ordered canvas selection. Pick order is
// semantic: it decides slot order, send order, and which button lands on which
// action well.

import { nanoid } from 'nanoid'
import type { Cell, GroupShape } from './coordBuilder'
import { selectionToExpr } from './coordBuilder'
import type { CoordExpr } from './coords'
import type { Mapping, MappingType } from './document'
import { TRANSPORT_ACTIONS, DEVICE_NAV_ACTIONS, TRACK_NAV_ACTIONS } from './document'
import type { ControlKind } from './wellSpec'

export interface CellInfo extends GroupShape {
  type: ControlKind
}

function kindOf(cell: Cell, groups: CellInfo[]): ControlKind {
  const g = groups.find((g) => g.number === cell.group)
  if (!g) throw new Error(`no group ${cell.group}`)
  return g.type
}

function splitByKind(cells: Cell[], groups: CellInfo[]): { encoders: Cell[]; buttons: Cell[] } {
  const encoders: Cell[] = []
  const buttons: Cell[] = []
  for (const cell of cells) {
    ;(kindOf(cell, groups) === 'button' ? buttons : encoders).push(cell)
  }
  return { encoders, buttons }
}

function exprOf(cells: Cell[], groups: CellInfo[]): CoordExpr {
  return selectionToExpr(cells, groups)
}

function fillActions<K extends string>(
  actions: readonly K[],
  cells: Cell[],
  groups: CellInfo[]
): Partial<Record<K, CoordExpr>> {
  const bindings: Partial<Record<K, CoordExpr>> = {}
  cells.slice(0, actions.length).forEach((cell, i) => {
    bindings[actions[i]] = exprOf([cell], groups)
  })
  return bindings
}

export function createMapping(type: MappingType, cells: Cell[], groups: CellInfo[]): Mapping {
  const id = nanoid(8)
  switch (type) {
    case 'device': {
      const { encoders, buttons } = splitByKind(cells, groups)
      return {
        id,
        type,
        track: 'selected',
        device: 'selected',
        ...(encoders.length
          ? { encoders: { range: exprOf(encoders, groups), slots: `1-${encoders.length}` } }
          : {}),
        ...(buttons.length
          ? { button: { range: exprOf(buttons, groups), slots: `1-${buttons.length}` } }
          : {})
      }
    }
    case 'mixer': {
      const { encoders, buttons } = splitByKind(cells, groups)
      const bindings: Record<string, CoordExpr> = {}
      if (encoders.length === 1) bindings.volume = exprOf(encoders, groups)
      else if (encoders.length > 1) bindings.sends = exprOf(encoders, groups)
      const buttonWells = ['mute', 'solo', 'arm'] as const
      buttons.slice(0, 3).forEach((cell, i) => {
        bindings[buttonWells[i]] = exprOf([cell], groups)
      })
      return { id, type, track: 'selected', bindings }
    }
    case 'transport':
      return { id, type, bindings: fillActions(TRANSPORT_ACTIONS, cells, groups) }
    case 'track-nav':
      return { id, type, bindings: fillActions(TRACK_NAV_ACTIONS, cells, groups) }
    case 'device-nav':
      return { id, type, bindings: fillActions(DEVICE_NAV_ACTIONS, cells, groups) }
    case 'functions': {
      const bindings: Record<string, CoordExpr> = {}
      cells.forEach((cell, i) => {
        bindings[`function_${i + 1}`] = exprOf([cell], groups)
      })
      return { id, type, bindings }
    }
    case 'parameter-pager': {
      const [dec, inc] = cells
      const kind = kindOf(dec, groups)
      const pair = { dec: exprOf([dec], groups), inc: exprOf([inc], groups) }
      return kind === 'button' ? { id, type, buttons: pair } : { id, type, encoders: pair }
    }
    case 'clip':
      // Bindings assigned in the clip inspector ("fill from selection" there).
      return { id, type, bindings: {} }
  }
}
