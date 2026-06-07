import Foundation

public struct Slot: Equatable {
    public let name: String
    public let value: Float
    public let min: Float
    public let max: Float

    public init(name: String, value: Float, min: Float, max: Float) {
        self.name = name
        self.value = value
        self.min = min
        self.max = max
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
    public init(gridRow: Int, gridCol: Int, kind: SlotKind, count: Int, startIndex: Int) {
        self.gridRow = gridRow; self.gridCol = gridCol; self.kind = kind
        self.count = count; self.startIndex = startIndex
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
    case unknown
}

/// A parsed line plus the identity fields carried on every message:
/// `source` (which surface sent it) and, for `LAYOUT`, the merge `group` and
/// display `order`. Non-layout messages report the defaults for group/order.
public struct ParsedMessage: Equatable {
    public let message: WireMessage
    public let source: String
    public let group: String
    public let order: Int
    public init(_ message: WireMessage, source: String = "main",
                group: String = "main", order: Int = 0) {
        self.message = message
        self.source = source
        self.group = group
        self.order = order
    }
}

public enum WireProtocol {
    /// Convenience for callers (and tests) that only care about the message
    /// body, not its source/group/order.
    public static func parse(line: String) -> WireMessage {
        return parseLine(line: line).message
    }

    public static func parseLine(line: String) -> ParsedMessage {
        let fields = line.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
        guard !fields.isEmpty else { return ParsedMessage(.unknown) }
        // fields[1] is the source id on every message.
        let source = fields.count >= 2 ? fields[1] : "main"

        switch fields[0] {
        case "PING":
            guard fields.count == 2 else { return ParsedMessage(.unknown) }
            return ParsedMessage(.ping, source: source)

        case "HIDE":
            guard fields.count == 2 else { return ParsedMessage(.unknown) }
            return ParsedMessage(.hide, source: source)

        case "LAYOUT":
            // LAYOUT|<src>|<group>|<order>|<n>|<gr>|<gc>|<kind>|<count>|<start>... × n
            guard fields.count >= 5,
                  let order = Int(fields[3]),
                  let n = Int(fields[4]) else { return ParsedMessage(.unknown) }
            let group = fields[2]
            guard fields.count == 5 + n * 5 else { return ParsedMessage(.unknown) }
            var cells: [HudCell] = []
            for i in 0..<n {
                let base = 5 + i * 5
                guard let gr = Int(fields[base]),
                      let gc = Int(fields[base+1]),
                      let kind = SlotKind(rawValue: fields[base+2]),
                      let count = Int(fields[base+3]),
                      let start = Int(fields[base+4]) else { return ParsedMessage(.unknown) }
                cells.append(HudCell(gridRow: gr, gridCol: gc, kind: kind, count: count, startIndex: start))
            }
            return ParsedMessage(.layout(cells), source: source, group: group, order: order)

        case "DEVICE":
            guard fields.count >= 3 else { return ParsedMessage(.unknown) }
            return ParsedMessage(.device(fields[2]), source: source)

        case "SLOT", "UPDATE":
            guard fields.count == 8 else { return ParsedMessage(.unknown) }
            guard let kind = SlotKind(rawValue: fields[2]) else { return ParsedMessage(.unknown) }
            guard let index = Int(fields[3]) else { return ParsedMessage(.unknown) }
            let name = fields[4]
            guard let value = Float(fields[5]),
                  let vmin = Float(fields[6]),
                  let vmax = Float(fields[7]) else { return ParsedMessage(.unknown) }
            let slot = Slot(name: name, value: value, min: vmin, max: vmax)
            let msg: WireMessage = fields[0] == "UPDATE" ? .update(kind, index, slot) : .slot(kind, index, slot)
            return ParsedMessage(msg, source: source)

        case "COMMIT":
            guard fields.count == 3, let count = Int(fields[2]) else { return ParsedMessage(.unknown) }
            return ParsedMessage(.commit(count), source: source)

        case "MODE":
            guard fields.count >= 3 else { return ParsedMessage(.unknown) }
            let m: WireMessage = fields[2] == "shift" ? .mode(isShift: true)
                 : fields[2] == "normal" ? .mode(isShift: false)
                 : .unknown
            return ParsedMessage(m, source: source)

        case "PAGE":
            // Accept short 6-field form (counts only) and 8-field form
            // (counts + enc_label + btn_label). Labels carry "Best of" on
            // page 1 of a known device or the standard-bank name(s) for
            // higher pages — empty string means "no label this page".
            guard fields.count == 6 || fields.count == 8,
                  let encPage = Int(fields[2]),
                  let encTotal = Int(fields[3]),
                  let btnPage = Int(fields[4]),
                  let btnTotal = Int(fields[5]) else { return ParsedMessage(.unknown) }
            let encLabel = fields.count == 8 ? fields[6] : ""
            let btnLabel = fields.count == 8 ? fields[7] : ""
            return ParsedMessage(.page(encPage: encPage, encTotal: encTotal,
                                       btnPage: btnPage, btnTotal: btnTotal,
                                       encLabel: encLabel, btnLabel: btnLabel),
                                 source: source)

        default:
            return ParsedMessage(.unknown)
        }
    }

    public static func parseAll(data: Data) -> [ParsedMessage] {
        guard let text = String(data: data, encoding: .utf8) else { return [] }
        return text
            .components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
            .map { parseLine(line: $0) }
    }
}
