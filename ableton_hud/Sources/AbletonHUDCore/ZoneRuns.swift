import Foundation

/// A maximal run of contiguous cell slots that share the same zone colour.
/// `range` is in cell-local coordinates (`0..<cell.count`); `hex` is the shared
/// `RRGGBB` zone colour, or `nil` for an un-zoned run (no background painted).
public struct ZoneRun: Equatable {
    public let range: Range<Int>
    public let hex: String?

    public init(range: Range<Int>, hex: String?) {
        self.range = range
        self.hex = hex
    }
}

/// Partition a cell's `count` slots into contiguous runs of equal zone colour.
///
/// The wire delivers a per-slot colour map (`dialColors` / `buttonColors`) keyed
/// by *wire* index; a cell occupies wire indices `start ..< start+count`. Zones
/// are contiguous slot runs within a cell (env, global, signature, …) and
/// adjacent zones always differ in hue, so grouping equal-hex neighbours recovers
/// the zone areas exactly. `nil` hex (slot absent from the map) forms its own
/// un-zoned run. A non-zoned device has an empty map → one `nil` run spanning the
/// whole cell → the caller paints no background (pixel-identical to pre-zoning).
public func zoneRuns(count: Int, colors: [Int: String], start: Int) -> [ZoneRun] {
    guard count > 0 else { return [] }
    var runs: [ZoneRun] = []
    var runStart = 0
    var runHex = colors[start]
    for i in 1..<count {
        let hex = colors[start + i]
        if hex != runHex {
            runs.append(ZoneRun(range: runStart..<i, hex: runHex))
            runStart = i
            runHex = hex
        }
    }
    runs.append(ZoneRun(range: runStart..<count, hex: runHex))
    return runs
}
