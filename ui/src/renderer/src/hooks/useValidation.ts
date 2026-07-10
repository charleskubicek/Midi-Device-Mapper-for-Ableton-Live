import { useEffect, useRef } from 'react'
import type { ControllerInfo, ValidateResult } from '../../../shared/protocol'
import { serializeDocument } from '../../../shared/serializer'
import { correlateProblem } from '../../../shared/correlate'
import { useDocumentStore } from '../store/documentStore'
import { useValidationStore } from '../store/validationStore'

const DEBOUNCE_MS = 400

/** Debounced document → sidecar build_validated_model → problems store. */
export function useValidation(controller: ControllerInfo | null): void {
  const doc = useDocumentStore((s) => s.doc)
  const controllerAbsPath = useDocumentStore((s) => s.controllerAbsPath)
  const setResult = useValidationStore((s) => s.setResult)
  const revision = useRef(0)

  useEffect(() => {
    if (!doc || !controllerAbsPath || !controller) return
    const rev = ++revision.current
    const timer = setTimeout(async () => {
      const slash = controllerAbsPath.lastIndexOf('/')
      const mappingDir = controllerAbsPath.slice(0, slash)
      const controllerName = controllerAbsPath.slice(slash + 1)
      const text = serializeDocument({ ...doc, controllerPath: controllerName })
      useValidationStore.setState({ status: 'validating' })
      try {
        const result = await window.api.sidecar.request<ValidateResult>('validate', {
          mapping_text: text,
          mapping_dir: mappingDir
        })
        if (revision.current !== rev) return // stale
        setResult(
          result.valid ? 'valid' : 'invalid',
          result.problems.map((p) => ({
            message: p.message,
            kind: p.kind,
            source: 'engine' as const,
            mappingIds: correlateProblem({
              message: p.message,
              modes: doc.modes,
              groups: controller.groups
            })
          }))
        )
      } catch {
        if (revision.current === rev) setResult('offline', [])
      }
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [doc, controllerAbsPath, controller, setResult])
}
