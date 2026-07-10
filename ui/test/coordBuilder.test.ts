import { describe, expect, it } from 'vitest'
import { parseCoordExpr, printCoordExpr } from '../src/shared/coords'
import {
  Cell,
  GroupShape,
  cellsOf,
  selectionToExpr,
  OrphanCoordError,
  dedupeSelection
} from '../src/shared/coordBuilder'

const grid4x4 = (number: number): GroupShape => ({ number, control_count: 16, columns: 4, rows: 4 })
const row8 = (number: number): GroupShape => ({ number, control_count: 8, columns: null, rows: null })
const GROUPS: GroupShape[] = [row8(1), grid4x4(2), grid4x4(3)]

const cells = (group: number, ...indices: number[]): Cell[] => indices.map((index) => ({ group, index }))

function coordOf(sel: Cell[]): string {
  return printCoordExpr(selectionToExpr(sel, GROUPS))
}

describe('selectionToExpr', () => {
  it('single cell in a row group', () => {
    expect(coordOf(cells(1, 3))).toBe('row-1:3')
  })
  it('contiguous row run', () => {
    expect(coordOf(cells(1, 3, 4, 5, 6))).toBe('row-1:3-6')
  })
  it('run within one grid row uses row::col form', () => {
    expect(coordOf(cells(2, 13))).toBe('grid-2:4::1')
    expect(coordOf(cells(2, 5, 6, 7))).toBe('grid-2:2::1-3')
  })
  it('run crossing grid rows uses flat form', () => {
    expect(coordOf(cells(2, 5, 6, 7, 8, 9))).toBe('grid-2:5-9')
  })
  it('whole grid uses flat form', () => {
    expect(coordOf(cells(2, ...Array.from({ length: 16 }, (_, i) => i + 1)))).toBe('grid-2:1-16')
  })
  it('non-contiguous selection becomes comma-joined atoms in pick order', () => {
    expect(coordOf(cells(2, 5, 6, 7, 8, 9, 10, 11, 12))).toBe('grid-2:5-12')
    expect(coordOf([...cells(2, 5, 6), ...cells(2, 9, 10)])).toBe('grid-2:2::1-2,grid-2:3::1-2')
  })
  it('multi-group selection', () => {
    expect(coordOf([...cells(1, 1, 2), ...cells(2, 1)])).toBe('row-1:1-2,grid-2:1::1')
  })
  it('descending pick order yields per-cell atoms (no descending ranges)', () => {
    expect(coordOf(cells(1, 3, 2, 1))).toBe('row-1:3,row-1:2,row-1:1')
  })
})

describe('cellsOf (inverse)', () => {
  const roundTrip = ['row-1:3-6', 'grid-2:4::1', 'grid-2:2::1-3', 'grid-2:5-12', 'grid-2:1-16']
  for (const text of roundTrip) {
    it(`cellsOf∘build is identity for '${text}'`, () => {
      const expanded = cellsOf(parseCoordExpr(text), GROUPS)
      expect(printCoordExpr(selectionToExpr(expanded, GROUPS))).toBe(text)
    })
  }
  it('adjacent atoms re-compress to the minimal equivalent expression', () => {
    const expanded = cellsOf(parseCoordExpr('grid-2:5-8,grid-2:9-12'), GROUPS)
    expect(printCoordExpr(selectionToExpr(expanded, GROUPS))).toBe('grid-2:5-12')
    expect(expanded).toEqual(cellsOf(parseCoordExpr('grid-2:5-12'), GROUPS))
  })
  it('expands grid-cell form to flat indices', () => {
    expect(cellsOf(parseCoordExpr('grid-2:4::1-2'), GROUPS)).toEqual(cells(2, 13, 14))
  })
  it('throws OrphanCoordError for a missing group', () => {
    expect(() => cellsOf(parseCoordExpr('grid-9:1'), GROUPS)).toThrow(OrphanCoordError)
  })
  it('throws OrphanCoordError for out-of-range indices', () => {
    expect(() => cellsOf(parseCoordExpr('row-1:9'), GROUPS)).toThrow(OrphanCoordError)
    expect(() => cellsOf(parseCoordExpr('grid-2:5::1'), GROUPS)).toThrow(OrphanCoordError)
  })
})

describe('dedupeSelection', () => {
  it('keeps first-pick order', () => {
    expect(dedupeSelection([...cells(1, 3, 2), ...cells(1, 3)])).toEqual(cells(1, 3, 2))
  })
})
