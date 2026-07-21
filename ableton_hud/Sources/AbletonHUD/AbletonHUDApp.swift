import SwiftUI
import AppKit
import AbletonHUDCore
import os

@main
struct AbletonHUDApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private let udpListener = UDPListener()
    private var statusItem: NSStatusItem?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Menu bar icon for debug / quit access
        setupMenuBar()

        udpListener.start()

        sendHello()

        Task { @MainActor in
            AbletonFocusMonitor.shared.start()
            HUDOverlayManager.shared.start()
            GlobalInputMonitor.shared.start()   // SPIKE: log-only global input probe
        }

        os_log("[AbletonHUD] started — listening on UDP :5006", log: OSLog(subsystem: "com.local.AbletonHUD", category: "App"), type: .info)
    }

    func applicationWillTerminate(_ notification: Notification) {
        udpListener.stop()
        Task { @MainActor in
            GlobalInputMonitor.shared.stop()
            HUDOverlayManager.shared.stop()
            AbletonFocusMonitor.shared.stop()
        }
    }

    private func sendHello() {
        let sock = socket(AF_INET, SOCK_DGRAM, 0)
        guard sock >= 0 else { return }
        defer { close(sock) }
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = UInt16(40844).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")
        let data = "HELLO".data(using: .utf8)!
        _ = data.withUnsafeBytes { buf in
            sendto(sock, buf.baseAddress, data.count, 0,
                   withUnsafePointer(to: &addr) { UnsafeRawPointer($0).assumingMemoryBound(to: sockaddr.self) },
                   socklen_t(MemoryLayout<sockaddr_in>.size))
        }
    }

    // MARK: - Menu bar

    private func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "dial.medium", accessibilityDescription: "Ableton HUD")
        }
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Ableton HUD", action: nil, keyEquivalent: ""))
        menu.addItem(.separator())

        let debugItem = NSMenuItem(title: "Show Debug Info", action: #selector(showDebugInfo), keyEquivalent: "d")
        debugItem.target = self
        menu.addItem(debugItem)

        menu.addItem(.separator())
        let quitItem = NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quitItem)

        statusItem?.menu = menu
    }

    @objc private func showDebugInfo() {
        Task { @MainActor in
            let state = DeviceState.shared
            let dials = state.dialSlots.enumerated().compactMap { i, s -> String? in
                guard let s else { return nil }
                return "  dial[\(i)] \(s.name) = \(s.value)"
            }.joined(separator: "\n")
            let buttons = state.buttonSlots.enumerated().compactMap { i, s -> String? in
                guard let s else { return nil }
                return "  btn[\(i)] \(s.name) = \(s.value)"
            }.joined(separator: "\n")
            let msg = """
            Device: \(state.deviceName.isEmpty ? "(none)" : state.deviceName)
            Dials:
            \(dials.isEmpty ? "  (none)" : dials)
            Buttons:
            \(buttons.isEmpty ? "  (none)" : buttons)
            """
            print("[AbletonHUD DEBUG]\n\(msg)")
            let alert = NSAlert()
            alert.messageText = "AbletonHUD State"
            alert.informativeText = msg
            alert.runModal()
        }
    }
}
