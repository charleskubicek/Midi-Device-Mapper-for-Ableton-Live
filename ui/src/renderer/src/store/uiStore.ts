import { create } from 'zustand'
import type { Cell } from '../../../shared/coordBuilder'
import { dedupeSelection } from '../../../shared/coordBuilder'

interface UiState {
  /** ordered — pick order drives slot/action assignment */
  selection: Cell[]
  selectedMappingId: string | null
  activeModeIndex: number
  /** overlay other modes' occupancy on the canvas */
  showGhosts: boolean
  toggleGhosts(): void

  setSelection(cells: Cell[]): void
  addToSelection(cells: Cell[]): void
  toggleCell(cell: Cell): void
  clearSelection(): void
  selectMapping(id: string | null): void
  setActiveMode(index: number): void
}

export const useUiStore = create<UiState>((set, get) => ({
  selection: [],
  selectedMappingId: null,
  activeModeIndex: 0,
  showGhosts: true,
  toggleGhosts: () => set({ showGhosts: !get().showGhosts }),

  setSelection: (cells) => set({ selection: dedupeSelection(cells), selectedMappingId: null }),
  addToSelection: (cells) => set({ selection: dedupeSelection([...get().selection, ...cells]) }),
  toggleCell: (cell) => {
    const { selection } = get()
    const key = `${cell.group}:${cell.index}`
    const without = selection.filter((c) => `${c.group}:${c.index}` !== key)
    set({ selection: without.length === selection.length ? [...selection, cell] : without })
  },
  clearSelection: () => set({ selection: [], selectedMappingId: null }),
  selectMapping: (id) => set({ selectedMappingId: id, ...(id ? { selection: [] } : {}) }),
  setActiveMode: (index) => set({ activeModeIndex: index, selectedMappingId: null, selection: [] })
}))
