import { create } from 'zustand'

interface ConsoleState {
  title: string | null
  output: string
  open: boolean
  show(title: string, output: string): void
  append(text: string): void
  close(): void
}

export const useConsoleStore = create<ConsoleState>((set, get) => ({
  title: null,
  output: '',
  open: false,
  show: (title, output) => set({ title, output, open: true }),
  append: (text) => set({ output: get().output + text }),
  close: () => set({ open: false })
}))

export function ConsoleDrawer() {
  const { title, output, open, close } = useConsoleStore()
  if (!open) return null
  return (
    <div className="console-drawer">
      <div className="console-header">
        <b>{title}</b>
        <button onClick={close}>✕</button>
      </div>
      <pre>{output}</pre>
    </div>
  )
}
