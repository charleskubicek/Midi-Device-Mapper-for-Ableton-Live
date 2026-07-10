import { useEffect, useState } from 'react'

export interface ClipAction {
  key: string
  kind: 'encoder' | 'nudge' | 'button'
  label: string
  audio_only: boolean
}

export interface SchemaInfo {
  clip_actions: ClipAction[]
  transport_actions: string[]
  track_nav_actions: string[]
  device_nav_actions: string[]
  builtin_functions: string[]
}

let cached: Promise<SchemaInfo> | null = null

export function useSchemaInfo(): SchemaInfo | null {
  const [info, setInfo] = useState<SchemaInfo | null>(null)
  useEffect(() => {
    cached ??= window.api.sidecar.request<SchemaInfo>('schema_info')
    cached.then(setInfo).catch(() => {
      cached = null // retry next mount (sidecar may have been offline)
    })
  }, [])
  return info
}
