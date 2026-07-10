import { useState } from 'react'
import type { ControllerInfo } from '../../../shared/protocol'
import type { ModeButtonType } from '../../../shared/document'
import { printCoordExpr } from '../../../shared/coords'
import { selectionToExpr } from '../../../shared/coordBuilder'
import { cellInfos } from '../inspector/Inspector'
import { useDocumentStore } from '../store/documentStore'
import { useUiStore } from '../store/uiStore'

export function ModeTabs({ controller }: { controller: ControllerInfo }) {
  const doc = useDocumentStore((s) => s.doc)
  const update = useDocumentStore((s) => s.update)
  const activeModeIndex = useUiStore((s) => s.activeModeIndex)
  const setActiveMode = useUiStore((s) => s.setActiveMode)
  const selection = useUiStore((s) => s.selection)
  const showGhosts = useUiStore((s) => s.showGhosts)
  const toggleGhosts = useUiStore((s) => s.toggleGhosts)
  const [renaming, setRenaming] = useState<number | null>(null)
  const [renameText, setRenameText] = useState('')

  if (!doc) return null
  const groups = cellInfos(controller)
  const modeIndex = Math.min(activeModeIndex, doc.modes.length - 1)
  const activeMode = doc.modes[modeIndex]

  const addMode = () => {
    update((d) => {
      if (d.modeless) d.modeless = false
      d.modes.push({ name: `mode_${d.modes.length + 1}`, mappings: [] })
      return d
    })
    setActiveMode(doc.modes.length)
  }

  const deleteMode = (index: number) => {
    const mode = doc.modes[index]
    const n = mode.mappings.length
    if (!window.confirm(`Delete mode '${mode.name}'${n ? ` and its ${n} mapping(s)` : ''}?`)) return
    update((d) => {
      d.modes.splice(index, 1)
      if (d.modes.length === 1) {
        d.modeless = true
        delete d.modeButton
      }
      return d
    })
    setActiveMode(Math.max(0, index - 1))
  }

  const commitRename = (index: number) => {
    const name = renameText.trim()
    setRenaming(null)
    if (!name || name === doc.modes[index].name) return
    if (doc.modes.some((m, i) => i !== index && m.name === name)) {
      window.alert(`A mode named '${name}' already exists.`)
      return
    }
    update((d) => {
      d.modes[index].name = name
      return d
    })
  }

  const setOnColor = (color: string) => {
    update((d) => {
      if (color) d.modes[modeIndex].onColor = color
      else delete d.modes[modeIndex].onColor
      return d
    })
  }

  const setModeButtonFromSelection = () => {
    const cell = selection[0]
    const group = groups.find((g) => g.number === cell.group)
    if (group?.type !== 'button') {
      window.alert('The mode button must be a button control.')
      return
    }
    update((d) => {
      d.modeButton = {
        button: selectionToExpr([cell], groups),
        type: d.modeButton?.type ?? 'switch'
      }
      return d
    })
  }

  const setModeButtonType = (type: ModeButtonType) => {
    update((d) => {
      if (d.modeButton) d.modeButton.type = type
      return d
    })
  }

  const lightColors = Object.keys(controller.light_colors)
  const shiftWarning =
    doc.modeButton?.type === 'shift' && doc.modes.length > 2
      ? 'shift is a two-mode (hold) behavior — use switch for 3+ modes'
      : null

  return (
    <div className="mode-bar">
      <div className="mode-tabs">
        {doc.modes.map((mode, i) => (
          <div
            key={i}
            className={`mode-tab ${i === modeIndex ? 'active' : ''}`}
            onClick={() => setActiveMode(i)}
            onDoubleClick={() => {
              setRenaming(i)
              setRenameText(mode.name)
            }}
            title="Double-click to rename"
          >
            {renaming === i ? (
              <input
                autoFocus
                value={renameText}
                onChange={(e) => setRenameText(e.target.value)}
                onBlur={() => commitRename(i)}
                onKeyDown={(e) => e.key === 'Enter' && commitRename(i)}
              />
            ) : (
              <>
                {doc.modeless ? 'mappings' : mode.name}
                <span className="mode-count">{mode.mappings.length}</span>
                {!doc.modeless && doc.modes.length > 1 && (
                  <span
                    className="mode-close"
                    title="Delete mode"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteMode(i)
                    }}
                  >
                    ×
                  </span>
                )}
              </>
            )}
          </div>
        ))}
        <button className="mode-add" onClick={addMode} title={doc.modeless ? 'Convert to modes and add a second mode' : 'Add mode'}>
          +
        </button>
      </div>
      {!doc.modeless && (
        <div className="mode-settings">
          <span className="well-label">mode button</span>
          <code>{doc.modeButton ? printCoordExpr(doc.modeButton.button) : 'not set'}</code>
          <button
            disabled={selection.length !== 1}
            title={selection.length === 1 ? 'Use the selected button' : 'Select exactly one button on the canvas'}
            onClick={setModeButtonFromSelection}
          >
            ⇐ sel
          </button>
          {doc.modeButton && (
            <select
              value={doc.modeButton.type}
              onChange={(e) => setModeButtonType(e.target.value as ModeButtonType)}
              title="shift: second mode while held · switch: each press cycles modes"
            >
              <option value="switch">switch (cycle)</option>
              <option value="shift">shift (hold)</option>
            </select>
          )}
          <span className="well-label">on color</span>
          <select value={activeMode.onColor ?? ''} onChange={(e) => setOnColor(e.target.value)}>
            <option value="">(none)</option>
            {lightColors.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <label className="well-flag">
            <input type="checkbox" checked={showGhosts} onChange={toggleGhosts} /> show other modes
          </label>
          {shiftWarning && <span className="mode-warning">{shiftWarning}</span>}
        </div>
      )}
    </div>
  )
}
