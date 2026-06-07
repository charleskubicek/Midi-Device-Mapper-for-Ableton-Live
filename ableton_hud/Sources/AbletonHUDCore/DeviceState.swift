import Foundation
import Combine

/// All HUD state for a single sender (surface). Each source the HUD hears from
/// gets its own `SourceState`, so two surfaces sending interleaved bursts can
/// never clobber each other. Holds both the burst *pending* buffers and the
/// committed *published* values.
public final class SourceState {
    public var id: String = ""
    public var group: String = "main"
    public var order: Int = 0

    // Published (committed) values.
    public var deviceName: String = ""
    public var dialSlots: [Slot?] = []
    public var buttonSlots: [Slot?] = []
    public var hudCells: [HudCell] = []
    public var isShiftMode: Bool = false
    public var encoderPage: Int = 1
    public var pageTotal: Int = 1
    public var bankLabel: String = ""
    public var dismissed: Bool = false

    // Pending (in-burst) buffers, swapped into the published values on COMMIT.
    var pendingDials: [Int: Slot] = [:]
    var pendingButtons: [Int: Slot] = [:]
    var pendingName: String = ""
    var pendingCells: [HudCell] = []
    var pendingEncoderPage: Int = 1
    var pendingEncoderTotal: Int = 1
    var pendingButtonPage: Int = 1
    var pendingButtonTotal: Int = 1
    var pendingBankLabel: String = ""

    public init() {}
}

@MainActor
public class DeviceState: ObservableObject {
    public static let shared = DeviceState()

    /// Per-source state, keyed by source id. `sourceOrder` preserves first-seen
    /// order as a tiebreaker; composition sorts by `order` then first-seen.
    @Published public var sources: [String: SourceState] = [:]
    @Published public var sourceOrder: [String] = []

    /// The source whose datagram we most recently handled. Its group is the
    /// "active group" — the one the single overlay window composes.
    @Published public private(set) var activeSource: String? = nil

    // ---- Legacy single-source projection -----------------------------------
    // The current view + overlay manager still read these flat fields. They
    // mirror whichever source was most recently mutated. Phase 3 replaces the
    // view with per-source rendering and removes the projection.
    @Published public var deviceName: String = ""
    @Published public var dialSlots: [Slot?] = []
    @Published public var buttonSlots: [Slot?] = []
    @Published public var hudCells: [HudCell] = []
    @Published public var isShiftMode: Bool = false
    @Published public var encoderPage: Int = 1
    @Published public var pageTotal: Int = 1
    @Published public var bankLabel: String = ""
    @Published public var dismissed: Bool = false

    public let commitReceived = PassthroughSubject<Void, Never>()
    public let hideRequested = PassthroughSubject<Void, Never>()

    /// Fetch (creating if needed) the state for a source. Always refreshes
    /// group/order so a LAYOUT seen after a stray earlier message still wins.
    @discardableResult
    public func state(for source: String, group: String? = nil, order: Int? = nil) -> SourceState {
        let s: SourceState
        if let existing = sources[source] {
            s = existing
        } else {
            s = SourceState()
            s.id = source
            sources[source] = s
            sourceOrder.append(source)
        }
        if let group = group { s.group = group }
        if let order = order { s.order = order }
        return s
    }

    /// The composed group: members of the active source's group, in render
    /// order (`order`, then first-seen). When no source is active yet, returns
    /// every source so a single-controller setup still renders.
    public func activeMembers() -> [SourceState] {
        let group = activeSource.flatMap { sources[$0]?.group }
        let members = sourceOrder.compactMap { sources[$0] }
            .filter { group == nil || $0.group == group }
        return members.sorted { a, b in
            if a.order != b.order { return a.order < b.order }
            let ia = sourceOrder.firstIndex(of: a.id) ?? 0
            let ib = sourceOrder.firstIndex(of: b.id) ?? 0
            return ia < ib
        }
    }

    /// A source is "visible" when it has committed content and hasn't been
    /// dismissed. The panel shows while any active-group member is visible and
    /// hides only once they all are dismissed/empty.
    public var anyActiveVisible: Bool {
        activeMembers().contains { !$0.dismissed && !$0.deviceName.isEmpty }
    }

    public func apply(message: WireMessage, source: String = "main",
                      group: String = "main", order: Int = 0) {
        if case .layout = message {} else if case .unknown = message {} else {
            activeSource = source
        }
        switch message {
        case .layout(let cells):
            // LAYOUT also establishes the source's group/order for composition.
            let s = state(for: source, group: group, order: order)
            s.pendingCells = cells

        case .device(let name):
            let s = state(for: source)
            // A new device burst means the user (re)selected a device — clear the
            // sticky dismiss so the upcoming COMMIT is allowed to show the HUD.
            s.dismissed = false
            s.pendingDials = [:]
            s.pendingButtons = [:]
            s.pendingName = name
            s.pendingEncoderPage = 1
            s.pendingEncoderTotal = 1
            s.pendingButtonPage = 1
            s.pendingButtonTotal = 1
            s.pendingBankLabel = ""
            mirror(s)

        case .slot(let kind, let index, let slot):
            guard index >= 0 else { return }
            let s = state(for: source)
            switch kind {
            case .dial:   s.pendingDials[index] = slot
            case .button: s.pendingButtons[index] = slot
            }

        case .update(let kind, let index, let slot):
            guard index >= 0 else { return }
            let s = state(for: source)
            switch kind {
            case .dial:
                if index < s.dialSlots.count { s.dialSlots[index] = slot }
            case .button:
                if index < s.buttonSlots.count { s.buttonSlots[index] = slot }
            }
            mirror(s)
            commitReceived.send()

        case .commit:
            let s = state(for: source)
            s.dismissed = false
            s.hudCells = s.pendingCells
            s.deviceName = s.pendingName
            s.encoderPage = s.pendingEncoderPage
            s.pageTotal = max(s.pendingEncoderTotal, s.pendingButtonTotal)
            s.bankLabel = s.pendingBankLabel
            let totalDials = s.pendingCells.filter { $0.kind == .dial }.reduce(0) { $0 + $1.count }
            let totalButtons = s.pendingCells.filter { $0.kind == .button }.reduce(0) { $0 + $1.count }
            s.dialSlots = (0..<totalDials).map { s.pendingDials[$0] }
            s.buttonSlots = (0..<totalButtons).map { s.pendingButtons[$0] }
            mirror(s)
            commitReceived.send()

        case .ping:
            _ = state(for: source)
            commitReceived.send()

        case .hide:
            let s = state(for: source)
            s.dismissed = true
            mirror(s)
            hideRequested.send()

        case .mode(let isShift):
            let s = state(for: source)
            s.isShiftMode = isShift
            mirror(s)

        case .page(let encPage, let encTotal, let btnPage, let btnTotal,
                   let encLabel, let btnLabel):
            let s = state(for: source)
            s.pendingEncoderPage = encPage
            s.pendingEncoderTotal = encTotal
            s.pendingButtonPage = btnPage
            s.pendingButtonTotal = btnTotal
            // Encoder label is the primary HUD title; fall back to the button
            // label if the encoder page has none but a button page does.
            s.pendingBankLabel = !encLabel.isEmpty ? encLabel : btnLabel

        case .unknown:
            break
        }

        // Notify observers of the dictionary's contents changing (SourceState is
        // a reference type, so mutating it in place doesn't auto-publish).
        objectWillChange.send()
    }

    /// Copy a source's published values into the flat legacy fields. Interim
    /// shim until Phase 3's per-source view; removed then.
    private func mirror(_ s: SourceState) {
        deviceName = s.deviceName
        dialSlots = s.dialSlots
        buttonSlots = s.buttonSlots
        hudCells = s.hudCells
        isShiftMode = s.isShiftMode
        encoderPage = s.encoderPage
        pageTotal = s.pageTotal
        bankLabel = s.bankLabel
        dismissed = s.dismissed
    }
}
