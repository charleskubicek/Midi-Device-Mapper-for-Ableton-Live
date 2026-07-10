import { describe, expect, it } from 'vitest'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { serializeDocument } from '../src/shared/serializer'
import { goldenDocs, minimalMixer } from './golden/docs'

const GOLDEN_DIR = path.join(__dirname, 'golden')

describe('serializeDocument', () => {
  it('serializes a modeless mixer document', () => {
    const text = serializeDocument(minimalMixer)
    expect(text).toBe(
      [
        'controller: controller.nt',
        'ableton_dir: /Applications/Ableton Live 12 Suite.app',
        'hud: off',
        'show-hud-on: selection',
        'mappings:',
        '    -',
        '        type: mixer',
        '        track: selected',
        '        mappings:',
        '            volume: grid-2:1',
        ''
      ].join('\n')
    )
  })

  it('never serializes UI-only ids', () => {
    for (const doc of Object.values(goldenDocs)) {
      expect(serializeDocument(doc)).not.toMatch(/\bid\b/)
    }
  })

  // Golden contract: expected files are committed; regenerate deliberately with
  // UPDATE_GOLDEN=1 npx vitest run. Python-side acceptance of these same files
  // lives in tests/test_ui_golden.py.
  for (const [file, doc] of Object.entries(goldenDocs)) {
    it(`matches golden ${file}`, () => {
      const target = path.join(GOLDEN_DIR, file)
      const text = serializeDocument(doc)
      if (process.env.UPDATE_GOLDEN || !existsSync(target)) {
        writeFileSync(target, text)
      }
      expect(text).toBe(readFileSync(target, 'utf8'))
    })
  }
})
