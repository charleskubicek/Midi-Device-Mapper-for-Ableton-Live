import { useMemo } from 'react'
import type { ControllerInfo } from '../../../shared/protocol'
import { cellKey, cellsOf } from '../../../shared/coordBuilder'
import { computeOccupancy } from '../../../shared/occupancy'
import { useDocumentStore } from '../store/documentStore'
import { useUiStore } from '../store/uiStore'
import { useValidationStore, UiProblem } from '../store/validationStore'

/** Instant TS-side checks: intra-mode clashes, orphaned coords, mode-button collisions. */
function instantProblems(controller: ControllerInfo): UiProblem[] {
  const doc = useDocumentStore.getState().doc
  if (!doc) return []
  const problems: UiProblem[] = []

  let modeButtonKeys = new Set<string>()
  if (doc.modeButton) {
    try {
      modeButtonKeys = new Set(cellsOf(doc.modeButton.button, controller.groups).map(cellKey))
    } catch {
      problems.push({
        message: 'The mode button no longer resolves on this controller — re-pick it.',
        kind: 'orphan',
        mappingIds: [],
        source: 'instant'
      })
    }
  }

  for (const mode of doc.modes) {
    const { claims, orphans } = computeOccupancy(mode.mappings, controller.groups)
    for (const [key, claimList] of claims) {
      if (claimList.length > 1) {
        problems.push({
          message: `Clash in '${mode.name}': one control is bound by ${claimList
            .map((c) => `${c.mappingType} (${c.well})`)
            .join(' and ')}`,
          kind: 'clash',
          mappingIds: claimList.map((c) => c.mappingId),
          source: 'instant'
        })
      }
      if (modeButtonKeys.has(key)) {
        problems.push({
          message: `A ${claimList[0].mappingType} mapping in '${mode.name}' claims the mode button cell.`,
          kind: 'clash',
          mappingIds: claimList.map((c) => c.mappingId),
          source: 'instant'
        })
      }
    }
    for (const orphan of orphans) {
      problems.push({
        message: `Orphaned coordinate in '${mode.name}' (${orphan.well}): ${orphan.message} — re-pick the controls.`,
        kind: 'orphan',
        mappingIds: [orphan.mappingId],
        source: 'instant'
      })
    }
  }
  return problems
}

export function ProblemsPanel({ controller }: { controller: ControllerInfo }) {
  const doc = useDocumentStore((s) => s.doc)
  const status = useValidationStore((s) => s.status)
  const engineProblems = useValidationStore((s) => s.engineProblems)
  const selectMapping = useUiStore((s) => s.selectMapping)
  const setActiveMode = useUiStore((s) => s.setActiveMode)

  const instant = useMemo(() => (doc ? instantProblems(controller) : []), [doc, controller])
  // Engine problems that an instant check already reports (same coords) stay
  // useful for wording, but avoid pure duplicates by keying on mappingIds+kind.
  const all = [...instant, ...engineProblems]

  if (!doc) return null

  const focus = (problem: UiProblem) => {
    const id = problem.mappingIds[0]
    if (!id) return
    const modeIndex = doc.modes.findIndex((m) => m.mappings.some((mm) => mm.id === id))
    if (modeIndex >= 0) setActiveMode(modeIndex)
    selectMapping(id)
  }

  return (
    <div className={`problems-panel ${all.length ? 'has-problems' : ''}`}>
      <span className={`validation-pill ${status}`}>
        {status === 'valid' && all.length === 0
          ? '✓ valid'
          : status === 'validating'
            ? 'validating…'
            : status === 'offline'
              ? 'engine offline'
              : `${all.length} problem${all.length === 1 ? '' : 's'}`}
      </span>
      {all.map((p, i) => (
        <button
          key={i}
          className={`problem-row ${p.kind}`}
          onClick={() => focus(p)}
          title={p.mappingIds.length ? 'Click to open the mapping' : ''}
        >
          {p.message}
        </button>
      ))}
    </div>
  )
}
