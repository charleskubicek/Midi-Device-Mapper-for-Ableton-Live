import AppKit
import Combine
import AbletonHUDCore

@MainActor
class AbletonFocusMonitor: ObservableObject {
    static let shared = AbletonFocusMonitor()

    @Published private(set) var isAbletonFrontmost = false

    private var activationObserver: NSObjectProtocol?
    private var deactivationObserver: NSObjectProtocol?

    func start() {
        let nc = NSWorkspace.shared.notificationCenter

        activationObserver = nc.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notif in
            guard let self else { return }
            let app = notif.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication
            let isAbleton = app?.bundleIdentifier?.hasPrefix("com.ableton.live") == true
            hudLog("didActivate: \(app?.localizedName ?? "?") — isAbleton=\(isAbleton)")
            Task { @MainActor in self.isAbletonFrontmost = isAbleton }
        }

        deactivationObserver = nc.addObserver(
            forName: NSWorkspace.didDeactivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notif in
            guard let self else { return }
            let app = notif.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication
            let isAbleton = app?.bundleIdentifier?.hasPrefix("com.ableton.live") == true
            hudLog("didDeactivate: \(app?.localizedName ?? "?") — isAbleton=\(isAbleton)")
            // Only clear focus when Ableton itself loses focus, not when any other app does
            if isAbleton {
                Task { @MainActor in self.isAbletonFrontmost = false }
            }
        }

        // Seed initial state — if Ableton was already frontmost when we launched,
        // no activation notification will fire, so we check right now.
        let alreadyFront = NSWorkspace.shared.frontmostApplication?
            .bundleIdentifier?.hasPrefix("com.ableton.live") == true
        isAbletonFrontmost = alreadyFront
        hudLog("AbletonFocusMonitor.start() — seeded isAbletonFrontmost=\(alreadyFront)")
    }

    func stop() {
        let nc = NSWorkspace.shared.notificationCenter
        if let obs = activationObserver { nc.removeObserver(obs) }
        if let obs = deactivationObserver { nc.removeObserver(obs) }
    }
}
