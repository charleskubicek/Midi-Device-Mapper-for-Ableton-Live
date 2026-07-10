import { spawn, spawnSync, ChildProcessWithoutNullStreams } from 'node:child_process'
import { createInterface } from 'node:readline'
import path from 'node:path'
import type { SidecarResponse } from '../shared/protocol'

// The repo root is one level above ui/. In dev, __dirname is ui/out/main.
export const REPO_ROOT = path.resolve(__dirname, '..', '..', '..')

const REQUEST_TIMEOUT_MS = 10_000
const GENERATE_TIMEOUT_MS = 120_000
const MAX_RESTARTS = 5

interface Pending {
  resolve: (value: unknown) => void
  reject: (err: Error) => void
  timer: NodeJS.Timeout
}

/** Resolve the poetry venv's python. Falls back to `python3` so the app still
 *  starts (with a visible sidecar error) when poetry isn't on PATH. */
function resolvePython(): string {
  const probe = spawnSync('poetry', ['env', 'info', '--path'], {
    cwd: REPO_ROOT,
    encoding: 'utf8'
  })
  const venv = probe.status === 0 ? probe.stdout.trim() : ''
  return venv ? path.join(venv, 'bin', 'python') : 'python3'
}

export class SidecarManager {
  private proc: ChildProcessWithoutNullStreams | null = null
  private pending = new Map<number, Pending>()
  private nextId = 1
  private restarts = 0
  private pythonPath: string | null = null
  onStatusChange: (status: 'running' | 'offline') => void = () => {}

  status(): 'running' | 'offline' {
    return this.proc ? 'running' : 'offline'
  }

  start(): void {
    if (this.proc) return
    this.pythonPath ??= resolvePython()
    const proc = spawn(this.pythonPath, ['-m', 'ableton_control_surface_as_code.ui_api'], {
      cwd: REPO_ROOT,
      env: { ...process.env, PYTHONPATH: REPO_ROOT, PYTHONUNBUFFERED: '1' }
    })
    this.proc = proc
    this.onStatusChange('running')

    createInterface({ input: proc.stdout }).on('line', (line) => this.onLine(line))
    proc.stderr.on('data', (chunk: Buffer) => {
      console.error('[sidecar]', chunk.toString().trimEnd())
    })
    proc.on('exit', (code) => {
      console.error(`[sidecar] exited with code ${code}`)
      this.proc = null
      this.onStatusChange('offline')
      this.rejectAll(new Error(`sidecar exited (code ${code})`))
      if (this.restarts < MAX_RESTARTS) {
        const delay = 500 * 2 ** this.restarts
        this.restarts += 1
        setTimeout(() => this.start(), delay)
      }
    })
    proc.on('spawn', () => {
      // A successful request resets the backoff counter (see onLine).
    })
  }

  stop(): void {
    const proc = this.proc
    this.proc = null
    this.restarts = MAX_RESTARTS // suppress restart on deliberate stop
    proc?.kill()
    this.rejectAll(new Error('sidecar stopped'))
  }

  request<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const proc = this.proc
    if (!proc) return Promise.reject(new Error('sidecar offline'))
    const id = this.nextId++
    const timeoutMs = method === 'generate' ? GENERATE_TIMEOUT_MS : REQUEST_TIMEOUT_MS
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`sidecar request ${method} timed out`))
      }, timeoutMs)
      this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject, timer })
      proc.stdin.write(JSON.stringify({ id, method, params }) + '\n')
    })
  }

  private onLine(line: string): void {
    let response: SidecarResponse
    try {
      response = JSON.parse(line)
    } catch {
      console.error('[sidecar] unparseable line:', line)
      return
    }
    if (response.id === null) return
    const pending = this.pending.get(response.id)
    if (!pending) return
    this.pending.delete(response.id)
    clearTimeout(pending.timer)
    this.restarts = 0
    if (response.ok) pending.resolve(response.result)
    else pending.reject(Object.assign(new Error(response.error.message), { sidecar: response.error }))
  }

  private rejectAll(err: Error): void {
    for (const { reject, timer } of this.pending.values()) {
      clearTimeout(timer)
      reject(err)
    }
    this.pending.clear()
  }
}
