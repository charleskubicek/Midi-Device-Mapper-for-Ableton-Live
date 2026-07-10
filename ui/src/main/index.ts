import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'node:path'
import { SidecarManager } from './sidecar'

const sidecar = new SidecarManager()

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'Mapping Editor',
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })
  sidecar.onStatusChange = (status) => {
    if (!win.isDestroyed()) win.webContents.send('sidecar:status', status)
  }
  if (process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    win.loadFile(path.join(__dirname, '../renderer/index.html'))
  }
  const screenshotPath = process.env.MAPPING_EDITOR_SCREENSHOT
  if (screenshotPath) {
    win.webContents.on('did-finish-load', () => {
      setTimeout(async () => {
        const image = await win.webContents.capturePage()
        const { writeFileSync } = await import('node:fs')
        writeFileSync(screenshotPath, image.toPNG())
        app.quit()
      }, 2000)
    })
  }
  return win
}

ipcMain.handle('sidecar:request', (_event, method: string, params: Record<string, unknown>) =>
  sidecar.request(method, params)
)
ipcMain.handle('sidecar:status', () => sidecar.status())
// Dev/smoke hooks: MAPPING_EDITOR_CONTROLLER auto-loads a controller file on
// launch; MAPPING_EDITOR_SCREENSHOT captures the window to that path and quits.
ipcMain.handle('file:initialControllerPath', () => process.env.MAPPING_EDITOR_CONTROLLER ?? null)
ipcMain.handle('file:demoMode', () => process.env.MAPPING_EDITOR_DEMO === '1')
ipcMain.handle('file:openControllerDialog', async () => {
  const result = await dialog.showOpenDialog({
    title: 'Open controller file',
    filters: [{ name: 'NestedText', extensions: ['nt'] }],
    properties: ['openFile']
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle('file:saveMappingDialog', async (_event, defaultName: string) => {
  const result = await dialog.showSaveDialog({
    title: 'Save mapping file',
    defaultPath: defaultName,
    filters: [{ name: 'NestedText', extensions: ['nt'] }]
  })
  return result.canceled ? null : result.filePath
})
ipcMain.handle('file:writeText', async (_event, filePath: string, text: string) => {
  const { mkdirSync, writeFileSync } = await import('node:fs')
  mkdirSync(path.dirname(filePath), { recursive: true })
  writeFileSync(filePath, text)
})
ipcMain.handle('file:relativePath', (_event, fromDir: string, toFile: string) =>
  path.relative(fromDir, toFile) || path.basename(toFile)
)
ipcMain.handle('file:dirname', (_event, p: string) => path.dirname(p))
ipcMain.handle('file:findAbletonDirs', async () => {
  const { readdirSync } = await import('node:fs')
  try {
    return readdirSync('/Applications')
      .filter((name) => name.startsWith('Ableton') && name.endsWith('.app'))
      .map((name) => `/Applications/${name}`)
  } catch {
    return []
  }
})

ipcMain.handle('file:runScript', async (_event, cwd: string, script: string) => {
  const { spawn } = await import('node:child_process')
  const { existsSync } = await import('node:fs')
  const scriptPath = path.join(cwd, script)
  if (!existsSync(scriptPath)) {
    return { code: -1, output: `${scriptPath} does not exist — generate the surface first.` }
  }
  return new Promise((resolve) => {
    const proc = spawn('bash', [script], { cwd })
    let output = ''
    proc.stdout.on('data', (d: Buffer) => (output += d.toString()))
    proc.stderr.on('data', (d: Buffer) => (output += d.toString()))
    proc.on('close', (code) => resolve({ code: code ?? -1, output }))
  })
})
ipcMain.handle('file:exists', async (_event, p: string) => {
  const { existsSync } = await import('node:fs')
  return existsSync(p)
})

let controllerWatcher: import('node:fs').FSWatcher | null = null
ipcMain.handle('file:watchController', async (event, filePath: string) => {
  const { watch } = await import('node:fs')
  controllerWatcher?.close()
  controllerWatcher = watch(filePath, { persistent: false }, () => {
    // Editors often replace the file; debounce bursts of events.
    setTimeout(() => event.sender.send('controller:changed', filePath), 150)
  })
})

app.whenReady().then(() => {
  sidecar.start()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  sidecar.stop()
  app.quit()
})
