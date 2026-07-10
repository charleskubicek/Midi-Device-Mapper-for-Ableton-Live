// Which control kinds each mapping type / inspector well accepts, and when a
// mapping type is offered for a canvas selection. Single source of truth for
// palette enablement, pick-mode cell dimming, and TS pre-validation.

import type { MappingType } from './document'

export type ControlKind = 'knob' | 'button' | 'slider'
export type Accepts = 'button' | 'encoder' | 'any'

export function kindMatches(accepts: Accepts, kind: ControlKind): boolean {
  if (accepts === 'any') return true
  if (accepts === 'button') return kind === 'button'
  return kind === 'knob' || kind === 'slider'
}

export interface TypeSpec {
  type: MappingType
  label: string
  /** short badge glyph on mapped canvas cells */
  glyph: string
  /** badge color (stable per type) */
  color: string
  /** can this type be created from this selection? null = enabled */
  disabledReason(kinds: ControlKind[]): string | null
}

const allButtons = (kinds: ControlKind[]): string | null =>
  kinds.every((k) => k === 'button') ? null : 'needs buttons only'

const nonEmpty = (kinds: ControlKind[]): string | null =>
  kinds.length > 0 ? null : 'select some controls first'

export const TYPE_SPECS: TypeSpec[] = [
  {
    type: 'device',
    label: 'Device',
    glyph: 'D',
    color: '#4cc2ff',
    disabledReason: nonEmpty
  },
  {
    type: 'mixer',
    label: 'Mixer',
    glyph: 'Mx',
    color: '#8bd450',
    disabledReason: nonEmpty
  },
  {
    type: 'transport',
    label: 'Transport',
    glyph: 'T',
    color: '#e0b34c',
    disabledReason: allButtons
  },
  {
    type: 'track-nav',
    label: 'Track nav',
    glyph: 'Tn',
    color: '#d478d4',
    disabledReason: (k) => allButtons(k) ?? (k.length <= 2 ? null : 'takes at most 2 buttons (left/right)')
  },
  {
    type: 'device-nav',
    label: 'Device nav',
    glyph: 'Dn',
    color: '#7d8cf0',
    disabledReason: (k) => allButtons(k) ?? (k.length <= 5 ? null : 'takes at most 5 buttons')
  },
  {
    type: 'functions',
    label: 'Functions',
    glyph: 'Fn',
    color: '#f08d7d',
    disabledReason: allButtons
  },
  {
    type: 'parameter-pager',
    label: 'Param pager',
    glyph: 'Pg',
    color: '#5ad4c0',
    disabledReason: (k) =>
      k.length === 2 && k[0] === k[1] ? null : 'takes exactly 2 controls of the same kind (dec/inc)'
  },
  {
    type: 'clip',
    label: 'Clip',
    glyph: 'Cl',
    color: '#c9a2f0',
    disabledReason: nonEmpty
  }
]

export const TYPE_SPEC_BY_TYPE: Record<string, TypeSpec> = Object.fromEntries(
  TYPE_SPECS.map((s) => [s.type, s])
)
