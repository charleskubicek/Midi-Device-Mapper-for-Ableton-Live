import { describe, expect, it } from 'vitest'
import { parseCoordExpr, printCoordExpr, cellCount, CoordParseError } from '../src/shared/coords'

const roundTrips = [
  'row-1:3',
  'row-1:1-8',
  'row-2:3-6',
  'col-3:2',
  'grid-2:5-12',
  'grid-2:4::1',
  'grid-2:2::1-4',
  'grid-1:5-8,grid-1:9-12',
  'row-2:3,grid-2:4::2',
  'grid-4:4::2 momentary',
  'row-1:1-8 map_mode_absolute',
  'grid-2:4::1 mode-2'
]

describe('coord expressions', () => {
  for (const text of roundTrips) {
    it(`round-trips '${text}'`, () => {
      expect(printCoordExpr(parseCoordExpr(text))).toBe(text)
    })
  }

  it('counts cells across atoms', () => {
    expect(cellCount(parseCoordExpr('grid-1:5-8,grid-1:9-12'))).toBe(8)
    expect(cellCount(parseCoordExpr('row-1:3'))).toBe(1)
    expect(cellCount(parseCoordExpr('grid-2:2::1-4'))).toBe(4)
  })

  it('normalizes single-cell ranges to bare numbers', () => {
    const expr = parseCoordExpr('row-1:3-3')
    expect(printCoordExpr(expr)).toBe('row-1:3')
  })

  it('rejects garbage with a helpful message', () => {
    expect(() => parseCoordExpr('row1:3')).toThrow(CoordParseError)
    expect(() => parseCoordExpr('grid-2:8-5')).toThrow(/ascending/)
    expect(() => parseCoordExpr('row-1:2::3')).toThrow(/grid axis/)
  })
})
