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
    case mode(isShift: Bool)
    case page(encPage: Int, encTotal: Int, btnPage: Int, btnTotal: Int,
              encLabel: String, btnLabel: String)
    case unknown
}

public enum WireProtocol {
    public static func parse(line: String) -> WireMessage {
        let fields = line.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
        guard !fields.isEmpty else { return .unknown }

        switch fields[0] {
        case "PING":
            guard fields.count == 1 else { return .unknown }
            return .ping

        case "LAYOUT":
            guard fields.count >= 2, let n = Int(fields[1]) else { return .unknown }
            guard fields.count >= 2 + n * 5 else { return .unknown }
            var cells: [HudCell] = []
            for i in 0..<n {
                let base = 2 + i * 5
                guard let gr = Int(fields[base]),
                      let gc = Int(fields[base+1]),
                      let kind = SlotKind(rawValue: fields[base+2]),
                      let count = Int(fields[base+3]),
                      let start = Int(fields[base+4]) else { return .unknown }
                cells.append(HudCell(gridRow: gr, gridCol: gc, kind: kind, count: count, startIndex: start))
            }
            return .layout(cells)

        case "DEVICE":
            guard fields.count >= 2 else { return .unknown }
            return .device(fields[1])

        case "SLOT", "UPDATE":
            guard fields.count >= 7 else { return .unknown }
            guard let kind = SlotKind(rawValue: fields[1]) else { return .unknown }
            guard let index = Int(fields[2]) else { return .unknown }
            let name = fields[3]
            guard let value = Float(fields[4]),
                  let vmin = Float(fields[5]),
                  let vmax = Float(fields[6]) else { return .unknown }
            let slot = Slot(name: name, value: value, min: vmin, max: vmax)
            return fields[0] == "UPDATE" ? .update(kind, index, slot) : .slot(kind, index, slot)

        case "COMMIT":
            guard fields.count >= 2, let count = Int(fields[1]) else { return .unknown }
            return .commit(count)

        case "MODE":
            guard fields.count >= 2 else { return .unknown }
            return fields[1] == "shift" ? .mode(isShift: true)
                 : fields[1] == "normal" ? .mode(isShift: false)
                 : .unknown

        case "PAGE":
            // Accept legacy 5-field form (counts only) and 7-field form
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
