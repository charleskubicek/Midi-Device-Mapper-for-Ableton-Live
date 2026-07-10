import { useCallback, useEffect, useState } from 'react'
import type { ControllerInfo } from '../../shared/protocol'
import { emptyDocument } from '../../shared/document'
import { serializeDocument } from '../../shared/serializer'
import { Canvas } from './canvas/Canvas'
import { Inspector } from './inspector/Inspector'
import { ModeTabs } from './modes/ModeTabs'
import { ProblemsPanel } from './panels/ProblemsPanel'
import { ConsoleDrawer, useConsoleStore } from './panels/ConsoleDrawer'
import { useValidation } from './hooks/useValidation'
import { useValidationStore } from './store/validationStore'
import { NewFileWizard, WizardResult } from './panels/NewFileWizard'
import { useDocumentStore } from './store/documentStore'
import { useUiStore } from './store/uiStore'

export default function App() {
  const [controller, setController] = useState<ControllerInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [sidecarStatus, setSidecarStatus] = useState<'running' | 'offline'>('offline')
  const [wizardOpen, setWizardOpen] = useState(false)

  const doc = useDocumentStore((s) => s.doc)
  const controllerAbsPath = useDocumentStore((s) => s.controllerAbsPath)
  const savedPath = useDocumentStore((s) => s.savedPath)
  const dirty = useDocumentStore((s) => s.dirty)
  const newDocument = useDocumentStore((s) => s.newDocument)
  const markSaved = useDocumentStore((s) => s.markSaved)
  const undo = useDocumentStore((s) => s.undo)
  const redo = useDocumentStore((s) => s.redo)

  useEffect(() => {
    window.api.sidecar.status().then(setSidecarStatus)
    const onStatus = (e: Event) => setSidecarStatus((e as CustomEvent).detail)
    window.addEventListener('sidecar-status', onStatus)
    return () => window.removeEventListener('sidecar-status', onStatus)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault()
        e.shiftKey ? redo() : undo()
      } else if (e.key === 'Escape') {
        useUiStore.getState().clearSelection()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [undo, redo])

  const loadControllerCanvas = useCallback(async (path: string) => {
    setError(null)
    try {
      const info = await window.api.sidecar.request<ControllerInfo>('load_controller', { path })
      setController(info)
      window.api.file.watchController(path).catch(() => {})
      return info
    } catch (e) {
      setController(null)
      setError((e as Error).message)
      return null
    }
  }, [])

  useValidation(controller)

  // Controller file changed on disk: reload the layout; orphaned coords show
  // up in the problems panel via the instant occupancy check.
  useEffect(() => {
    const onChanged = (e: Event) => {
      const path = (e as CustomEvent).detail as string
      loadControllerCanvas(path)
    }
    window.addEventListener('controller-changed', onChanged)
    return () => window.removeEventListener('controller-changed', onChanged)
  }, [loadControllerCanvas])

  // Dev/smoke hook: auto-open a document for MAPPING_EDITOR_CONTROLLER;
  // MAPPING_EDITOR_DEMO=1 additionally seeds example mappings.
  useEffect(() => {
    window.api.file.initialControllerPath().then(async (path) => {
      if (!path) return
      const load = async () => {
        const info = await loadControllerCanvas(path)
        if (!info) return
        newDocument(emptyDocument(path.split('/').pop()!, '/Applications'), path)
        if (await window.api.file.demoMode()) {
          const { createMapping } = await import('../../shared/createMapping')
          const { cellInfos } = await import('./inspector/Inspector')
          const groups = cellInfos(info)
          const knobs = groups.filter((g) => g.type === 'knob')
          const buttons = groups.filter((g) => g.type === 'button')
          useDocumentStore.getState().update((doc) => {
            if (knobs[0]) {
              doc.modes[0].mappings.push(
                createMapping(
                  'device',
                  Array.from({ length: knobs[0].control_count }, (_, i) => ({ group: knobs[0].number, index: i + 1 })),
                  groups
                )
              )
            }
            if (buttons[0]) {
              doc.modes[0].mappings.push(
                createMapping('mixer', [{ group: buttons[0].number, index: 1 }, { group: buttons[0].number, index: 2 }], groups),
                createMapping('transport', [{ group: buttons[0].number, index: 5 }, { group: buttons[0].number, index: 6 }], groups)
              )
              doc.modeless = false
              doc.modes[0].name = 'main_mode'
              doc.modes.push({
                name: 'shift_mode',
                mappings: [
                  createMapping('device-nav', [{ group: buttons[0].number, index: 9 }, { group: buttons[0].number, index: 10 }], groups)
                ]
              })
              doc.modeButton = {
                button: { atoms: [{ form: 'grid-cell', group: buttons[0].number, gridRow: 4, from: 4, to: 4 }], refinements: [] },
                type: 'shift'
              }
            }
            return doc
          })
        }
      }
      load().catch(() => setTimeout(load, 1000))
    })
  }, [loadControllerCanvas, newDocument])

  const onWizardCreate = useCallback(
    async (result: WizardResult) => {
      setWizardOpen(false)
      const info = await loadControllerCanvas(result.controllerAbsPath)
      if (!info) return
      const doc = emptyDocument(result.controllerAbsPath.split('/').pop()!, result.abletonDir)
      doc.hud = result.hud
      doc.showHudOn = result.showHudOn
      newDocument(doc, result.controllerAbsPath)
    },
    [loadControllerCanvas, newDocument]
  )

  const save = useCallback(async () => {
    const state = useDocumentStore.getState()
    if (!state.doc || !state.controllerAbsPath) return
    let target = state.savedPath
    if (!target) {
      const stem = state.controllerAbsPath.split('/').pop()!.replace(/\.nt$/, '').replace(/^controller_?/, '')
      const suggested = `ck_${stem || 'mapping'}.nt`
      target = await window.api.file.saveMappingDialog(suggested)
      if (!target) return
    }
    const targetDir = await window.api.file.dirname(target)
    const relController = await window.api.file.relativePath(targetDir, state.controllerAbsPath)
    const text = serializeDocument({ ...state.doc, controllerPath: relController })
    await window.api.file.writeText(target, text)
    markSaved(target)
    setNotice(`Saved ${target}`)
    setTimeout(() => setNotice(null), 4000)
  }, [markSaved])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        save()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [save])

  const validationStatus = useValidationStore((s) => s.status)
  const canGenerate = !!savedPath && !dirty && validationStatus === 'valid'

  const generate = useCallback(async () => {
    if (!savedPath) return
    const console = useConsoleStore.getState()
    console.show('generate', `Generating from ${savedPath}…\n`)
    try {
      const result = await window.api.sidecar.request<{ output: string }>('generate', {
        mapping_path: savedPath
      })
      console.append(result.output + '\n✓ done\n')
    } catch (e) {
      console.append(`✗ ${(e as Error).message}\n`)
    }
  }, [savedPath])

  const deploy = useCallback(async () => {
    if (!savedPath) return
    const surfaceDir = savedPath.replace(/\.nt$/, '')
    const console = useConsoleStore.getState()
    console.show('deploy', `Running deploy.sh in ${surfaceDir}…\n`)
    const result = await window.api.file.runScript(surfaceDir, 'deploy.sh')
    console.append(result.output + (result.code === 0 ? '\n✓ deployed — restart Ableton Live to load it\n' : `\n✗ exit ${result.code}\n`))
  }, [savedPath])

  return (
    <div className="app">
      <div className="toolbar">
        <button onClick={() => setWizardOpen(true)}>New mapping…</button>
        <button onClick={save} disabled={!doc}>
          Save{dirty ? ' •' : ''}
        </button>
        <button
          onClick={generate}
          disabled={!canGenerate}
          title={
            canGenerate
              ? 'Generate the control surface scripts'
              : !savedPath
                ? 'Save the mapping first'
                : dirty
                  ? 'Save your changes first'
                  : 'Fix validation problems first'
          }
        >
          Generate
        </button>
        <button onClick={deploy} disabled={!savedPath} title="Run the generated surface's deploy.sh">
          Deploy
        </button>
        {savedPath && <span title={savedPath}>{savedPath.split('/').pop()}</span>}
        {controllerAbsPath && (
          <span className="muted" title={controllerAbsPath}>
            controller: {controllerAbsPath.split('/').pop()}
          </span>
        )}
        {notice && <span className="notice">{notice}</span>}
        <span className={`status-pill ${sidecarStatus === 'offline' ? 'offline' : ''}`}>
          engine {sidecarStatus}
        </span>
      </div>
      {controller && doc && <ModeTabs controller={controller} />}
      <div className="main-split">
        <div className="workspace">
          {error && <div className="canvas-error">{error}</div>}
          {!error && controller && doc && <Canvas controller={controller} />}
          {!error && !controller && (
            <div className="empty-hint">New mapping… to start from a controller .nt file.</div>
          )}
        </div>
        {controller && doc && <Inspector controller={controller} />}
      </div>
      {controller && doc && <ProblemsPanel controller={controller} />}
      <ConsoleDrawer />
      {wizardOpen && <NewFileWizard onCreate={onWizardCreate} onCancel={() => setWizardOpen(false)} />}
    </div>
  )
}
