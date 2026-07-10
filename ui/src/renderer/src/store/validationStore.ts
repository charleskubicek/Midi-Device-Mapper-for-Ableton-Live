import { create } from 'zustand'

export interface UiProblem {
  message: string
  kind: string
  /** correlated mapping ids (may be empty) */
  mappingIds: string[]
  /** 'engine' = from build_validated_model; 'instant' = TS pre-validation */
  source: 'engine' | 'instant'
}

interface ValidationState {
  status: 'idle' | 'validating' | 'valid' | 'invalid' | 'offline'
  engineProblems: UiProblem[]
  setResult(status: ValidationState['status'], problems: UiProblem[]): void
}

export const useValidationStore = create<ValidationState>((set) => ({
  status: 'idle',
  engineProblems: [],
  setResult: (status, engineProblems) => set({ status, engineProblems })
}))
