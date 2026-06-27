import AppKit
import SwiftUI
import Combine
import AbletonHUDCore
import os

private let log = OSLog(subsystem: "com.local.AbletonHUD", category: "HUDOverlay")
private let kSavedPosition = "hudPanelPosition"

@MainActor
class HUDOverlayManager {
    static let shared = HUDOverlayManager()

    private var overlayPanel: NSPanel?
    private var localKeyMonitor: Any?
    private var moveObserver: NSObjectProtocol?
    private var cancellables = Set<AnyCancellable>()
    private var dismissTimer: Timer?
    private var savedPosition: NSPoint?
    let chrome = HUDChrome()

    func start() {
        createPanel()
        setupKeyMonitor()

        DeviceState.shared.commitReceived
            .receive(on: RunLoop.main)
            .sink { [weak self] in
                guard let self else { return }
                let focused = AbletonFocusMonitor.shared.isAbletonFrontmost
                os_log("commitReceived — focused=%{public}d", log: log, type: .info, focused)
                hudLog("commitReceived: focused=\(focused) visible=\(DeviceState.shared.isVisible)", level: .fine)
                // Any active-group member committing/pinging re-arms the single
                // dismiss timer = "alive while either surface is active".
                if focused && DeviceState.shared.isVisible {
                    self.show()
                } else {
                    hudLog("commitReceived: not showing (focused=\(focused) visible=\(DeviceState.shared.isVisible))", level: .fine)
                }
            }
            .store(in: &cancellables)

        DeviceState.shared.hideRequested
            .receive(on: RunLoop.main)
            .sink { [weak self] in
                // A single source's HIDE must not drop the whole composed panel.
                // Hide only once every active-group member is dismissed/empty.
                if !DeviceState.shared.isVisible {
                    hudLog("hideRequested — all active sources dismissed, hiding", level: .fine)
                    self?.hide()
                } else {
                    hudLog("hideRequested — other active source still visible, keeping panel", level: .fine)
                }
            }
            .store(in: &cancellables)

        AbletonFocusMonitor.shared.$isAbletonFrontmost
            .receive(on: RunLoop.main)
            .sink { [weak self] isFront in
                if !isFront {
                    self?.hide()
                } else if DeviceState.shared.isVisible {
                    self?.show()
                }
            }
            .store(in: &cancellables)

        chrome.$zoom
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in
                self?.resizePanel()
            }
            .store(in: &cancellables)

        chrome.$baseSize
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in
                self?.resizePanel()
            }
            .store(in: &cancellables)

        chrome.$isMouseOver
            .receive(on: RunLoop.main)
            .sink { [weak self] isOver in
                guard let self else { return }
                if isOver {
                    self.dismissTimer?.invalidate()
                    self.dismissTimer = nil
                } else {
                    self.armDismissTimer()
                }
            }
            .store(in: &cancellables)
    }

    func stop() {
        dismissTimer?.invalidate()
        hide()
        if let monitor = localKeyMonitor {
            NSEvent.removeMonitor(monitor)
            localKeyMonitor = nil
        }
        if let obs = moveObserver {
            NotificationCenter.default.removeObserver(obs)
            moveObserver = nil
        }
        cancellables.removeAll()
    }

    func show() {
        guard let panel = overlayPanel else { return }
        resizePanel()
        if !panel.isVisible {
            centerOnAbletonWindow()
        }
        panel.orderFront(nil)
        if !chrome.isMouseOver {
            armDismissTimer()
        }
        hudLog("show() — frame=\(panel.frame)", level: .fine)
    }

    func hide() {
        hudLog("hide() — wasVisible=\(overlayPanel?.isVisible ?? false)", level: .fine)
        dismissTimer?.invalidate()
        dismissTimer = nil
        overlayPanel?.orderOut(nil)
    }

    // MARK: - Private

    private func armDismissTimer() {
        dismissTimer?.invalidate()
        dismissTimer = Timer.scheduledTimer(withTimeInterval: 7, repeats: false) { [weak self] _ in
            hudLog("dismissTimer fired -> hide()", level: .fine)
            self?.hide()
        }
    }

    private func resizePanel() {
        guard let panel = overlayPanel else { return }
        let newSize = NSSize(
            width: max(1, chrome.baseSize.width) * chrome.zoom,
            height: max(1, chrome.baseSize.height) * chrome.zoom
        )
        if newSize != panel.contentView?.frame.size {
            panel.setContentSize(newSize)
        }
    }

    private func createPanel() {
        hudLog("createPanel()")

        // Restore saved position from UserDefaults
        if let raw = UserDefaults.standard.string(forKey: kSavedPosition) {
            let parts = raw.split(separator: ",")
            if parts.count == 2, let x = Double(parts[0]), let y = Double(parts[1]) {
                savedPosition = NSPoint(x: x, y: y)
            }
        }

        let hostingController = NSHostingController(rootView: HUDView(state: DeviceState.shared, chrome: chrome))
        hostingController.view.wantsLayer = true
        hostingController.view.layer?.backgroundColor = CGColor.clear

        let panel = NSPanel(
            contentRect: NSRect(origin: .zero, size: hostingController.view.fittingSize),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        panel.isReleasedWhenClosed = false
        panel.hasShadow = true
        panel.hidesOnDeactivate = false
        panel.isMovableByWindowBackground = true
        panel.contentViewController = hostingController

        if let cv = panel.contentView {
            cv.wantsLayer = true
            cv.layer?.backgroundColor = CGColor.clear
        }

        // Persist position whenever the user drags the panel
        moveObserver = NotificationCenter.default.addObserver(
            forName: NSWindow.didMoveNotification,
            object: panel,
            queue: .main
        ) { [weak self] _ in
            guard let self, let origin = self.overlayPanel?.frame.origin else { return }
            self.savedPosition = origin
            UserDefaults.standard.set("\(origin.x),\(origin.y)", forKey: kSavedPosition)
            hudLog("Panel moved — saved position \(origin)")
        }

        overlayPanel = panel

        if let cv = panel.contentView {
            let trackView = HUDChromeTrackingView(chrome: chrome)
            trackView.frame = cv.bounds
            trackView.autoresizingMask = [.width, .height]
            cv.addSubview(trackView, positioned: .above, relativeTo: hostingController.view)
        }

        hudLog("createPanel() done — size=\(panel.frame.size)")
    }

    private func setupKeyMonitor() {
        localKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if event.keyCode == 53 { // Esc
                self?.hide()
                return nil
            }
            return event
        }
    }

    // MARK: - Centering

    /// Find Ableton's main window bounds via CGWindowList (no accessibility permissions needed).
    private func abletonWindowFrame() -> CGRect? {
        guard let pid = NSWorkspace.shared.runningApplications
            .first(where: { $0.bundleIdentifier?.hasPrefix("com.ableton.live") == true })?
            .processIdentifier else { return nil }

        let opts: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
        guard let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }

        // Find the first layer-0 window owned by Ableton
        for info in list {
            guard (info[kCGWindowOwnerPID as String] as? Int32) == pid,
                  (info[kCGWindowLayer as String] as? Int) == 0,
                  let bounds = info[kCGWindowBounds as String] as? [String: CGFloat] else { continue }
            return CGRect(
                x: bounds["X"] ?? 0,
                y: bounds["Y"] ?? 0,
                width: bounds["Width"] ?? 0,
                height: bounds["Height"] ?? 0
            )
        }
        return nil
    }

    private func centerOnAbletonWindow() {
        guard let panel = overlayPanel,
              let screen = NSScreen.main else { return }

        // Honour the last position the user dragged the panel to
        if let pos = savedPosition {
            panel.setFrameOrigin(pos)
            hudLog("Restored saved position: \(pos)")
            return
        }

        if let rect = abletonWindowFrame(), rect.width > 0 {
            // CGWindowList uses top-left origin; AppKit uses bottom-left — convert Y
            let screenH = screen.frame.height
            let cx = rect.midX
            let cy = screenH - rect.midY   // midY in AppKit coords
            let sz = panel.frame.size
            panel.setFrameOrigin(NSPoint(x: cx - sz.width / 2, y: cy - sz.height / 2))
            hudLog("Positioned via CGWindowList: \(panel.frame)")
            return
        }

        // Fallback: center on visible screen area
        let f = screen.visibleFrame
        let sz = panel.frame.size
        panel.setFrameOrigin(NSPoint(x: f.midX - sz.width / 2, y: f.midY - sz.height / 2))
        hudLog("Positioned at screen center: \(panel.frame)")
    }
}

private final class HUDChromeTrackingView: NSView {
    private let chrome: HUDChrome

    init(chrome: HUDChrome) {
        self.chrome = chrome
        super.init(frame: .zero)
        let opts: NSTrackingArea.Options = [.activeAlways, .mouseEnteredAndExited, .inVisibleRect]
        addTrackingArea(NSTrackingArea(rect: bounds, options: opts, owner: self, userInfo: nil))
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func mouseEntered(with event: NSEvent) {
        chrome.isMouseOver = true
    }

    override func mouseExited(with event: NSEvent) {
        chrome.isMouseOver = false
    }
}
