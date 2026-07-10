import type { ControlGroupInfo } from '../../../shared/protocol'
import type { Cell } from '../../../shared/coordBuilder'

export const CELL = 44
export const PAD = 10
export const HEADER = 20
const GAP = 24

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface PlacedCell {
  cell: Cell
  rect: Rect
}

export interface PlacedGroup {
  group: ControlGroupInfo
  rect: Rect
  cells: PlacedCell[]
  /** 'grid' | 'row' — how coords address this group */
  axis: 'grid' | 'row'
  cols: number
  rows: number
}

export interface CanvasLayout {
  groups: PlacedGroup[]
  width: number
  height: number
}

function shapeOf(group: ControlGroupInfo): { rows: number; cols: number } {
  if (group.columns != null && group.rows != null) return { rows: group.rows, cols: group.columns }
  return { rows: 1, cols: group.control_count }
}

export function cardSize(group: ControlGroupInfo): { w: number; h: number } {
  const { rows, cols } = shapeOf(group)
  return { w: cols * CELL + PAD * 2, h: rows * CELL + PAD * 2 + HEADER }
}

/** Bucket groups by grid_row, order by grid_col — the generator's reading order. */
export function layoutController(groups: ControlGroupInfo[]): CanvasLayout {
  const rowBuckets = new Map<number, ControlGroupInfo[]>()
  for (const g of groups) {
    const bucket = rowBuckets.get(g.grid_row) ?? []
    bucket.push(g)
    rowBuckets.set(g.grid_row, bucket)
  }
  const placed: PlacedGroup[] = []
  let y = 0
  let width = 0
  for (const rowKey of [...rowBuckets.keys()].sort((a, b) => a - b)) {
    const bucket = rowBuckets.get(rowKey)!.sort((a, b) => a.grid_col - b.grid_col)
    let x = 0
    let rowHeight = 0
    for (const group of bucket) {
      const { rows, cols } = shapeOf(group)
      const { w, h } = cardSize(group)
      const cells: PlacedCell[] = []
      for (let i = 0; i < group.control_count; i++) {
        const r = Math.floor(i / cols)
        const c = i % cols
        if (r >= rows) break
        cells.push({
          cell: { group: group.number, index: i + 1 },
          rect: { x: x + PAD + c * CELL, y: y + HEADER + PAD + r * CELL, w: CELL, h: CELL }
        })
      }
      placed.push({
        group,
        rect: { x, y, w, h },
        cells,
        axis: group.columns != null ? 'grid' : 'row',
        cols,
        rows
      })
      x += w + GAP
      rowHeight = Math.max(rowHeight, h)
    }
    width = Math.max(width, x - GAP)
    y += rowHeight + GAP
  }
  return { groups: placed, width, height: y - GAP }
}

export function intersects(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}

export function cellAtPoint(layout: CanvasLayout, x: number, y: number): Cell | null {
  for (const pg of layout.groups) {
    for (const pc of pg.cells) {
      const r = pc.rect
      if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) return pc.cell
    }
  }
  return null
}

/** Cells inside a marquee rect, in reading order (group order, then index). */
export function cellsInRect(layout: CanvasLayout, rect: Rect): Cell[] {
  const out: Cell[] = []
  for (const pg of layout.groups) {
    for (const pc of pg.cells) {
      if (intersects(rect, pc.rect)) out.push(pc.cell)
    }
  }
  return out
}
