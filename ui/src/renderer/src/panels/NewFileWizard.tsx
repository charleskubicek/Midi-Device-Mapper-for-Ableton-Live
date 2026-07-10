import { useEffect, useState } from 'react'
import type { HudMode, HudTrigger } from '../../../shared/document'

export interface WizardResult {
  controllerAbsPath: string
  abletonDir: string
  hud: HudMode
  showHudOn: HudTrigger
}

interface Props {
  onCreate(result: WizardResult): void
  onCancel(): void
}

export function NewFileWizard({ onCreate, onCancel }: Props) {
  const [controllerPath, setControllerPath] = useState<string | null>(null)
  const [abletonDirs, setAbletonDirs] = useState<string[]>([])
  const [abletonDir, setAbletonDir] = useState('')
  const [abletonDirMissing, setAbletonDirMissing] = useState(false)
  const [hud, setHud] = useState<HudMode>('on')
  const [showHudOn, setShowHudOn] = useState<HudTrigger>('selection')

  useEffect(() => {
    window.api.file.findAbletonDirs().then((dirs) => {
      setAbletonDirs(dirs)
      if (dirs.length > 0) setAbletonDir(dirs[dirs.length - 1])
      else setAbletonDirMissing(true)
    })
  }, [])

  const pickController = async () => {
    const path = await window.api.file.openControllerDialog()
    if (path) setControllerPath(path)
  }

  const ready = controllerPath && abletonDir.trim()

  return (
    <div className="wizard-backdrop">
      <div className="wizard">
        <h2>New mapping</h2>

        <label>Controller file</label>
        <div className="wizard-row">
          <button onClick={pickController}>Choose…</button>
          <span className="wizard-path">{controllerPath ?? 'none selected'}</span>
        </div>

        <label>Ableton app</label>
        <div className="wizard-row">
          {abletonDirs.length > 0 ? (
            <select value={abletonDir} onChange={(e) => setAbletonDir(e.target.value)}>
              {abletonDirs.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={abletonDir}
              placeholder="/Applications/Ableton Live 12 Suite.app"
              onChange={(e) => setAbletonDir(e.target.value)}
            />
          )}
        </div>
        {abletonDirMissing && (
          <div className="wizard-warning">
            No Ableton app found in /Applications — enter the path manually (it may live on
            another machine; generation checks it, editing does not).
          </div>
        )}

        <label>HUD</label>
        <div className="wizard-row">
          <select value={hud} onChange={(e) => setHud(e.target.value as HudMode)}>
            <option value="on">on — every mapped cell shows its label</option>
            <option value="device_only">device_only — only focused device params</option>
            <option value="off">off — HUD disabled</option>
          </select>
        </div>

        <label>Show HUD on</label>
        <div className="wizard-row">
          <select value={showHudOn} onChange={(e) => setShowHudOn(e.target.value as HudTrigger)}>
            <option value="selection">selection — follow Live&apos;s selected device</option>
            <option value="controller-nav">controller-nav — only controller nav shows it</option>
          </select>
        </div>

        <div className="wizard-actions">
          <button onClick={onCancel}>Cancel</button>
          <button
            className="primary"
            disabled={!ready}
            onClick={() =>
              onCreate({ controllerAbsPath: controllerPath!, abletonDir: abletonDir.trim(), hud, showHudOn })
            }
          >
            Create
          </button>
        </div>
      </div>
    </div>
  )
}
