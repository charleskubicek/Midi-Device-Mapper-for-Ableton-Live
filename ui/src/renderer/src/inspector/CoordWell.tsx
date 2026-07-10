import { useEffect, useState } from 'react'
import type { CoordExpr } from '../../../shared/coords'
import { parseCoordExpr, printCoordExpr, CoordParseError } from '../../../shared/coords'
import type { GroupShape } from '../../../shared/coordBuilder'
import { cellsOf, selectionToExpr, OrphanCoordError } from '../../../shared/coordBuilder'
import { kindMatches, Accepts, ControlKind } from '../../../shared/wellSpec'
import { useUiStore } from '../store/uiStore'

interface Props {
  label: string
  expr: CoordExpr | undefined
  accepts: Accepts
  groups: (GroupShape & { type: ControlKind })[]
  onChange(expr: CoordExpr | undefined): void
  /** show a momentary-refinement toggle (button wells) */
  refinable?: boolean
}

/** A single coordinate field: typed input + assign-from-selection + clear. */
export function CoordWell({ label, expr, accepts, groups, onChange, refinable }: Props) {
  const selection = useUiStore((s) => s.selection)
  const [text, setText] = useState(expr ? printCoordExpr(expr) : '')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setText(expr ? printCoordExpr(expr) : '')
    setError(null)
  }, [expr])

  const validate = (candidate: CoordExpr): string | null => {
    let cells
    try {
      cells = cellsOf(candidate, groups)
    } catch (e) {
      if (e instanceof OrphanCoordError) return e.message
      throw e
    }
    const byNumber = new Map(groups.map((g) => [g.number, g]))
    const bad = cells.find((c) => !kindMatches(accepts, byNumber.get(c.group)!.type))
    if (bad) return `${label} needs ${accepts === 'button' ? 'buttons' : 'encoders'}; ${printCoordExpr({ atoms: [{ form: 'strip', axis: 'row', group: bad.group, from: bad.index, to: bad.index }], refinements: [] })} is a ${byNumber.get(bad.group)!.type}`
    return null
  }

  const commitText = () => {
    if (!text.trim()) {
      onChange(undefined)
      setError(null)
      return
    }
    try {
      const parsed = parseCoordExpr(text)
      const problem = validate(parsed)
      setError(problem)
      if (!problem) onChange(parsed)
    } catch (e) {
      if (e instanceof CoordParseError) setError(e.message)
      else throw e
    }
  }

  const assignFromSelection = () => {
    if (selection.length === 0) return
    const candidate = selectionToExpr(selection, groups)
    candidate.refinements = expr?.refinements ?? []
    const problem = validate(candidate)
    setError(problem)
    if (!problem) onChange(candidate)
  }

  const hasMomentary = expr?.refinements.includes('momentary') ?? false
  const toggleMomentary = () => {
    if (!expr) return
    onChange({
      ...expr,
      refinements: hasMomentary
        ? expr.refinements.filter((r) => r !== 'momentary')
        : [...expr.refinements, 'momentary']
    })
  }

  return (
    <div className="coord-well">
      <span className="well-label">{label}</span>
      <input
        value={text}
        placeholder="e.g. grid-2:4::1"
        onChange={(e) => setText(e.target.value)}
        onBlur={commitText}
        onKeyDown={(e) => e.key === 'Enter' && commitText()}
      />
      <button
        title={selection.length ? 'Assign the canvas selection' : 'Select controls on the canvas first'}
        disabled={selection.length === 0}
        onClick={assignFromSelection}
      >
        ⇐ sel
      </button>
      {expr && (
        <button title="Clear" onClick={() => onChange(undefined)}>
          ✕
        </button>
      )}
      {refinable && expr && (
        <label className="well-flag" title="Act on press and release (hold behavior)">
          <input type="checkbox" checked={hasMomentary} onChange={toggleMomentary} /> momentary
        </label>
      )}
      {error && <div className="well-error">{error}</div>}
    </div>
  )
}
