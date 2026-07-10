import { create } from 'zustand'
import type { MappingDocument } from '../../../shared/document'

interface DocumentState {
  /** current document, or null before New/Open */
  doc: MappingDocument | null
  /** absolute path of the controller file backing doc.controllerPath */
  controllerAbsPath: string | null
  /** absolute path the mapping was last saved to (null = never saved) */
  savedPath: string | null
  dirty: boolean
  undoStack: MappingDocument[]
  redoStack: MappingDocument[]

  newDocument(doc: MappingDocument, controllerAbsPath: string): void
  /** All document mutations go through here so undo/redo stays correct. */
  update(mutate: (doc: MappingDocument) => MappingDocument): void
  markSaved(path: string): void
  undo(): void
  redo(): void
}

const MAX_UNDO = 100

export const useDocumentStore = create<DocumentState>((set, get) => ({
  doc: null,
  controllerAbsPath: null,
  savedPath: null,
  dirty: false,
  undoStack: [],
  redoStack: [],

  newDocument: (doc, controllerAbsPath) =>
    set({ doc, controllerAbsPath, savedPath: null, dirty: false, undoStack: [], redoStack: [] }),

  update: (mutate) => {
    const { doc, undoStack } = get()
    if (!doc) return
    set({
      doc: mutate(structuredClone(doc)),
      dirty: true,
      undoStack: [...undoStack.slice(-MAX_UNDO), doc],
      redoStack: []
    })
  },

  markSaved: (path) => set({ savedPath: path, dirty: false }),

  undo: () => {
    const { doc, undoStack, redoStack } = get()
    if (!doc || undoStack.length === 0) return
    set({
      doc: undoStack[undoStack.length - 1],
      undoStack: undoStack.slice(0, -1),
      redoStack: [...redoStack, doc],
      dirty: true
    })
  },

  redo: () => {
    const { doc, undoStack, redoStack } = get()
    if (!doc || redoStack.length === 0) return
    set({
      doc: redoStack[redoStack.length - 1],
      redoStack: redoStack.slice(0, -1),
      undoStack: [...undoStack, doc],
      dirty: true
    })
  }
}))
