import type { ControllerInfo } from '../../../shared/protocol'
import type { Mapping } from '../../../shared/document'
import type { CoordExpr } from '../../../shared/coords'
import type { CellInfo } from '../../../shared/createMapping'
import { createMapping } from '../../../shared/createMapping'
import { printCoordExpr } from '../../../shared/coords'
import { selectionToExpr } from '../../../shared/coordBuilder'
import { TYPE_SPECS, TYPE_SPEC_BY_TYPE, ControlKind } from '../../../shared/wellSpec'
import { useDocumentStore } from '../store/documentStore'
import { useUiStore } from '../store/uiStore'
import { MixerInspector } from './MixerInspector'
import { BindingsInspector } from './BindingsInspector'
import { FunctionsInspector } from './FunctionsInspector'
import { DeviceInspector } from './DeviceInspector'
import { PagerInspector } from './PagerInspector'
import { ClipInspector } from './ClipInspector'
import { TRANSPORT_ACTIONS, TRACK_NAV_ACTIONS, DEVICE_NAV_ACTIONS } from '../../../shared/document'

interface Props {
  controller: ControllerInfo
}

export function cellInfos(controller: ControllerInfo): CellInfo[] {
  return controller.groups.map((g) => ({
    number: g.number,
    control_count: g.control_count,
    columns: g.columns,
    rows: g.rows,
    type: g.type
  }))
}

function TypePalette({ controller }: Props) {
  const selection = useUiStore((s) => s.selection)
  const activeModeIndex = useUiStore((s) => s.activeModeIndex)
  const selectMapping = useUiStore((s) => s.selectMapping)
  const update = useDocumentStore((s) => s.update)
  const groups = cellInfos(controller)
  const byNumber = new Map(groups.map((g) => [g.number, g]))
  const kinds: ControlKind[] = selection.map((c) => byNumber.get(c.group)!.type)

  let coordPreview = ''
  try {
    coordPreview = printCoordExpr(selectionToExpr(selection, groups))
  } catch {
    coordPreview = '(unresolvable)'
  }

  const apply = (type: Mapping['type']) => {
    const mapping = createMapping(type, selection, groups)
    update((doc) => {
      doc.modes[activeModeIndex].mappings.push(mapping)
      return doc
    })
    selectMapping(mapping.id)
  }

  return (
    <div className="palette">
      <div className="inspector-header">
        {selection.length} selected · <code>{coordPreview}</code>
      </div>
      <div className="palette-hint">Map this selection to:</div>
      {TYPE_SPECS.map((spec) => {
        const reason = spec.disabledReason(kinds)
        return (
          <button
            key={spec.type}
            className="palette-type"
            disabled={reason != null}
            title={reason ?? ''}
            style={{ borderLeftColor: spec.color }}
            onClick={() => apply(spec.type)}
          >
            <b>{spec.label}</b>
            {reason && <span className="palette-reason"> — {reason}</span>}
          </button>
        )
      })}
    </div>
  )
}

function MappingEditor({ controller, mapping }: Props & { mapping: Mapping }) {
  const activeModeIndex = useUiStore((s) => s.activeModeIndex)
  const selectMapping = useUiStore((s) => s.selectMapping)
  const update = useDocumentStore((s) => s.update)
  const groups = cellInfos(controller)

  const updateMapping = (fn: (m: Mapping) => Mapping) =>
    update((doc) => {
      const mode = doc.modes[activeModeIndex]
      mode.mappings = mode.mappings.map((m) => (m.id === mapping.id ? fn(structuredClone(m)) : m))
      return doc
    })

  const remove = () => {
    update((doc) => {
      const mode = doc.modes[activeModeIndex]
      mode.mappings = mode.mappings.filter((m) => m.id !== mapping.id)
      return doc
    })
    selectMapping(null)
  }

  const spec = TYPE_SPEC_BY_TYPE[mapping.type]
  const setBinding = (well: string) => (expr: CoordExpr | undefined) =>
    updateMapping((m) => {
      const bindings = (m as { bindings: Record<string, CoordExpr | undefined> }).bindings
      if (expr === undefined) delete bindings[well]
      else bindings[well] = expr
      return m
    })

  let body
  switch (mapping.type) {
    case 'mixer':
      body = <MixerInspector mapping={mapping} groups={groups} updateMapping={updateMapping} setBinding={setBinding} />
      break
    case 'transport':
      body = (
        <BindingsInspector mapping={mapping} groups={groups} wells={TRANSPORT_ACTIONS} accepts="button" setBinding={setBinding} />
      )
      break
    case 'track-nav':
      body = (
        <BindingsInspector mapping={mapping} groups={groups} wells={TRACK_NAV_ACTIONS} accepts="button" setBinding={setBinding} />
      )
      break
    case 'device-nav':
      body = (
        <BindingsInspector mapping={mapping} groups={groups} wells={DEVICE_NAV_ACTIONS} accepts="button" setBinding={setBinding} />
      )
      break
    case 'functions':
      body = <FunctionsInspector mapping={mapping} groups={groups} updateMapping={updateMapping} />
      break
    case 'device':
      body = <DeviceInspector mapping={mapping} groups={groups} updateMapping={updateMapping} />
      break
    case 'parameter-pager':
      body = <PagerInspector mapping={mapping} groups={groups} updateMapping={updateMapping} />
      break
    case 'clip':
      body = <ClipInspector mapping={mapping} groups={groups} updateMapping={updateMapping} />
      break
  }

  return (
    <div className="mapping-editor">
      <div className="inspector-header">
        <span className="type-chip" style={{ background: spec.color }}>
          {spec.glyph}
        </span>
        <b>{spec.label}</b>
        <button className="danger" onClick={remove} title="Delete this mapping">
          delete
        </button>
      </div>
      {body}
    </div>
  )
}

export function Inspector({ controller }: Props) {
  const doc = useDocumentStore((s) => s.doc)
  const selection = useUiStore((s) => s.selection)
  const selectedMappingId = useUiStore((s) => s.selectedMappingId)
  const activeModeIndex = useUiStore((s) => s.activeModeIndex)
  const selectMapping = useUiStore((s) => s.selectMapping)

  if (!doc) return null
  const mode = doc.modes[activeModeIndex]
  const selectedMapping = mode.mappings.find((m) => m.id === selectedMappingId)

  return (
    <div className="inspector">
      {selectedMapping ? (
        <MappingEditor controller={controller} mapping={selectedMapping} />
      ) : selection.length > 0 ? (
        <TypePalette controller={controller} />
      ) : (
        <div className="palette-hint">
          Select controls on the canvas to create a mapping, or click a mapped control to edit it.
        </div>
      )}
      {mode.mappings.length > 0 && (
        <div className="mapping-list">
          <div className="well-label">mappings in this mode</div>
          {mode.mappings.map((m) => {
            const spec = TYPE_SPEC_BY_TYPE[m.type]
            return (
              <button
                key={m.id}
                className={`mapping-row ${m.id === selectedMappingId ? 'active' : ''}`}
                onClick={() => selectMapping(m.id)}
              >
                <span className="type-chip" style={{ background: spec.color }}>
                  {spec.glyph}
                </span>
                {spec.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
