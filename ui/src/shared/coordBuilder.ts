// Selection ⇄ coordinate expressions.
//
// A selection is an ORDERED list of cells — order carries meaning (slot/send
// assignment follows pick order). A cell is (group number, 1-based flat index
// within the group). selectionToAtoms compresses a selection into the minimal
// atom list the grammar allows; cellsOf expands any expression back to cells.

import type { CoordAtom, CoordExpr } from './coords'

export interface Cell {
  group: number
  index: number
}

export function cellKey(cell: Cell): string {
  return `${cell.group}:${cell.index}`
}

/** The subset of sidecar group info the coord math needs. */
export interface GroupShape {
  number: number
  control_count: number
  /** null for row/col strips; set for layout:grid groups */
  columns: number | null
  rows: number | null
}

function isGrid(g: GroupShape): boolean {
  return g.columns != null
}

/** grid row (1-based) containing a flat index, for a grid group */
function gridRowOf(index: number, columns: number): number {
  return Math.floor((index - 1) / columns) + 1
}
function colOf(index: number, columns: number): number {
  return ((index - 1) % columns) + 1
}

export class OrphanCoordError extends Error {}

/** Expand an expression into ordered cells. Throws OrphanCoordError when the
 *  expression doesn't resolve against the given groups (controller changed). */
export function cellsOf(expr: CoordExpr, groups: GroupShape[]): Cell[] {
  const byNumber = new Map(groups.map((g) => [g.number, g]))
  const cells: Cell[] = []
  for (const atom of expr.atoms) {
    const group = byNumber.get(atom.group)
    if (!group) throw new OrphanCoordError(`no group ${atom.group} on this controller`)
    let from = atom.from
    let to = atom.to
    if (atom.form === 'grid-cell') {
      if (!isGrid(group)) throw new OrphanCoordError(`group ${atom.group} is not a grid`)
      const cols = group.columns!
      if (atom.gridRow > group.rows! || atom.to > cols) {
        throw new OrphanCoordError(`grid-${atom.group}:${atom.gridRow}::${atom.from}-${atom.to} is outside the grid`)
      }
      from = (atom.gridRow - 1) * cols + atom.from
      to = (atom.gridRow - 1) * cols + atom.to
    }
    if (to > group.control_count) {
      throw new OrphanCoordError(`index ${to} is outside group ${atom.group} (${group.control_count} controls)`)
    }
    for (let i = from; i <= to; i++) cells.push({ group: atom.group, index: i })
  }
  return cells
}

/** Compress ordered cells into minimal atoms, preserving selection order.
 *  Runs of flat-consecutive cells in the same group become one atom:
 *  - row/col strip groups → strip atom (row-1:3-6)
 *  - grid groups, run within one grid row → grid-cell atom (grid-2:4::1-3),
 *    matching hand-written style — except a run covering the WHOLE grid,
 *    which reads better flat (grid-1:1-16)
 *  - grid groups, run crossing grid rows → flat atom (grid-2:5-12)
 */
export function selectionToAtoms(cells: Cell[], groups: GroupShape[]): CoordAtom[] {
  const byNumber = new Map(groups.map((g) => [g.number, g]))
  const atoms: CoordAtom[] = []
  let run: Cell[] = []

  const flush = () => {
    if (run.length === 0) return
    const group = byNumber.get(run[0].group)
    if (!group) throw new OrphanCoordError(`no group ${run[0].group} on this controller`)
    const from = run[0].index
    const to = run[run.length - 1].index
    if (!isGrid(group)) {
      atoms.push({ form: 'strip', axis: 'row', group: group.number, from, to })
    } else {
      const cols = group.columns!
      const sameRow = gridRowOf(from, cols) === gridRowOf(to, cols)
      const wholeGrid = from === 1 && to === group.control_count
      if (sameRow && !wholeGrid) {
        atoms.push({
          form: 'grid-cell',
          group: group.number,
          gridRow: gridRowOf(from, cols),
          from: colOf(from, cols),
          to: colOf(to, cols)
        })
      } else {
        atoms.push({ form: 'grid-flat', group: group.number, from, to })
      }
    }
    run = []
  }

  for (const cell of cells) {
    const prev = run[run.length - 1]
    if (prev && (cell.group !== prev.group || cell.index !== prev.index + 1)) flush()
    run.push(cell)
  }
  flush()
  return atoms
}

export function selectionToExpr(cells: Cell[], groups: GroupShape[]): CoordExpr {
  return { atoms: selectionToAtoms(cells, groups), refinements: [] }
}

/** Normalize an arbitrary click/marquee selection: dedupe, keep first-pick order. */
export function dedupeSelection(cells: Cell[]): Cell[] {
  const seen = new Set<string>()
  const out: Cell[] = []
  for (const cell of cells) {
    const key = cellKey(cell)
    if (!seen.has(key)) {
      seen.add(key)
      out.push(cell)
    }
  }
  return out
}
