import Foundation

public struct Slot: Equatable {
    public let name: String
    public let value: Float
    public let min: Float
    public let max: Float
    /// Optional SF Symbol name rendered *inside* a button cell ("" = none).
    public let glyph: String

    public init(name: String, value: Float, min: Float, max: Float, glyph: String = "") {
        self.name = name
        self.value = value
        self.min = min
        self.max = max
        self.glyph = glyph
    }
}

public enum SlotKind: String, Equatable {
    case dial
    case button
}

public struct HudCell: Equatable {
    public let gridRow: Int
    public let gridCol: Int
    public let kind: SlotKind
    public let count: Int
    public let startIndex: Int
    /// Independent-layout group. A standalone surface emits everything as
    /// section 0; the lc_parks compositor tags the secondary controller section
    /// 1 so the HUD renders it as a separate block to the right of the primary
    /// (each section is its own sub-grid). Slot indices stay in one flat space.
    public let section: Int
    public init(gridRow: Int, gridCol: Int, kind: SlotKind, count: Int,
                startIndex: Int, section: Int = 0) {
        self.gridRow = gridRow; self.gridCol = gridCol; self.kind = kind
        self.count = count; self.startIndex = startIndex; self.section = section
    }
}

/// One zone-colour tint on the wire: which slot (kind + wire index) gets which
/// RRGGBB hue. See grid-zone-colour-coding-plan.
public struct ZoneTint: Equatable {
    public let kind: SlotKind
    public let index: Int
    public let hex: String
    public init(kind: SlotKind, index: Int, hex: String) {
        self.kind = kind; self.index = index; self.hex = hex
    }
}

public enum WireMessage: Equatable {
    case layout([HudCell])
    case device(String)
    case slot(SlotKind, Int, Slot)
    /// Immediate single-slot update — no burst, no COMMIT needed.
    case update(SlotKind, Int, Slot)
    case commit(Int)
/// Keepalive — resets the HUD dismiss timer without changing display state.
    case ping
    /// Explicit dismiss — the user navigated away from the device in Live.
    /// Hides the HUD and stays hidden until a new device burst arrives.
    case hide
    case mode(isShift: Bool)
    case page(encPage: Int, encTotal: Int, btnPage: Int, btnTotal: Int,
              encLabel: String, btnLabel: String)
    /// Show-info feedback: a transient, human-readable explanation of a button
    /// press, rendered + faded on the HUD. `wireIdx` is the HUD button-array
    /// index (-1 when the press isn't tied to a cell). `text` may contain '|'.
    case event(kind: String, wireIdx: Int, text: String)
    /// Per-burst zone tints for dial/button outlines. Empty array = clear (a
    /// non-zoned device focus). Keyed by the same wire index as SLOT.
    case zones([ZoneTint])
    /// Cosmetic column dividers (hud_dividers plan). Each Int is a grid_col
    /// boundary; the HUD draws a full-height vertical rule to the left of that
    /// column. Empty array = no dividers. Behaves like LAYOUT: buffered, then
    /// published on COMMIT.
    case dividers([Int])
    /// Whether this surface wants input-driven auto-hide: while true, the HUD
    /// sticky-dismisses on any mac mouse/keyboard input in Ableton (summon
    /// surfaces only — see hud-input-autohide-plan). Sent with LAYOUT so a
    /// late-starting HUD learns it; default false until an `AUTOHIDE|1` arrives.
    case autoHide(Bool)
    /// hud_toggle press. The HUD arbitrates show-vs-hide from its own true
    /// visibility (Python can't track it — the HUD hides autonomously via the
    /// idle timer and input monitor). Sent at the head of a fresh burst: if the
    /// HUD was visible it hides on that burst's COMMIT, else it shows the fresh
    /// data. See hud-input-autohide-plan.
    case toggleRequest
    case unknown
}

public enum WireProtocol {
    /// Single-source parser: the HUD has exactly one sender (a standalone
    /// surface, or the `lc_parks` compositor which merges any secondary region
    /// itself before emitting). No source/group/order on the wire.
    public static func parse(line: String) -> WireMessage {
        let fields = line.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
        guard !fields.isEmpty else { return .unknown }

        switch fields[0] {
        case "PING":
            guard fields.count == 1 else { return .unknown }
            return .ping

        case "HIDE":
            guard fields.count == 1 else { return .unknown }
            return .hide

        case "LAYOUT":
            // LAYOUT|<n>|<gr>|<gc>|<kind>|<count>|<start>|<section>... × n
            guard fields.count >= 2, let n = Int(fields[1]) else { return .unknown }
            guard fields.count == 2 + n * 6 else { return .unknown }
            var cells: [HudCell] = []
            for i in 0..<n {
                let base = 2 + i * 6
                guard let gr = Int(fields[base]),
                      let gc = Int(fields[base+1]),
                      let kind = SlotKind(rawValue: fields[base+2]),
                      let count = Int(fields[base+3]),
                      let start = Int(fields[base+4]),
                      let section = Int(fields[base+5]) else { return .unknown }
                cells.append(HudCell(gridRow: gr, gridCol: gc, kind: kind, count: count,
                                     startIndex: start, section: section))
            }
            return .layout(cells)

        case "DEVICE":
            guard fields.count >= 2 else { return .unknown }
            return .device(fields[1])

        case "SLOT", "UPDATE":
            // Optional 8th `glyph` field: 7 fields = text-only (glyph ""),
            // 8 = with SF Symbol. Tolerating both keeps an older sender working.
            guard fields.count == 7 || fields.count == 8 else { return .unknown }
            guard let kind = SlotKind(rawValue: fields[1]) else { return .unknown }
            guard let index = Int(fields[2]) else { return .unknown }
            let name = fields[3]
            guard let value = Float(fields[4]),
                  let vmin = Float(fields[5]),
                  let vmax = Float(fields[6]) else { return .unknown }
            let glyph = fields.count == 8 ? fields[7] : ""
            let slot = Slot(name: name, value: value, min: vmin, max: vmax, glyph: glyph)
            return fields[0] == "UPDATE" ? .update(kind, index, slot) : .slot(kind, index, slot)

        case "COMMIT":
            guard fields.count == 2, let count = Int(fields[1]) else { return .unknown }
            return .commit(count)

        case "MODE":
            guard fields.count == 2 else { return .unknown }
            return fields[1] == "shift" ? .mode(isShift: true)
                 : fields[1] == "normal" ? .mode(isShift: false)
                 : .unknown

        case "PAGE":
            // Accept short 5-field form (counts only) and 7-field form
            // (counts + enc_label + btn_label). Labels carry "Best of" on
            // page 1 of a known device or the standard-bank name(s) for
            // higher pages — empty string means "no label this page".
            guard fields.count == 5 || fields.count == 7,
                  let encPage = Int(fields[1]),
                  let encTotal = Int(fields[2]),
                  let btnPage = Int(fields[3]),
                  let btnTotal = Int(fields[4]) else { return .unknown }
            let encLabel = fields.count == 7 ? fields[5] : ""
            let btnLabel = fields.count == 7 ? fields[6] : ""
            return .page(encPage: encPage, encTotal: encTotal,
                         btnPage: btnPage, btnTotal: btnTotal,
                         encLabel: encLabel, btnLabel: btnLabel)

        case "EVENT":
            // EVENT|<kind>|<wireIdx>|<text...> — text is the rest, may hold '|'.
            guard fields.count >= 4, let wireIdx = Int(fields[2]) else { return .unknown }
            let text = fields[3...].joined(separator: "|")
            return .event(kind: fields[1], wireIdx: wireIdx, text: text)

        case "AUTOHIDE":
            // AUTOHIDE|<0|1> — enable input-driven auto-hide for this surface.
            guard fields.count == 2, fields[1] == "0" || fields[1] == "1" else { return .unknown }
            return .autoHide(fields[1] == "1")

        case "TOGGLE":
            guard fields.count == 1 else { return .unknown }
            return .toggleRequest

        case "DIVIDERS":
            // DIVIDERS|<n>|<col0>|<col1>|... — cosmetic HUD column rules.
            guard fields.count >= 2, let n = Int(fields[1]) else { return .unknown }
            guard fields.count == 2 + n else { return .unknown }
            var cols: [Int] = []
            for i in 0..<n {
                guard let c = Int(fields[2 + i]) else { return .unknown }
                cols.append(c)
            }
            return .dividers(cols)

        case "ZONES":
            // ZONES|<n>|<kind>|<idx>|<hex>| × n. n=0 clears all tints.
            guard fields.count >= 2, let n = Int(fields[1]) else { return .unknown }
            guard fields.count == 2 + n * 3 else { return .unknown }
            var tints: [ZoneTint] = []
            for i in 0..<n {
                let base = 2 + i * 3
                guard let kind = SlotKind(rawValue: fields[base]),
                      let idx = Int(fields[base+1]) else { return .unknown }
                tints.append(ZoneTint(kind: kind, index: idx, hex: fields[base+2]))
            }
            return .zones(tints)

        default:
            return .unknown
        }
    }

    public static func parseAll(data: Data) -> [WireMessage] {
        guard let text = String(data: data, encoding: .utf8) else { return [] }
        return text
            .components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
            .map { parse(line: $0) }
    }
}
