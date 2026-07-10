import { useCallback, useEffect, useState } from 'react'
import type { CoordExpr } from '../../../shared/coords'
import type { FunctionsMapping, Mapping } from '../../../shared/document'
import { BUILTIN_FUNCTIONS } from '../../../shared/document'
import type { CellInfo } from '../../../shared/createMapping'
import { useDocumentStore } from '../store/documentStore'
import { CoordWell } from './CoordWell'

interface Props {
  mapping: FunctionsMapping
  groups: CellInfo[]
  updateMapping(fn: (m: Mapping) => Mapping): void
}

interface FnInfo {
  name: string
  params: number
}

export function FunctionsInspector({ mapping, groups, updateMapping }: Props) {
  const [newName, setNewName] = useState('')
  const savedPath = useDocumentStore((s) => s.savedPath)
  // undefined = not loaded yet; null = no functions.py next to the mapping
  const [available, setAvailable] = useState<FnInfo[] | null | undefined>(undefined)

  const savedDir = savedPath ? savedPath.slice(0, savedPath.lastIndexOf('/')) : null

  const refresh = useCallback(() => {
    if (!savedDir) return
    window.api.sidecar
      .request<{ functions: FnInfo[] | null }>('list_functions', { dir: savedDir })
      .then((r) => setAvailable(r.functions))
      .catch(() => setAvailable(undefined))
  }, [savedDir])

  useEffect(refresh, [refresh])

  const knownNames = new Set<string>([
    ...BUILTIN_FUNCTIONS,
    ...(available ?? []).map((f) => f.name)
  ])
  const unknownBound = Object.keys(mapping.bindings).filter((name) => !knownNames.has(name))

  const createStub = async () => {
    // Only when no functions.py exists — never overwrite a user's file.
    if (!savedDir || unknownBound.length === 0 || available !== null) return
    const body = unknownBound.map((name) => `    def ${name}(self):\n        pass\n`).join('\n')
    await window.api.file.writeText(
      `${savedDir}/functions.py`,
      `# Generated stub — implement these methods.\n\n\nclass Functions:\n${body}`
    )
    refresh()
  }

  const rename = (from: string, to: string) => {
    if (!to || to === from) return
    updateMapping((m) => {
      const fm = m as FunctionsMapping
      const bindings: Record<string, CoordExpr> = {}
      for (const [k, v] of Object.entries(fm.bindings)) bindings[k === from ? to : k] = v
      fm.bindings = bindings
      return fm
    })
  }

  const setExpr = (name: string) => (expr: CoordExpr | undefined) =>
    updateMapping((m) => {
      const fm = m as FunctionsMapping
      if (expr === undefined) delete fm.bindings[name]
      else fm.bindings[name] = expr
      return fm
    })

  const addRow = () => {
    const name = newName.trim()
    if (!name || mapping.bindings[name]) return
    setNewName('')
    updateMapping((m) => {
      const fm = m as FunctionsMapping
      fm.bindings[name] = { atoms: [], refinements: [] }
      return fm
    })
  }

  return (
    <div>
      {Object.entries(mapping.bindings).map(([name, expr]) => (
        <div key={name} className="function-row">
          <NameField name={name} onRename={(to) => rename(name, to)} />
          <CoordWell
            label=""
            expr={expr.atoms.length ? expr : undefined}
            accepts="button"
            groups={groups}
            onChange={setExpr(name)}
            refinable
          />
        </div>
      ))}
      <div className="coord-well">
        <input
          value={newName}
          placeholder="function name (from functions.py)"
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addRow()}
          list="builtin-functions"
        />
        <datalist id="builtin-functions">
          {[...knownNames].map((f) => (
            <option key={f} value={f} />
          ))}
        </datalist>
        <button onClick={addRow} disabled={!newName.trim()}>
          + add
        </button>
      </div>
      <div className="palette-hint">
        Names must match methods of the Functions class in a functions.py next to the mapping file
        (builtin: hud_toggle).
      </div>
      {savedDir && unknownBound.length > 0 && (
        <div className="well-error">
          Not in functions.py: {unknownBound.join(', ')}
          {available === null ? (
            <button className="small" onClick={createStub}>
              create functions.py stub
            </button>
          ) : (
            <span> — add these methods to the Functions class by hand.</span>
          )}
        </div>
      )}
      {!savedDir && (
        <div className="palette-hint">Save the mapping to check names against its functions.py.</div>
      )}
    </div>
  )
}

function NameField({ name, onRename }: { name: string; onRename(to: string): void }) {
  const [text, setText] = useState(name)
  return (
    <input
      className="function-name"
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => onRename(text.trim())}
      onKeyDown={(e) => e.key === 'Enter' && onRename(text.trim())}
    />
  )
}
