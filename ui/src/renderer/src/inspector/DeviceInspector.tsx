import { cellCount } from '../../../shared/coords'
import type { DeviceMapping, Mapping, RangeMap, Track } from '../../../shared/document'
import type { CellInfo } from '../../../shared/createMapping'
import { CoordWell } from './CoordWell'

interface Props {
  mapping: DeviceMapping
  groups: CellInfo[]
  updateMapping(fn: (m: Mapping) => Mapping): void
}

/** '1-16' → 16, '1,3,5' → 3, 'attack, decay' → 2 */
export function specCount(spec: string | undefined): number | null {
  if (!spec?.trim()) return null
  const m = /^(\d+)\s*-\s*(\d+)$/.exec(spec.trim())
  if (m) return Number(m[2]) - Number(m[1]) + 1
  return spec.split(',').filter((s) => s.trim()).length
}

type RangeKind = 'encoders' | 'buttons'

/** device encoders/button + their -list variants, normalized to one array */
function rangesOf(m: DeviceMapping, kind: RangeKind): RangeMap[] {
  if (kind === 'encoders') return [...(m.encoders ? [m.encoders] : []), ...(m.encoderList ?? [])]
  return [...(m.button ? [m.button] : []), ...(m.buttonList ?? [])]
}

function writeRanges(m: DeviceMapping, kind: RangeKind, ranges: RangeMap[]): void {
  if (kind === 'encoders') {
    delete m.encoders
    delete m.encoderList
    if (ranges.length === 1) m.encoders = ranges[0]
    else if (ranges.length > 1) m.encoderList = ranges
  } else {
    delete m.button
    delete m.buttonList
    if (ranges.length === 1) m.button = ranges[0]
    else if (ranges.length > 1) m.buttonList = ranges
  }
}

export function DeviceInspector({ mapping, groups, updateMapping }: Props) {
  const setTrack = (track: Track) => updateMapping((m) => ({ ...m, track }) as Mapping)
  const setDevice = (device: DeviceMapping['device']) =>
    updateMapping((m) => ({ ...m, device }) as Mapping)

  const updateRange = (kind: RangeKind, index: number, fn: (rm: RangeMap) => RangeMap | null) =>
    updateMapping((m) => {
      const dm = m as DeviceMapping
      const ranges = rangesOf(dm, kind)
      const next = fn(ranges[index])
      if (next === null) ranges.splice(index, 1)
      else ranges[index] = next
      writeRanges(dm, kind, ranges)
      return dm
    })

  const addRange = (kind: RangeKind) =>
    updateMapping((m) => {
      const dm = m as DeviceMapping
      const ranges = rangesOf(dm, kind)
      ranges.push({ range: { atoms: [], refinements: [] }, slots: '' })
      writeRanges(dm, kind, ranges)
      return dm
    })

  const named = mapping.device !== 'selected'

  return (
    <div>
      <div className="coord-well">
        <span className="well-label">track</span>
        <select value={mapping.track} onChange={(e) => setTrack(e.target.value as Track)}>
          <option value="selected">selected</option>
          <option value="master">master</option>
        </select>
      </div>
      <div className="coord-well">
        <span className="well-label">device</span>
        <select
          value={named ? 'named' : 'selected'}
          onChange={(e) => setDevice(e.target.value === 'selected' ? 'selected' : { name: '' })}
        >
          <option value="selected">selected</option>
          <option value="named">named…</option>
        </select>
        {named && (
          <input
            value={(mapping.device as { name: string }).name}
            placeholder="device name"
            onChange={(e) => setDevice({ name: e.target.value })}
          />
        )}
      </div>

      {(['encoders', 'buttons'] as const).map((kind) => {
        const ranges = rangesOf(mapping, kind)
        return (
          <div key={kind} className="device-section">
            <div className="well-label">{kind}</div>
            {ranges.map((rm, i) => (
              <RangeEditor
                key={i}
                kind={kind}
                rm={rm}
                groups={groups}
                onChange={(next) => updateRange(kind, i, () => next)}
              />
            ))}
            <button className="small" onClick={() => addRange(kind)}>
              + add {kind === 'encoders' ? 'encoder' : 'button'} range
            </button>
          </div>
        )
      })}

      <div className="device-section">
        <CoordWell
          label="on-off"
          expr={mapping.onOff}
          accepts="button"
          groups={groups}
          onChange={(expr) =>
            updateMapping((m) => {
              const dm = m as DeviceMapping
              if (expr === undefined) delete dm.onOff
              else dm.onOff = expr
              return dm
            })
          }
        />
      </div>
    </div>
  )
}

function RangeEditor({
  kind,
  rm,
  groups,
  onChange
}: {
  kind: RangeKind
  rm: RangeMap
  groups: CellInfo[]
  onChange(next: RangeMap | null): void
}) {
  const usesParameters = rm.parameters !== undefined
  const controls = rm.range.atoms.length ? cellCount(rm.range) : 0
  const targets = specCount(usesParameters ? rm.parameters : rm.slots)
  const mismatch = controls > 0 && targets != null && controls !== targets

  return (
    <div className="range-editor">
      <CoordWell
        label="range"
        expr={rm.range.atoms.length ? rm.range : undefined}
        accepts={kind === 'encoders' ? 'encoder' : 'button'}
        groups={groups}
        onChange={(expr) => {
          if (expr === undefined) onChange(null)
          else onChange({ ...rm, range: expr })
        }}
      />
      <div className="coord-well">
        {kind === 'encoders' ? (
          <>
            <span className="well-label">
              <label title="Device parameter indices (bypasses slot layout)">
                <input
                  type="radio"
                  checked={usesParameters}
                  onChange={() => onChange({ range: rm.range, parameters: rm.slots ?? '1-8' })}
                />{' '}
                params
              </label>
              <label title="HUD slot numbers or slot names">
                <input
                  type="radio"
                  checked={!usesParameters}
                  onChange={() => onChange({ range: rm.range, slots: rm.parameters ?? '1-8' })}
                />{' '}
                slots
              </label>
            </span>
            <input
              value={usesParameters ? rm.parameters : rm.slots}
              placeholder={usesParameters ? 'e.g. 1-16' : 'e.g. 1-8 or names'}
              onChange={(e) =>
                onChange(
                  usesParameters
                    ? { range: rm.range, parameters: e.target.value }
                    : { range: rm.range, slots: e.target.value }
                )
              }
            />
          </>
        ) : (
          <>
            <span className="well-label">slots</span>
            <input
              value={rm.slots ?? ''}
              placeholder="e.g. 1-8, 5-16, or switch1"
              onChange={(e) => onChange({ range: rm.range, slots: e.target.value })}
            />
          </>
        )}
        <span className={`count-badge ${mismatch ? 'bad' : ''}`} title="controls ↔ slots/params">
          {controls} ↔ {targets ?? '?'} {mismatch ? '✗' : controls > 0 && targets != null ? '✓' : ''}
        </span>
      </div>
    </div>
  )
}
