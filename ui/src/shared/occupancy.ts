// Which cells a mapping claims, and which mapping(s) claim each cell.

import type { CoordExpr } from './coords'
import type { Mapping } from './document'
import { Cell, GroupShape, cellKey, cellsOf, OrphanCoordError } from './coordBuilder'

export interface WellExpr {
  /** human name of the well, e.g. 'encoders', 'volume', 'inc' */
  well: string
  expr: CoordExpr
}

export function exprsOfMapping(mapping: Mapping): WellExpr[] {
  switch (mapping.type) {
    case 'device': {
      const out: WellExpr[] = []
      if (mapping.encoders) out.push({ well: 'encoders', expr: mapping.encoders.range })
      mapping.encoderList?.forEach((rm, i) => out.push({ well: `encoders[${i + 1}]`, expr: rm.range }))
      if (mapping.onOff) out.push({ well: 'on-off', expr: mapping.onOff })
      if (mapping.button) out.push({ well: 'button', expr: mapping.button.range })
      mapping.buttonList?.forEach((rm, i) => out.push({ well: `button[${i + 1}]`, expr: rm.range }))
      return out
    }
    case 'parameter-pager': {
      const out: WellExpr[] = []
      if (mapping.encoders) {
        out.push({ well: 'enc dec', expr: mapping.encoders.dec }, { well: 'enc inc', expr: mapping.encoders.inc })
      }
      if (mapping.buttons) {
        out.push({ well: 'btn dec', expr: mapping.buttons.dec }, { well: 'btn inc', expr: mapping.buttons.inc })
      }
      return out
    }
    default:
      return Object.entries(mapping.bindings)
        .filter(([, expr]) => expr !== undefined)
        .map(([well, expr]) => ({ well, expr: expr as CoordExpr }))
  }
}

export interface CellClaim {
  mappingId: string
  mappingType: Mapping['type']
  well: string
}

export interface OccupancyResult {
  /** cellKey → claims (length > 1 within one mode = clash) */
  claims: Map<string, CellClaim[]>
  /** mapping wells whose coords no longer resolve on this controller */
  orphans: { mappingId: string; well: string; message: string }[]
}

export function computeOccupancy(mappings: Mapping[], groups: GroupShape[]): OccupancyResult {
  const claims = new Map<string, CellClaim[]>()
  const orphans: OccupancyResult['orphans'] = []
  for (const mapping of mappings) {
    for (const { well, expr } of exprsOfMapping(mapping)) {
      let cells: Cell[]
      try {
        cells = cellsOf(expr, groups)
      } catch (e) {
        if (e instanceof OrphanCoordError) {
          orphans.push({ mappingId: mapping.id, well, message: e.message })
          continue
        }
        throw e
      }
      for (const cell of cells) {
        const key = cellKey(cell)
        const list = claims.get(key) ?? []
        list.push({ mappingId: mapping.id, mappingType: mapping.type, well })
        claims.set(key, list)
      }
    }
  }
  return { claims, orphans }
}
