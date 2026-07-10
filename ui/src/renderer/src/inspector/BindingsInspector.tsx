import type { CoordExpr } from '../../../shared/coords'
import type { CellInfo } from '../../../shared/createMapping'
import type { Accepts } from '../../../shared/wellSpec'
import { CoordWell } from './CoordWell'

interface BindingsMapping {
  bindings: Partial<Record<string, CoordExpr>>
}

interface Props {
  mapping: BindingsMapping
  groups: CellInfo[]
  wells: readonly string[]
  accepts: Accepts
  setBinding(well: string): (expr: CoordExpr | undefined) => void
}

/** Generic inspector for fixed-well mapping types (transport, track/device nav). */
export function BindingsInspector({ mapping, groups, wells, accepts, setBinding }: Props) {
  return (
    <div>
      {wells.map((well) => (
        <CoordWell
          key={well}
          label={well}
          expr={mapping.bindings[well]}
          accepts={accepts}
          groups={groups}
          onChange={setBinding(well)}
          refinable={accepts === 'button'}
        />
      ))}
    </div>
  )
}
