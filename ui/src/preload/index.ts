import { contextBridge, ipcRenderer } from 'electron'
import type { RendererApi } from '../shared/protocol'

const api: RendererApi = {
  sidecar: {
    request: (method, params = {}) => ipcRenderer.invoke('sidecar:request', method, params),
    status: () => ipcRenderer.invoke('sidecar:status')
  },
  file: {
    openControllerDialog: () => ipcRenderer.invoke('file:openControllerDialog'),
    initialControllerPath: () => ipcRenderer.invoke('file:initialControllerPath'),
    demoMode: () => ipcRenderer.invoke('file:demoMode'),
    saveMappingDialog: (defaultName) => ipcRenderer.invoke('file:saveMappingDialog', defaultName),
    writeText: (path, text) => ipcRenderer.invoke('file:writeText', path, text),
    relativePath: (fromDir, toFile) => ipcRenderer.invoke('file:relativePath', fromDir, toFile),
    dirname: (path) => ipcRenderer.invoke('file:dirname', path),
    findAbletonDirs: () => ipcRenderer.invoke('file:findAbletonDirs'),
    watchController: (path) => ipcRenderer.invoke('file:watchController', path),
    runScript: (cwd, script) => ipcRenderer.invoke('file:runScript', cwd, script),
    exists: (path) => ipcRenderer.invoke('file:exists', path)
  }
}

contextBridge.exposeInMainWorld('api', api)
ipcRenderer.on('sidecar:status', (_event, status) => {
  window.dispatchEvent(new CustomEvent('sidecar-status', { detail: status }))
})
ipcRenderer.on('controller:changed', (_event, path) => {
  window.dispatchEvent(new CustomEvent('controller-changed', { detail: path }))
})
