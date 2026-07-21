import Foundation
import Combine

/// All HUD state for the single sender. Holds both the burst *pending* buffers
/// and the committed *published* values. The `lc_parks` compositor merges any
/// secondary region on the Python side, so the HUD only ever sees one stream
/// with one combined grid.
@MainActor
public class DeviceState: ObservableObject {
    public static let shared = DeviceState()

    // Published (committed) values, observed by the SwiftUI view layer.
    @Published public var deviceName: String = ""
    @Published public var dialSlots: [Slot?] = []
    @Published public var buttonSlots: [Slot?] = []
    @Published public var hudCells: [HudCell] = []
    /// Cosmetic column dividers (hud_dividers plan): grid_col boundaries where
    /// the view draws a full-height vertical rule to the left of that column.
    @Published public var dividerCols: [Int] = []
    @Published public var isShiftMode: Bool = false
    @Published public var encoderPage: Int = 1
    @Published public var pageTotal: Int = 1
    @Published public var bankLabel: String = ""
    @Published public var dismissed: Bool = false

    /// Whether this surface wants input-driven auto-hide (hud-input-autohide-plan).
    /// Set by the `AUTOHIDE` wire message; only summon surfaces send `AUTOHIDE|1`.
    /// The GlobalInputMonitor gates on this so non-summon surfaces (and the
    /// pre-handshake window) never sticky-hide on a mac click/keystroke.
    @Published public var autoHideOnInput: Bool = false

    /// Zone-colour tints, wire index -> RRGGBB hex (grid-zone-colour-coding-plan).
    /// Empty when the focused device isn't zoned. The view colours dial ring /
    /// button border strokes from these.
    @Published public var dialColors: [Int: String] = [:]
    @Published public var buttonColors: [Int: String] = [:]

    /// Show-info: the most recent button-press explanation (EVENT). The view
    /// renders it as a transient footer + cell pulse and fades it; `seq` lets
    /// the view restart its fade even when the same text repeats. Orthogonal to
    /// the burst/published slot state.
    @Published public var lastEvent: ButtonEvent? = nil

    // hud_toggle arbitration: a TOGGLE at the head of a burst arms this, capturing
    // whether the HUD was visible *before* the burst. The burst's COMMIT then
    // hides (if it was visible) or shows the fresh data (if it wasn't) — the HUD
    // owns the show/hide decision because Python can't track true visibility.
    private var pendingToggle = false
    private var toggleWasVisible = false

    // Pending (in-burst) buffers, swapped into the published values on COMMIT.
    private var pendingDials: [Int: Slot] = [:]
    private var pendingButtons: [Int: Slot] = [:]
    private var pendingName: String = ""
    private var pendingCells: [HudCell] = []
    private var pendingDividerCols: [Int] = []
    private var pendingEncoderPage: Int = 1
    private var pendingEncoderTotal: Int = 1
    private var pendingButtonPage: Int = 1
    private var pendingButtonTotal: Int = 1
    private var pendingBankLabel: String = ""
    private var pendingDialColors: [Int: String] = [:]
    private var pendingButtonColors: [Int: String] = [:]

    public let commitReceived = PassthroughSubject<Void, Never>()
    public let hideRequested = PassthroughSubject<Void, Never>()

    private var eventSeq: Int = 0

    public init() {}

    /// The HUD is "visible" when it has committed content and hasn't been
    /// dismissed. The overlay manager gates show/hide on this.
    public var isVisible: Bool {
        !dismissed && !deviceName.isEmpty
    }

    /// The idle auto-dismiss timer fired: hide *stickily*, exactly like a wire
    /// HIDE. Without this the panel merely orderOut's and the next UPDATE (e.g.
    /// playback automation) re-shows it — under summon that resurrects the HUD
    /// uninvited. The sticky flag is cleared by the next device burst, so a
    /// `selection`-trigger surface keeps its "next selection re-shows" feel.
    public func timerDismiss() {
        hudLog("timerDismiss dismissed=\(dismissed)->true", level: .fine)
        dismissed = true
    }

    public func apply(message: WireMessage) {
        // Receiver-side trace (hud-protocol-instrumentation-plan, Part B): every
        // case logs its decisive state — especially the dismissed/isShiftMode
        // flips — at .fine so it interleaves with the surface's `[hudtrace]`
        // lines for both HUD bugs. Gated; silent unless HUD_FINE is armed.
        switch message {
        case .layout(let cells):
            pendingCells = cells
            hudLog("apply LAYOUT cells=\(cells.count)", level: .fine)

        case .dividers(let cols):
            // Like LAYOUT: buffered here, published on COMMIT, and NOT cleared by
            // DEVICE so it persists across device changes.
            pendingDividerCols = cols
            hudLog("apply DIVIDERS cols=\(cols)", level: .fine)

        case .device(let name):
            // A new device burst means the user (re)selected a device — clear the
            // sticky dismiss so the upcoming COMMIT is allowed to show the HUD.
            hudLog("apply DEVICE name=\(name) dismissed=\(dismissed)->false", level: .fine)
            dismissed = false
            pendingDials = [:]
            pendingButtons = [:]
            pendingName = name
            pendingEncoderPage = 1
            pendingEncoderTotal = 1
            pendingButtonPage = 1
            pendingButtonTotal = 1
            pendingBankLabel = ""
            pendingDialColors = [:]
            pendingButtonColors = [:]

        case .slot(let kind, let index, let slot):
            guard index >= 0 else { return }
            switch kind {
            case .dial:   pendingDials[index] = slot
            case .button: pendingButtons[index] = slot
            }
            hudLog("apply SLOT \(kind) idx=\(index)", level: .fine)

        case .update(let kind, let index, let slot):
            guard index >= 0 else { return }
            // A dismissed HUD ignores live UPDATEs entirely: it neither patches a
            // slot nor fires the commitReceived visibility signal. Otherwise a
            // stream of playback-automation UPDATEs would resurrect a HUD the
            // idle timer (or HIDE) just dismissed — the summon-mode failure the
            // sticky flag exists to prevent. The next real burst repaints fresh.
            guard !dismissed else {
                hudLog("apply UPDATE \(kind) idx=\(index) ignored (dismissed)", level: .fine)
                return
            }
            switch kind {
            case .dial:
                if index < dialSlots.count { dialSlots[index] = slot }
            case .button:
                if index < buttonSlots.count { buttonSlots[index] = slot }
            }
            hudLog("apply UPDATE \(kind) idx=\(index) dismissed=\(dismissed)", level: .fine)
            commitReceived.send()

        case .commit:
            hudCells = pendingCells
            dividerCols = pendingDividerCols
            deviceName = pendingName
            encoderPage = pendingEncoderPage
            pageTotal = max(pendingEncoderTotal, pendingButtonTotal)
            bankLabel = pendingBankLabel
            dialColors = pendingDialColors
            buttonColors = pendingButtonColors
            let totalDials = pendingCells.filter { $0.kind == .dial }.reduce(0) { $0 + $1.count }
            let totalButtons = pendingCells.filter { $0.kind == .button }.reduce(0) { $0 + $1.count }
            dialSlots = (0..<totalDials).map { pendingDials[$0] }
            buttonSlots = (0..<totalButtons).map { pendingButtons[$0] }
            // Fresh data is published above either way. A toggle burst that found
            // the HUD already visible means "hide"; otherwise (and for every
            // non-toggle burst) it means "show".
            if pendingToggle && toggleWasVisible {
                pendingToggle = false
                dismissed = true
                hudLog("apply COMMIT name=\(deviceName) (toggle-off) -> hide", level: .fine)
                hideRequested.send()
            } else {
                pendingToggle = false
                dismissed = false
                hudLog("apply COMMIT name=\(deviceName) dials=\(totalDials) buttons=\(totalButtons) dismissed->false isVisible=\(isVisible)", level: .fine)
                commitReceived.send()
            }

        case .ping:
            hudLog("apply PING (rearm timer) dismissed=\(dismissed)", level: .fine)
            commitReceived.send()

        case .hide:
            hudLog("apply HIDE dismissed=\(dismissed)->true", level: .fine)
            dismissed = true
            hideRequested.send()

        case .mode(let isShift):
            hudLog("apply MODE isShift=\(isShiftMode)->\(isShift)", level: .fine)
            isShiftMode = isShift

        case .page(let encPage, let encTotal, let btnPage, let btnTotal,
                   let encLabel, let btnLabel):
            pendingEncoderPage = encPage
            pendingEncoderTotal = encTotal
            pendingButtonPage = btnPage
            pendingButtonTotal = btnTotal
            // Encoder label is the primary HUD title; fall back to the button
            // label if the encoder page has none but a button page does.
            pendingBankLabel = !encLabel.isEmpty ? encLabel : btnLabel
            hudLog("apply PAGE enc=\(encPage)/\(encTotal) btn=\(btnPage)/\(btnTotal)", level: .fine)

        case .event(let kind, let wireIdx, let text):
            // Show-info: surface a transient explanation; the view renders +
            // fades it. Does not touch burst/published slot state.
            eventSeq += 1
            lastEvent = ButtonEvent(kind: kind, wireIdx: wireIdx, text: text, seq: eventSeq)
            hudLog("apply EVENT kind=\(kind) idx=\(wireIdx)", level: .fine)

        case .zones(let tints):
            // Per-burst zone tints; replace pending colours wholesale (an empty
            // ZONES clears them, so a non-zoned device commits no tint).
            pendingDialColors = [:]
            pendingButtonColors = [:]
            for t in tints {
                switch t.kind {
                case .dial:   pendingDialColors[t.index] = t.hex
                case .button: pendingButtonColors[t.index] = t.hex
                }
            }
            hudLog("apply ZONES count=\(tints.count)", level: .fine)

        case .autoHide(let enabled):
            hudLog("apply AUTOHIDE \(autoHideOnInput)->\(enabled)", level: .fine)
            autoHideOnInput = enabled

        case .toggleRequest:
            // Arm; capture visibility BEFORE the burst's DEVICE clears `dismissed`.
            pendingToggle = true
            toggleWasVisible = isVisible
            hudLog("apply TOGGLE armed wasVisible=\(isVisible)", level: .fine)

        case .unknown:
            hudLog("apply UNKNOWN", level: .fine)
            break
        }
    }
}

/// One show-info button-press explanation (from an EVENT message). `seq`
/// monotonically increases so the view can re-trigger its fade animation even
/// when an identical press repeats.
public struct ButtonEvent: Equatable {
    public let kind: String
    public let wireIdx: Int
    public let text: String
    public let seq: Int

    public init(kind: String, wireIdx: Int, text: String, seq: Int) {
        self.kind = kind
        self.wireIdx = wireIdx
        self.text = text
        self.seq = seq
    }
}
