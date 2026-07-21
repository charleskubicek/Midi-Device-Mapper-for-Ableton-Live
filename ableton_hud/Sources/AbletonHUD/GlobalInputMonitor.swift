import AppKit
import ApplicationServices
import Combine
import AbletonHUDCore

/// Input-driven auto-hide (hud-input-autohide-plan). The HUD means "I'm tweaking
/// a device with the hardware"; the moment the user switches to Live's GUI — any
/// mac mouse-click or keystroke while Ableton is frontmost — it sticky-hides.
/// That single rule replaces enumerating every non-device view (clip, browser,
/// mixer, …), which Live's API can't observe anyway.
///
/// Spike-confirmed on this platform: mouse-down needs no permission; keyDown
/// needs the Accessibility grant (`NSEvent` global key monitors); a global
/// monitor never receives the HUD's own panel clicks. Gated on
/// `DeviceState.autoHideOnInput` (summon surfaces only) via `InputDismissPolicy`.
@MainActor
final class GlobalInputMonitor {
    static let shared = GlobalInputMonitor()

    private var monitor: Any?
    private var cancellable: AnyCancellable?
    private var promptedForAccessibility = false

    func start() {
        // Defer the Accessibility prompt until a summon surface actually asks for
        // input-driven auto-hide (AUTOHIDE|1 -> autoHideOnInput). Non-summon
        // surfaces never need keyboard monitoring, so they never see the prompt.
        // Mouse-down works without any permission regardless.
        cancellable = DeviceState.shared.$autoHideOnInput
            .receive(on: RunLoop.main)
            .sink { [weak self] enabled in
                if enabled { self?.requestAccessibilityIfNeeded() }
            }

        let mask: NSEvent.EventTypeMask = [.leftMouseDown, .rightMouseDown, .keyDown]
        monitor = NSEvent.addGlobalMonitorForEvents(matching: mask) { _ in
            Task { @MainActor in
                let enabled = DeviceState.shared.autoHideOnInput
                let front = AbletonFocusMonitor.shared.isAbletonFrontmost
                let over = HUDOverlayManager.shared.chrome.isMouseOver
                if InputDismissPolicy.shouldDismiss(enabled: enabled, abletonFrontmost: front, overHud: over) {
                    hudLog("[input] mac input in Ableton -> stickyDismiss", level: .fine)
                    HUDOverlayManager.shared.stickyDismiss("input")
                }
            }
        }
        hudLog("[input] global input monitor installed=\(monitor != nil)")
    }

    /// keyDown global monitoring needs Accessibility; prompt once, the first time
    /// a summon surface enables input auto-hide. Mouse-down works regardless, so
    /// a denied prompt only loses keyboard dismissal.
    private func requestAccessibilityIfNeeded() {
        guard !promptedForAccessibility, !AXIsProcessTrusted() else { return }
        promptedForAccessibility = true
        let promptKey = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        let granted = AXIsProcessTrustedWithOptions([promptKey: true] as CFDictionary)
        hudLog("[input] summon surface enabled input auto-hide; Accessibility granted=\(granted) (keyboard needs it; mouse works regardless)")
    }

    func stop() {
        cancellable = nil
        if let m = monitor { NSEvent.removeMonitor(m) }
        monitor = nil
    }
}
