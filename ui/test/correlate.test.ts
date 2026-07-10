import { describe, expect, it } from 'vitest'
import { correlateProblem, extractCoordTokens } from '../src/shared/correlate'
import type { GroupShape } from '../src/shared/coordBuilder'
import { parseCoordExpr } from '../src/shared/coords'
import type { Mode } from '../src/shared/document'

const GROUPS: GroupShape[] = [
  { number: 1, control_count: 16, columns: 4, rows: 4 },
  { number: 2, control_count: 16, columns: 4, rows: 4 }
]

const modes: Mode[] = [
  {
    name: 'main_mode',
    mappings: [
      { id: 'mx1', type: 'mixer', track: 'selected', bindings: { volume: parseCoordExpr('grid-2:1') } },
      { id: 'fn1', type: 'functions', bindings: { hud_toggle: parseCoordExpr('grid-1:4::2') } }
    ]
  },
  {
    name: 'shift_mode',
    mappings: [
      { id: 'mx2', type: 'mixer', track: 'selected', bindings: { pan: parseCoordExpr('grid-2:1') } }
    ]
  }
]

describe('extractCoordTokens', () => {
  it('finds all coordinate forms in prose', () => {
    expect(
      extractCoordTokens(
        "Clash: 'grid-2:1' and grid-1:4::2 overlap; also row-3:5-8 (from grid-2:1)"
      )
    ).toEqual(['grid-2:1', 'grid-1:4::2', 'row-3:5-8'])
  })
  it('returns empty for messages without coords', () => {
    expect(extractCoordTokens('Duplicate mode name(s): main_mode')).toEqual([])
  })
})

describe('correlateProblem', () => {
  it('maps a clash message to the mappings claiming that cell, filtered by named mode', () => {
    const ids = correlateProblem({
      message: "Clashing mappings in mode 'main_mode': grid-2:1 is bound twice",
      modes,
      groups: GROUPS
    })
    expect(ids).toEqual(['mx1'])
  })
  it('searches all modes when none is named', () => {
    const ids = correlateProblem({ message: 'Problem with grid-2:1 somewhere', modes, groups: GROUPS })
    expect(ids.sort()).toEqual(['mx1', 'mx2'])
  })
  it('returns empty for uncorrelatable messages', () => {
    expect(correlateProblem({ message: 'Missing required HUD setting(s)', modes, groups: GROUPS })).toEqual([])
  })
})
