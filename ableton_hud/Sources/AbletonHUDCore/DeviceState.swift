import Foundation
import Combine

@MainActor
public class DeviceState: ObservableObject {
    public static let shared = DeviceState()

    @Published public var deviceName: String = ""
    @Published public var dialSlots: [Slot?] = []
    @Published public var buttonSlots: [Slot?] = []
    @Published public var hudCells: [HudCell] = []
    @Published public var isShiftMode: Bool = false
    @Published public var encoderPage: Int = 1
    @Published public var pageTotal: Int = 1
    /// Bank title for the current encoder page (e.g. "Amplitude / Filter" or
    /// "Best of"). Empty when the page has no label.
    @Published public var bankLabel: String = ""

    /// Sticky dismiss flag. Set by `HIDE` when the user navigates away from the
    /// device in Live; cleared by the next device burst (`DEVICE`/`COMMIT`).
    /// While true, the overlay manager suppresses every show path so routine
    /// `UPDATE`/`PING`/refocus traffic can't resurrect the HUD.
    @Published public var dismissed: Bool = false

    private var pendingDials: [Int: Slot] = [:]
    private var pendingButtons: [Int: Slot] = [:]
    private var pendingName: String = ""
    private var pendingCells: [HudCell] = []
    private var pendingEncoderPage: Int = 1
    private var pendingEncoderTotal: Int = 1
    private var pendingButtonPage: Int = 1
    private var pendingButtonTotal: Int = 1
    private var pendingBankLabel: String = ""

    public let commitReceived = PassthroughSubject<Void, Never>()
    public let hideRequested = PassthroughSubject<Void, Never>()

    public func apply(message: WireMessage) {
        switch message {
        case .layout(let cells):
            pendingCells = cells

        case .device(let name):
            // A new device burst means the user (re)selected a device — clear the
            // sticky dismiss so the upcoming COMMIT is allowed to show the HUD.
            dismissed = false
            pendingDials = [:]
            pendingButtons = [:]
            pendingName = name
            pendingEncoderPage = 1
            pendingEncoderTotal = 1
            pendingButtonPage = 1
            pendingButtonTotal = 1
            pendingBankLabel = ""

        case .slot(let kind, let index, let slot):
            guard index >= 0 else { return }
            switch kind {
            case .dial:   pendingDials[index] = slot
            case .button: pendingButtons[index] = slot
            }

        case .update(let kind, let index, let slot):
            guard index >= 0 else { return }
            switch kind {
            case .dial:
                if index < dialSlots.count { dialSlots[index] = slot }
            case .button:
                if index < buttonSlots.count { buttonSlots[index] = slot }
            }
            commitReceived.send()

        case .commit:
            dismissed = false
            hudCells = pendingCells
            deviceName = pendingName
            encoderPage = pendingEncoderPage
            pageTotal = max(pendingEncoderTotal, pendingButtonTotal)
            bankLabel = pendingBankLabel
            let totalDials = pendingCells.filter { $0.kind == .dial }.reduce(0) { $0 + $1.count }
            let totalButtons = pendingCells.filter { $0.kind == .button }.reduce(0) { $0 + $1.count }
            dialSlots = (0..<totalDials).map { pendingDials[$0] }
            buttonSlots = (0..<totalButtons).map { pendingButtons[$0] }
            commitReceived.send()

        case .ping:
            commitReceived.send()

        case .hide:
            dismissed = true
            hideRequested.send()

        case .mode(let isShift):
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

        case .unknown:
            break
        }
    }
}