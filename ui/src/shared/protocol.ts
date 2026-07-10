// Wire types shared between main, preload, and renderer.
// The Python side of this protocol is ableton_control_surface_as_code/ui_api.py.

export interface SidecarRequest {
  id: number
  method: string
  params: Record<string, unknown>
}

export interface SidecarError {
  kind: 'parse' | 'io' | 'config' | 'bad_request' | 'internal'
  message: string
  code?: string | null
}

export type SidecarResponse =
  | { id: number | null; ok: true; result: unknown }
  | { id: number | null; ok: false; error: SidecarError }

export interface Problem {
  message: string
  kind: string
  code: string | null
}

export interface ControlGroupInfo {
  number: number
  type: 'knob' | 'button' | 'slider'
  grid_row: number
  grid_col: number
  rows: number | null
  columns: number | null
  hud: boolean
  control_count: number
  midi_channel: number | null
  midi_type: 'CC' | 'note' | null
  midi_numbers: number[]
}

export interface ControllerInfo {
  light_colors: Record<string, number>
  button_behaviour: 'momentary' | 'toggle'
  encoder_mode: 'absolute' | 'relative'
  groups: ControlGroupInfo[]
  problems: Problem[]
}

export interface ValidateResult {
  valid: boolean
  problems: Problem[]
}

// API surface exposed to the renderer via contextBridge (preload/index.ts).
export interface RendererApi {
  sidecar: {
    request<T = unknown>(method: string, params?: Record<string, unknown>): Promise<T>
    status(): Promise<'running' | 'offline'>
  }
  file: {
    openControllerDialog(): Promise<string | null>
    initialControllerPath(): Promise<string | null>
    demoMode(): Promise<boolean>
    /** Save dialog for the mapping file; returns the chosen absolute path. */
    saveMappingDialog(defaultName: string): Promise<string | null>
    writeText(path: string, text: string): Promise<void>
    /** POSIX-relative path from a directory to a file (for `controller:`). */
    relativePath(fromDir: string, toFile: string): Promise<string>
    dirname(path: string): Promise<string>
    /** Ableton .app bundles found in /Applications. */
    findAbletonDirs(): Promise<string[]>
    /** watch the controller file; fires a 'controller-changed' window event */
    watchController(path: string): Promise<void>
    /** run a shell script (e.g. deploy.sh) with cwd; resolves when done */
    runScript(cwd: string, script: string): Promise<{ code: number; output: string }>
    exists(path: string): Promise<boolean>
  }
}
