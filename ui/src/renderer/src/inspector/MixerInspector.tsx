import type { CoordExpr } from '../../../shared/coords'
import type { Mapping, MixerMapping, Track } from '../../../shared/document'
import type { CellInfo } from '../../../shared/createMapping'
import { CoordWell } from './CoordWell'

interface Props {
  mapping: MixerMapping
  groups: CellInfo[]
  updateMapping(fn: (m: Mapping) => Mapping): void
  setBinding(well: string): (expr: CoordExpr | undefined) => void
}

export function MixerInspector({ mapping, groups, updateMapping, setBinding }: Props) {
  const setTrack = (track: Track) => updateMapping((m) => ({ ...m, track }) as Mapping)
  return (
    <div>
      <div className="coord-well">
        <span className="well-label">track</span>
        <select value={mapping.track} onChange={(e) => setTrack(e.target.value as Track)}>
          <option value="selected">selected</option>
          <option value="master">master</option>
        </select>
      </div>
      <CoordWell label="volume" expr={mapping.bindings.volume} accepts="encoder" groups={groups} onChange={setBinding('volume')} />
      <CoordWell label="pan" expr={mapping.bindings.pan} accepts="encoder" groups={groups} onChange={setBinding('pan')} />
      <CoordWell label="sends" expr={mapping.bindings.sends} accepts="encoder" groups={groups} onChange={setBinding('sends')} />
      <CoordWell label="mute" expr={mapping.bindings.mute} accepts="button" groups={groups} onChange={setBinding('mute')} refinable />
      <CoordWell label="solo" expr={mapping.bindings.solo} accepts="button" groups={groups} onChange={setBinding('solo')} refinable />
      <CoordWell label="arm" expr={mapping.bindings.arm} accepts="button" groups={groups} onChange={setBinding('arm')} refinable />
      <div className="palette-hint">sends: each selected knob becomes the next send (A, B, C…) in pick order.</div>
    </div>
  )
}
