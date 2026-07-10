// Golden documents. Each pairs with an expected .nt file in this directory;
// tests/test_ui_golden.py (Python) additionally asserts the generator accepts
// every golden .nt against controller.nt + functions.py in this directory.

import type { MappingDocument } from '../../src/shared/document'
import { parseCoordExpr as c } from '../../src/shared/coords'

export const minimalMixer: MappingDocument = {
  controllerPath: 'controller.nt',
  abletonDir: '/Applications/Ableton Live 12 Suite.app',
  hud: 'off',
  showHudOn: 'selection',
  modeless: true,
  modes: [
    {
      name: 'main_mode',
      mappings: [
        { id: 'm1', type: 'mixer', track: 'selected', bindings: { volume: c('grid-2:1') } }
      ]
    }
  ]
}

// Exercises every mapping type, modes + shift mode-button, encoder-list,
// button slots, on-off, sends multi-coord, and a refinement.
export const full: MappingDocument = {
  controllerPath: 'controller.nt',
  abletonDir: '/Applications/Ableton Live 12 Suite.app',
  remoteOn: false,
  hud: 'on',
  showHudOn: 'selection',
  modeButton: { button: c('grid-4:4::1'), type: 'shift' },
  modeless: false,
  modes: [
    {
      name: 'main_mode',
      onColor: 'red_low',
      mappings: [
        {
          id: 'd1',
          type: 'device',
          track: 'selected',
          device: 'selected',
          encoders: { range: c('grid-3:1-16'), slots: '1-16' },
          button: { range: c('grid-1:1-12'), slots: '1-12' },
          onOff: c('grid-1:4::1')
        },
        {
          id: 'x1',
          type: 'mixer',
          track: 'selected',
          bindings: { mute: c('grid-4:1'), solo: c('grid-4:2') }
        },
        {
          id: 'f1',
          type: 'functions',
          bindings: { iterate_midi_pattern: c('grid-4:1::4'), hud_toggle: c('grid-4:4::2') }
        },
        {
          id: 'dn1',
          type: 'device-nav',
          bindings: { left: c('grid-4:4::3'), right: c('grid-4:4::4') }
        },
        {
          id: 'tn1',
          type: 'track-nav',
          bindings: { left: c('grid-4:3::1'), right: c('grid-4:3::2') }
        },
        {
          id: 't1',
          type: 'transport',
          bindings: { 'play-stop': c('grid-4:3::3'), loop: c('grid-4:3::4') }
        },
        {
          id: 'c1',
          type: 'clip',
          bindings: {
            gain: c('grid-2:1'),
            'pitch-coarse': c('grid-2:2'),
            looping: c('grid-4:2::1'),
            warping: c('grid-4:2::2')
          }
        }
      ]
    },
    {
      name: 'shift_mode',
      onColor: 'green_full',
      mappings: [
        {
          id: 'x2',
          type: 'mixer',
          track: 'selected',
          bindings: {
            volume: c('grid-3:4'),
            pan: c('grid-3:3'),
            sends: c('grid-3:5-8,grid-3:9-12')
          }
        },
        {
          id: 'd2',
          type: 'device',
          track: 'selected',
          device: 'selected',
          encoderList: [
            { range: c('grid-2:1-8'), slots: '1-8' },
            { range: c('grid-2:9-16'), slots: '9-16' }
          ],
          buttonList: [{ range: c('grid-4:1-12'), slots: '5-16' }]
        },
        {
          id: 'f2',
          type: 'functions',
          bindings: { press_rack_random_button: c('grid-4:4::2 momentary') }
        },
        {
          id: 'p2',
          type: 'parameter-pager',
          encoders: { inc: c('grid-4:4::4'), dec: c('grid-4:4::3') }
        }
      ]
    }
  ]
}

export const goldenDocs: Record<string, MappingDocument> = {
  'minimal_mixer.nt': minimalMixer,
  'full.nt': full
}
