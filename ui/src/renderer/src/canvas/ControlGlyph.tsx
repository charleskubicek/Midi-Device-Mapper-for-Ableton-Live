import { CELL } from './geometry'

interface Props {
  type: 'knob' | 'button' | 'slider'
  x: number
  y: number
  title: string
}

const INSET = 6

export function ControlGlyph({ type, x, y, title }: Props) {
  const size = CELL - INSET * 2
  const cx = x + CELL / 2
  const cy = y + CELL / 2
  let shape
  if (type === 'knob') {
    const r = size / 2
    shape = (
      <>
        <circle className="glyph-knob" cx={cx} cy={cy} r={r} />
        <line className="glyph-knob-tick" x1={cx} y1={cy} x2={cx} y2={cy - r + 3} />
      </>
    )
  } else if (type === 'button') {
    shape = <rect className="glyph-button" x={x + INSET} y={y + INSET} width={size} height={size} rx={5} />
  } else {
    shape = (
      <rect className="glyph-slider" x={cx - size / 5} y={y + INSET / 2} width={(size * 2) / 5} height={CELL - INSET} rx={4} />
    )
  }
  return (
    <g>
      <title>{title}</title>
      {shape}
    </g>
  )
}
