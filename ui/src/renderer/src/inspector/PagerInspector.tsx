import type { CoordExpr } from '../../../shared/coords'
import type { Mapping, PagerMapping } from '../../../shared/document'
import type { CellInfo } from '../../../shared/createMapping'
import { CoordWell } from './CoordWell'

interface Props {
  mapping: PagerMapping
  groups: CellInfo[]
  updateMapping(fn: (m: Mapping) => Mapping): void
}

export function PagerInspector({ mapping, groups, updateMapping }: Props) {
  const setPart =
    (part: 'encoders' | 'buttons', key: 'inc' | 'dec') => (expr: CoordExpr | undefined) =>
      updateMapping((m) => {
        const pm = m as PagerMapping
        const current = pm[part] ?? { inc: { atoms: [], refinements: [] }, dec: { atoms: [], refinements: [] } }
        if (expr === undefined) {
          const other = key === 'inc' ? 'dec' : 'inc'
          if (current[other].atoms.length === 0) delete pm[part]
          else pm[part] = { ...current, [key]: { atoms: [], refinements: [] } }
        } else {
          pm[part] = { ...current, [key]: expr }
        }
        return pm
      })

  const wellsFor = (part: 'encoders' | 'buttons') => {
    const pair = mapping[part]
    const accepts = part === 'buttons' ? 'button' : 'encoder'
    return (
      <div className="device-section" key={part}>
        <div className="well-label">{part} pager</div>
        <CoordWell
          label="dec"
          expr={pair?.dec.atoms.length ? pair.dec : undefined}
          accepts={accepts}
          groups={groups}
          onChange={setPart(part, 'dec')}
        />
        <CoordWell
          label="inc"
          expr={pair?.inc.atoms.length ? pair.inc : undefined}
          accepts={accepts}
          groups={groups}
          onChange={setPart(part, 'inc')}
        />
      </div>
    )
  }

  return (
    <div>
      {wellsFor('encoders')}
      {wellsFor('buttons')}
      <div className="palette-hint">Steps the visible parameter page of the focused device.</div>
    </div>
  )
}
