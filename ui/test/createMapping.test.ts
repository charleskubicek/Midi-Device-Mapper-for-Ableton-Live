import { describe, expect, it } from 'vitest'
import { createMapping, CellInfo } from '../src/shared/createMapping'
import { printCoordExpr } from '../src/shared/coords'
import type { DeviceMapping, MixerMapping, TransportMapping, PagerMapping } from '../src/shared/document'

const GROUPS: CellInfo[] = [
  { number: 1, control_count: 16, columns: 4, rows: 4, type: 'button' },
  { number: 2, control_count: 16, columns: 4, rows: 4, type: 'knob' }
]

const knobs = (...i: number[]) => i.map((index) => ({ group: 2, index }))
const buttons = (...i: number[]) => i.map((index) => ({ group: 1, index }))

describe('createMapping prefill', () => {
  it('device splits selection into encoders and buttons with 1-N slots', () => {
    const m = createMapping('device', [...knobs(1, 2, 3, 4), ...buttons(1, 2)], GROUPS) as DeviceMapping
    expect(m.track).toBe('selected')
    expect(printCoordExpr(m.encoders!.range)).toBe('grid-2:1::1-4')
    expect(m.encoders!.slots).toBe('1-4')
    expect(m.encoders!.parameters).toBeUndefined()
    expect(printCoordExpr(m.button!.range)).toBe('grid-1:1::1-2')
    expect(m.button!.slots).toBe('1-2')
  })

  it('mixer: one knob → volume, several knobs → sends, buttons → mute/solo/arm', () => {
    const single = createMapping('mixer', knobs(3), GROUPS) as MixerMapping
    expect(printCoordExpr(single.bindings.volume!)).toBe('grid-2:1::3')
    const multi = createMapping('mixer', [...knobs(5, 6, 7), ...buttons(1, 2)], GROUPS) as MixerMapping
    expect(printCoordExpr(multi.bindings.sends!)).toBe('grid-2:2::1-3')
    expect(printCoordExpr(multi.bindings.mute!)).toBe('grid-1:1::1')
    expect(printCoordExpr(multi.bindings.solo!)).toBe('grid-1:1::2')
    expect(multi.bindings.arm).toBeUndefined()
  })

  it('transport fills actions in pick order', () => {
    const m = createMapping('transport', buttons(5, 6), GROUPS) as TransportMapping
    expect(printCoordExpr(m.bindings['play-stop']!)).toBe('grid-1:2::1')
    expect(printCoordExpr(m.bindings['record-session']!)).toBe('grid-1:2::2')
    expect(m.bindings.loop).toBeUndefined()
  })

  it('pager: first pick is dec, second is inc; kind picks encoders vs buttons', () => {
    const enc = createMapping('parameter-pager', knobs(1, 2), GROUPS) as PagerMapping
    expect(printCoordExpr(enc.encoders!.dec)).toBe('grid-2:1::1')
    expect(printCoordExpr(enc.encoders!.inc)).toBe('grid-2:1::2')
    expect(enc.buttons).toBeUndefined()
    const btn = createMapping('parameter-pager', buttons(1, 2), GROUPS) as PagerMapping
    expect(btn.buttons).toBeDefined()
    expect(btn.encoders).toBeUndefined()
  })
})
