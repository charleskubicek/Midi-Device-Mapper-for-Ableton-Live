// The in-memory mapping document — the TS mirror of model_v2.RootV2's input
// schema. Serialized to NestedText by serializer.ts; ids are UI-only identity
// (never serialized).

import type { CoordExpr } from './coords'

export type Track = 'selected' | 'master'
export type DeviceTarget = 'selected' | { name: string }

/** One encoder/button range with exactly one of parameters|slots (device). */
export interface RangeMap {
  range: CoordExpr
  /** e.g. '1-16' — device parameter indices */
  parameters?: string
  /** e.g. '1-8', '5-16', or literal switch slots for buttons */
  slots?: string
}

export interface DeviceMapping {
  id: string
  type: 'device'
  track: Track
  device: DeviceTarget
  encoders?: RangeMap
  encoderList?: RangeMap[]
  button?: RangeMap
  buttonList?: RangeMap[]
  onOff?: CoordExpr
}

export const MIXER_FUNCTIONS = ['volume', 'pan', 'mute', 'solo', 'arm', 'sends'] as const
export type MixerFunction = (typeof MIXER_FUNCTIONS)[number]

export interface MixerMapping {
  id: string
  type: 'mixer'
  track: Track
  bindings: Partial<Record<MixerFunction, CoordExpr>>
}

export const TRANSPORT_ACTIONS = [
  'play-stop',
  'record-session',
  'record-arrangement',
  'loop',
  'midi-arrange-overdub'
] as const
export type TransportAction = (typeof TRANSPORT_ACTIONS)[number]

export interface TransportMapping {
  id: string
  type: 'transport'
  bindings: Partial<Record<TransportAction, CoordExpr>>
}

export const TRACK_NAV_ACTIONS = ['left', 'right'] as const
export interface TrackNavMapping {
  id: string
  type: 'track-nav'
  bindings: Partial<Record<(typeof TRACK_NAV_ACTIONS)[number], CoordExpr>>
}

export const DEVICE_NAV_ACTIONS = ['left', 'right', 'first', 'last', 'first-last'] as const
export interface DeviceNavMapping {
  id: string
  type: 'device-nav'
  bindings: Partial<Record<(typeof DEVICE_NAV_ACTIONS)[number], CoordExpr>>
}

export const BUILTIN_FUNCTIONS = ['hud_toggle'] as const
export interface FunctionsMapping {
  id: string
  type: 'functions'
  /** function name (from functions.py, or a builtin) → coord */
  bindings: Record<string, CoordExpr>
}

export interface IncDec {
  inc: CoordExpr
  dec: CoordExpr
}
export interface PagerMapping {
  id: string
  type: 'parameter-pager'
  encoders?: IncDec
  buttons?: IncDec
}

export interface ClipMapping {
  id: string
  type: 'clip'
  /** clip action key (model_clip.CLIP_ACTIONS) → coord */
  bindings: Record<string, CoordExpr>
}

export type Mapping =
  | DeviceMapping
  | MixerMapping
  | TransportMapping
  | TrackNavMapping
  | DeviceNavMapping
  | FunctionsMapping
  | PagerMapping
  | ClipMapping

export type MappingType = Mapping['type']

export interface Mode {
  name: string
  onColor?: string
  mappings: Mapping[]
}

export type HudMode = 'on' | 'device_only' | 'off'
export type HudTrigger = 'selection' | 'controller-nav'
export type ModeButtonType = 'shift' | 'switch'

export interface ModeButton {
  button: CoordExpr
  type: ModeButtonType
}

export interface MappingDocument {
  /** relative to the document's directory */
  controllerPath: string
  abletonDir: string
  hud: HudMode
  showHudOn: HudTrigger
  parameterMappingsFile?: string
  remoteOn?: boolean
  modeButton?: ModeButton
  /** true = flat `mappings:`; modes must then hold exactly one Mode whose name is ignored */
  modeless: boolean
  modes: Mode[]
}

export function emptyDocument(controllerPath: string, abletonDir: string): MappingDocument {
  return {
    controllerPath,
    abletonDir,
    hud: 'on',
    showHudOn: 'selection',
    modeless: true,
    modes: [{ name: 'main_mode', mappings: [] }]
  }
}
