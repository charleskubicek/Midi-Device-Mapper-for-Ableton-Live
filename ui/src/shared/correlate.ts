// Map sidecar problem messages back to the mappings they concern.
//
// The generator's problem strings are prose, but they reliably embed the
// coordinate strings and mode names the UI itself wrote. We extract coord
// tokens, expand them to cells, and find the mappings claiming those cells.

import { parseAtom, CoordParseError } from './coords'
import { Cell, GroupShape, cellKey, cellsOf } from './coordBuilder'
import type { Mode } from './document'
import { exprsOfMapping } from './occupancy'

const COORD_TOKEN = /\b(?:row|col|grid)-\d+:\d+(?:::\d+(?:-\d+)?|-\d+)?\b/g

export function extractCoordTokens(message: string): string[] {
  return [...new Set(message.match(COORD_TOKEN) ?? [])]
}

export interface CorrelationInput {
  message: string
  modes: Mode[]
  groups: GroupShape[]
}

/** ids of mappings the message most plausibly concerns (empty = panel-only) */
export function correlateProblem({ message, modes, groups }: CorrelationInput): string[] {
  const tokens = extractCoordTokens(message)
  if (tokens.length === 0) return []

  const cells: Cell[] = []
  for (const token of tokens) {
    try {
      cells.push(...cellsOf({ atoms: [parseAtom(token)], refinements: [] }, groups))
    } catch (e) {
      if (e instanceof CoordParseError) continue
      // unresolvable (orphan) coords still correlate by token below
      continue
    }
  }
  const cellKeys = new Set(cells.map(cellKey))

  // Prefer modes named in the message; fall back to all modes.
  const namedModes = modes.filter((m) => message.includes(`'${m.name}'`) || message.includes(`mode ${m.name}`))
  const searchModes = namedModes.length ? namedModes : modes

  const ids = new Set<string>()
  for (const mode of searchModes) {
    for (const mapping of mode.mappings) {
      for (const { expr } of exprsOfMapping(mapping)) {
        let claimed: Cell[]
        try {
          claimed = cellsOf(expr, groups)
        } catch {
          continue
        }
        if (claimed.some((c) => cellKeys.has(cellKey(c)))) {
          ids.add(mapping.id)
          break
        }
      }
    }
  }
  return [...ids]
}
