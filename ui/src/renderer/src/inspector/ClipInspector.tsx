import type { CoordExpr } from '../../../shared/coords'
import type { ClipMapping, Mapping } from '../../../shared/document'
import type { CellInfo } from '../../../shared/createMapping'
import { selectionToExpr } from '../../../shared/coordBuilder'
import { kindMatches } from '../../../shared/wellSpec'
import { useSchemaInfo, ClipAction } from '../hooks/useSchemaInfo'
import { useUiStore } from '../store/uiStore'
import { CoordWell } from './CoordWell'

interface Props {
  mapping: ClipMapping
  groups: CellInfo[]
  updateMapping(fn: (m: Mapping) => Mapping): void
}

const KIND_LABELS: Record<ClipAction['kind'], string> = {
  encoder: 'encoders (absolute)',
  nudge: 'nudge encoders (turn = step)',
  button: 'buttons'
}

export function ClipInspector({ mapping, groups, updateMapping }: Props) {
  const schema = useSchemaInfo()
  const selection = useUiStore((s) => s.selection)

  if (!schema) return <div className="palette-hint">Loading clip actions… (engine required)</div>

  const setBinding = (key: string) => (expr: CoordExpr | undefined) =>
    updateMapping((m) => {
      const cm = m as ClipMapping
      if (expr === undefined) delete cm.bindings[key]
      else cm.bindings[key] = expr
      return cm
    })

  const fillFromSelection = () => {
    const byNumber = new Map(groups.map((g) => [g.number, g]))
    updateMapping((m) => {
      const cm = m as ClipMapping
      let cursor = 0
      for (const action of schema.clip_actions) {
        if (cursor >= selection.length) break
        if (cm.bindings[action.key]) continue
        const accepts = action.kind === 'button' ? 'button' : 'encoder'
        const cell = selection[cursor]
        if (!kindMatches(accepts, byNumber.get(cell.group)!.type)) continue
        cm.bindings[action.key] = selectionToExpr([cell], groups)
        cursor += 1
      }
      return cm
    })
  }

  const kinds: ClipAction['kind'][] = ['encoder', 'nudge', 'button']
  return (
    <div>
      <button className="small" disabled={selection.length === 0} onClick={fillFromSelection}>
        fill unassigned from selection ({selection.length})
      </button>
      {kinds.map((kind) => (
        <div key={kind} className="device-section">
          <div className="well-label">{KIND_LABELS[kind]}</div>
          {schema.clip_actions
            .filter((a) => a.kind === kind)
            .map((action) => (
              <CoordWell
                key={action.key}
                label={action.key}
                expr={mapping.bindings[action.key]}
                accepts={kind === 'button' ? 'button' : 'encoder'}
                groups={groups}
                onChange={setBinding(action.key)}
                refinable={kind === 'button'}
              />
            ))}
        </div>
      ))}
      <div className="palette-hint">Audio-clip-only actions (gain, pitch, warp) no-op on MIDI clips.</div>
    </div>
  )
}
