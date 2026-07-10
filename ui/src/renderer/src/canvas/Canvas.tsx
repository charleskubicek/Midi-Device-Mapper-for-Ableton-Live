import { useMemo, useRef, useState } from 'react'
import type { ControllerInfo } from '../../../shared/protocol'
import { cellKey, Cell, cellsOf } from '../../../shared/coordBuilder'
import { computeOccupancy } from '../../../shared/occupancy'
import { TYPE_SPEC_BY_TYPE } from '../../../shared/wellSpec'
import { useDocumentStore } from '../store/documentStore'
import { useUiStore } from '../store/uiStore'
import { ControlGlyph } from './ControlGlyph'
import { layoutController, cellAtPoint, cellsInRect, Rect, PAD } from './geometry'

interface Props {
  controller: ControllerInfo
}

const DRAG_THRESHOLD = 4

export function Canvas({ controller }: Props) {
  const doc = useDocumentStore((s) => s.doc)
  const activeModeIndex = useUiStore((s) => s.activeModeIndex)
  const showGhosts = useUiStore((s) => s.showGhosts)
  const modeIndex = doc ? Math.min(activeModeIndex, doc.modes.length - 1) : 0
  const mappings = useMemo(() => doc?.modes[modeIndex]?.mappings ?? [], [doc, modeIndex])
  const layout = useMemo(() => layoutController(controller.groups), [controller])
  const occupancy = useMemo(
    () => computeOccupancy(mappings, controller.groups),
    [mappings, controller]
  )
  const ghostKeys = useMemo(() => {
    if (!doc || !showGhosts) return new Set<string>()
    const others = doc.modes.filter((_, i) => i !== modeIndex).flatMap((m) => m.mappings)
    const { claims } = computeOccupancy(others, controller.groups)
    return new Set(claims.keys())
  }, [doc, modeIndex, showGhosts, controller])
  const modeButtonKeys = useMemo(() => {
    if (!doc?.modeButton) return new Set<string>()
    try {
      return new Set(cellsOf(doc.modeButton.button, controller.groups).map(cellKey))
    } catch {
      return new Set<string>()
    }
  }, [doc, controller])
  const selection = useUiStore((s) => s.selection)
  const selectedMappingId = useUiStore((s) => s.selectedMappingId)
  const { setSelection, addToSelection, toggleCell, selectMapping } = useUiStore()

  const svgRef = useRef<SVGSVGElement>(null)
  const dragStart = useRef<{ x: number; y: number; additive: boolean } | null>(null)
  const [marquee, setMarquee] = useState<Rect | null>(null)

  const selectedKeys = useMemo(() => new Set(selection.map(cellKey)), [selection])

  const toLocal = (e: React.PointerEvent): { x: number; y: number } => {
    const box = svgRef.current!.getBoundingClientRect()
    return { x: e.clientX - box.left, y: e.clientY - box.top }
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return
    const { x, y } = toLocal(e)
    dragStart.current = { x, y, additive: e.metaKey || e.ctrlKey }
    svgRef.current!.setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragStart.current) return
    const { x, y } = toLocal(e)
    const s = dragStart.current
    if (marquee || Math.abs(x - s.x) > DRAG_THRESHOLD || Math.abs(y - s.y) > DRAG_THRESHOLD) {
      setMarquee({
        x: Math.min(s.x, x),
        y: Math.min(s.y, y),
        w: Math.abs(x - s.x),
        h: Math.abs(y - s.y)
      })
    }
  }

  const onPointerUp = (e: React.PointerEvent) => {
    const start = dragStart.current
    dragStart.current = null
    if (!start) return
    if (marquee) {
      const cells = cellsInRect(layout, marquee)
      setMarquee(null)
      if (cells.length) {
        start.additive ? addToSelection(cells) : setSelection(cells)
      }
      return
    }
    const { x, y } = toLocal(e)
    const cell = cellAtPoint(layout, x, y)
    if (!cell) {
      // click on empty canvas or a group header
      const headerGroup = layout.groups.find(
        (pg) =>
          x >= pg.rect.x && x < pg.rect.x + pg.rect.w && y >= pg.rect.y && y < pg.rect.y + PAD + 10
      )
      if (headerGroup) setSelection(headerGroup.cells.map((pc) => pc.cell))
      else useUiStore.getState().clearSelection()
      return
    }
    if (e.metaKey || e.ctrlKey) {
      toggleCell(cell)
      return
    }
    if (e.shiftKey && selection.length > 0) {
      const last = selection[selection.length - 1]
      if (last.group === cell.group) {
        const step = cell.index >= last.index ? 1 : -1
        const extension: Cell[] = []
        for (let i = last.index + step; step > 0 ? i <= cell.index : i >= cell.index; i += step) {
          extension.push({ group: cell.group, index: i })
        }
        addToSelection(extension)
        return
      }
    }
    const claims = occupancy.claims.get(cellKey(cell))
    if (claims && claims.length > 0) selectMapping(claims[0].mappingId)
    else setSelection([cell])
  }

  return (
    <svg
      ref={svgRef}
      width={layout.width}
      height={layout.height}
      role="img"
      aria-label="Controller layout"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      {layout.groups.map((pg) => (
        <g key={pg.group.number}>
          <rect className="group-card" {...pg.rect} width={pg.rect.w} height={pg.rect.h} rx={8} />
          <text className="group-label" x={pg.rect.x + PAD} y={pg.rect.y + 14}>
            {pg.axis}-{pg.group.number} · {pg.group.type}
            {pg.group.hud ? '' : ' · no hud'}
          </text>
          {pg.cells.map((pc) => {
            const key = cellKey(pc.cell)
            const claims = occupancy.claims.get(key) ?? []
            const isClash = claims.length > 1
            const spec = claims[0] ? TYPE_SPEC_BY_TYPE[claims[0].mappingType] : null
            const isSelected = selectedKeys.has(key)
            const inSelectedMapping =
              selectedMappingId != null && claims.some((c) => c.mappingId === selectedMappingId)
            const coord =
              pg.axis === 'grid'
                ? `grid-${pg.group.number}:${Math.floor((pc.cell.index - 1) / pg.cols) + 1}::${((pc.cell.index - 1) % pg.cols) + 1}`
                : `row-${pg.group.number}:${pc.cell.index}`
            const midi = `ch ${pg.group.midi_channel} ${pg.group.midi_type} ${pg.group.midi_numbers[pc.cell.index - 1]}`
            const title = claims.length
              ? `${coord} — ${midi}\n${claims.map((c) => `${c.mappingType} · ${c.well}`).join('\n')}`
              : `${coord} — ${midi}`
            return (
              <g key={key}>
                <ControlGlyph type={pg.group.type} x={pc.rect.x} y={pc.rect.y} title={title} />
                {ghostKeys.has(key) && !spec && (
                  <rect
                    x={pc.rect.x + 7}
                    y={pc.rect.y + pc.rect.h - 9}
                    width={pc.rect.w - 14}
                    height={3}
                    rx={1.5}
                    fill="#5a6272"
                    opacity={0.6}
                  />
                )}
                {modeButtonKeys.has(key) && (
                  <rect
                    className="cell-ring mode-button"
                    x={pc.rect.x + 2}
                    y={pc.rect.y + 2}
                    width={pc.rect.w - 4}
                    height={pc.rect.h - 4}
                    rx={7}
                  />
                )}
                {spec && (
                  <>
                    <rect
                      x={pc.rect.x + 7}
                      y={pc.rect.y + pc.rect.h - 9}
                      width={pc.rect.w - 14}
                      height={3}
                      rx={1.5}
                      fill={spec.color}
                    />
                    <text
                      x={pc.rect.x + pc.rect.w / 2}
                      y={pc.rect.y + 16}
                      textAnchor="middle"
                      fontSize={8}
                      fill={spec.color}
                      pointerEvents="none"
                    >
                      {spec.glyph}
                    </text>
                  </>
                )}
                {(isSelected || inSelectedMapping || isClash) && (
                  <rect
                    className={
                      isClash ? 'cell-ring clash' : isSelected ? 'cell-ring selected' : 'cell-ring mapping'
                    }
                    x={pc.rect.x + 2}
                    y={pc.rect.y + 2}
                    width={pc.rect.w - 4}
                    height={pc.rect.h - 4}
                    rx={7}
                  />
                )}
              </g>
            )
          })}
        </g>
      ))}
      {marquee && <rect className="marquee" {...marquee} width={marquee.w} height={marquee.h} />}
    </svg>
  )
}
