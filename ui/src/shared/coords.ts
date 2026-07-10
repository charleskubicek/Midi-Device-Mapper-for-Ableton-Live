// Coordinate expressions — the TS mirror of encoder_coords.py's grammar.
// Printing must emit exactly what the Lark grammar accepts; parsing exists so
// power users can type coordinate strings into inspector wells.

export type Axis = 'row' | 'col' | 'grid'

export type CoordAtom =
  | { form: 'strip'; axis: 'row' | 'col'; group: number; from: number; to: number } // row-1:3-6
  | { form: 'grid-flat'; group: number; from: number; to: number } //                 grid-1:5-12
  | { form: 'grid-cell'; group: number; gridRow: number; from: number; to: number } // grid-2:4::1-3

// 'toggle' is deprecated in the grammar (now the default behavior) — never offered.
export type Refinement = 'momentary' | 'mode-2' | 'map_mode_absolute'
export const REFINEMENTS: Refinement[] = ['momentary', 'mode-2', 'map_mode_absolute']

export interface CoordExpr {
  atoms: CoordAtom[]
  refinements: Refinement[]
}

export function atomCellCount(atom: CoordAtom): number {
  return atom.to - atom.from + 1
}

export function cellCount(expr: CoordExpr): number {
  return expr.atoms.reduce((n, a) => n + atomCellCount(a), 0)
}

function printRange(from: number, to: number): string {
  return from === to ? `${from}` : `${from}-${to}`
}

export function printAtom(atom: CoordAtom): string {
  switch (atom.form) {
    case 'strip':
      return `${atom.axis}-${atom.group}:${printRange(atom.from, atom.to)}`
    case 'grid-flat':
      return `grid-${atom.group}:${printRange(atom.from, atom.to)}`
    case 'grid-cell':
      return `grid-${atom.group}:${atom.gridRow}::${printRange(atom.from, atom.to)}`
  }
}

export function printCoordExpr(expr: CoordExpr): string {
  const atoms = expr.atoms.map(printAtom).join(',')
  return expr.refinements.length ? `${atoms} ${expr.refinements.join(' ')}` : atoms
}

const ATOM_RE = /^(row|col|grid)-(\d+):(?:(\d+)::)?(\d+)(?:-(\d+))?$/

export class CoordParseError extends Error {}

export function parseAtom(text: string): CoordAtom {
  const m = ATOM_RE.exec(text.trim())
  if (!m) {
    throw new CoordParseError(
      `Bad coordinate '${text.trim()}' — expected forms like row-1:3, row-1:1-8, grid-2:5-12, grid-2:4::1-3`
    )
  }
  const [, axis, groupS, gridRowS, fromS, toS] = m
  const group = Number(groupS)
  const from = Number(fromS)
  const to = toS ? Number(toS) : from
  if (from < 1 || to < from) {
    throw new CoordParseError(`Bad range in '${text.trim()}': must be ascending and start at 1 or higher`)
  }
  if (gridRowS) {
    if (axis !== 'grid') throw new CoordParseError(`'${text.trim()}': row::col form is only valid on a grid axis`)
    return { form: 'grid-cell', group, gridRow: Number(gridRowS), from, to }
  }
  if (axis === 'grid') return { form: 'grid-flat', group, from, to }
  return { form: 'strip', axis: axis as 'row' | 'col', group, from, to }
}

export function parseCoordExpr(text: string): CoordExpr {
  const tokens = text.trim().split(/\s+/)
  const refinements: Refinement[] = []
  while (tokens.length > 1 && (REFINEMENTS as string[]).includes(tokens[tokens.length - 1])) {
    refinements.unshift(tokens.pop() as Refinement)
  }
  const atomsText = tokens.join(' ')
  const atoms = atomsText.split(',').map(parseAtom)
  if (atoms.length === 0) throw new CoordParseError('Empty coordinate')
  return { atoms, refinements }
}
